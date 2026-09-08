import { diag } from "./diag";
import { slog } from "../lib/log";

export type AudioSource = "mic" | "system";

type ChunkHandler = (blob: Blob, source: AudioSource) => void;
type StopHandler = (source: AudioSource, reason: string) => void;

type CaptureSession = {
  stream: MediaStream;
  context: AudioContext;
  input: MediaStreamAudioSourceNode;
  processor: ScriptProcessorNode;
  silent: GainNode;
  pending: Float32Array[];
  pendingSamples: number;
  targetSamples: number;
  keepAlive: number | null;
  processCount: number;
  samplesReceived: number;
  chunksEmitted: number;
  silentSkips: number;
  lastRms: number;
  lastChunkBytes: number;
  lastSampleAt: number;
};

const CHUNK_SECONDS = 3.2;
const SILENCE_RMS = 0.008;

function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const pcm = new Int16Array(samples.length);
  for (let i = 0; i < samples.length; i += 1) {
    const value = Math.max(-1, Math.min(1, samples[i]));
    pcm[i] = value < 0 ? Math.round(value * 0x8000) : Math.round(value * 0x7fff);
  }
  const bytes = pcm.byteLength;
  const buffer = new ArrayBuffer(44 + bytes);
  const view = new DataView(buffer);
  const writeString = (offset: number, text: string) => {
    for (let i = 0; i < text.length; i += 1) view.setUint8(offset + i, text.charCodeAt(i));
  };
  writeString(0, "RIFF");
  view.setUint32(4, 36 + bytes, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, bytes, true);
  new Uint8Array(buffer, 44).set(new Uint8Array(pcm.buffer));
  return new Blob([buffer], { type: "audio/wav" });
}

function concatFloat32(chunks: Float32Array[], total: number): Float32Array {
  const out = new Float32Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    out.set(chunk, offset);
    offset += chunk.length;
  }
  return out;
}

function rms(samples: Float32Array): number {
  let sum = 0;
  for (let i = 0; i < samples.length; i += 1) sum += samples[i] * samples[i];
  return Math.sqrt(sum / Math.max(1, samples.length));
}

/**
 * One MediaStream + AudioContext per source for the whole listening session.
 * PCM is sliced into complete WAV files so Whisper can transcribe every chunk.
 * Groq finishing an answer never closes this session.
 */
export class AudioSessionManager {
  private sessions = new Map<AudioSource, CaptureSession>();
  private wanted = new Set<AudioSource>();
  private starting = new Map<AudioSource, Promise<void>>();
  private onChunk: ChunkHandler | null = null;
  private onStop: StopHandler | null = null;

  configure(handlers: { onChunk: ChunkHandler; onStop?: StopHandler }) {
    this.onChunk = handlers.onChunk;
    this.onStop = handlers.onStop ?? null;
  }

  isLive(source: AudioSource) {
    const session = this.sessions.get(source);
    return Boolean(session?.stream.getAudioTracks().some((track) => track.readyState === "live"));
  }

  isWanted(source: AudioSource) {
    return this.wanted.has(source);
  }

  snapshot(source: AudioSource) {
    const session = this.sessions.get(source);
    const tracks =
      session?.stream.getAudioTracks().map((track) => ({
        readyState: track.readyState,
        enabled: track.enabled,
        muted: track.muted,
        label: track.label,
      })) ?? [];
    return {
      source,
      wanted: this.wanted.has(source),
      live: this.isLive(source),
      contextState: session?.context.state ?? "none",
      sampleRate: session?.context.sampleRate ?? 0,
      processCount: session?.processCount ?? 0,
      samplesReceived: session?.samplesReceived ?? 0,
      chunksEmitted: session?.chunksEmitted ?? 0,
      silentSkips: session?.silentSkips ?? 0,
      lastRms: session?.lastRms ?? 0,
      lastChunkBytes: session?.lastChunkBytes ?? 0,
      pendingSamples: session?.pendingSamples ?? 0,
      lastSampleAt: session?.lastSampleAt ?? 0,
      tracks,
    };
  }

  async startMic() {
    if (this.wanted.has("mic") && this.isLive("mic")) return;
    await this.start("mic", async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("Microphone capture is not available in this window.");
      }
      return navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });
    });
  }

  async startSystem() {
    if (this.wanted.has("system") && this.isLive("system")) return;
    await this.start("system", async () => {
      if (!navigator.mediaDevices?.getDisplayMedia) {
        throw new Error("System audio capture is not available in this desktop runtime.");
      }
      return navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: true,
      });
    });
  }

  stop(source: AudioSource, reason = "stopped") {
    const session = this.sessions.get(source);
    const before = session ? this.snapshot(source) : { source, wanted: this.wanted.has(source), live: false };
    this.wanted.delete(source);
    this.sessions.delete(source);
    if (session) {
      diag("AUDIO_SESSION_STOP", { source, reason, ...before, ok: false });
      if (session.keepAlive != null) window.clearInterval(session.keepAlive);
      try {
        session.processor.onaudioprocess = null;
        session.processor.disconnect();
        session.input.disconnect();
        session.silent.disconnect();
      } catch {
        // already disconnected
      }
      void session.context.close().catch(() => undefined);
      session.stream.getTracks().forEach((track) => track.stop());
    }
    this.onStop?.(source, reason);
  }

  stopAll() {
    if (this.wanted.has("mic") || this.sessions.has("mic")) this.stop("mic", "app-close");
    if (this.wanted.has("system") || this.sessions.has("system")) this.stop("system", "app-close");
  }

  private async start(source: AudioSource, acquire: () => Promise<MediaStream>) {
    const inflight = this.starting.get(source);
    if (inflight) {
      await inflight;
      if (this.wanted.has(source) && this.isLive(source)) return;
    }
    const run = this.openSession(source, acquire);
    this.starting.set(source, run);
    try {
      await run;
    } finally {
      if (this.starting.get(source) === run) this.starting.delete(source);
    }
  }

  private async openSession(source: AudioSource, acquire: () => Promise<MediaStream>) {
    if (this.wanted.has(source) && this.isLive(source)) return;
    if (this.sessions.has(source)) this.stop(source, "replace");
    this.wanted.add(source);

    let stream: MediaStream;
    try {
      stream = await acquire();
    } catch (error) {
      this.wanted.delete(source);
      throw this.mapAcquireError(source, error);
    }

    const audioTracks = stream.getAudioTracks();
    if (!audioTracks.length) {
      this.wanted.delete(source);
      stream.getTracks().forEach((track) => track.stop());
      throw new Error(
        source === "mic"
          ? "Microphone opened but no audio track was available."
          : "System capture started but no audio track was returned. On Windows, Savuor uses Electron loopback audio."
      );
    }

    const context = new AudioContext();
    if (context.state === "suspended") {
      await context.resume().catch(() => undefined);
    }

    const input = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(4096, 1, 1);
    const silent = context.createGain();
    silent.gain.value = 0;
    const session: CaptureSession = {
      stream,
      context,
      input,
      processor,
      silent,
      pending: [],
      pendingSamples: 0,
      targetSamples: Math.round(context.sampleRate * CHUNK_SECONDS),
      keepAlive: null,
      processCount: 0,
      samplesReceived: 0,
      chunksEmitted: 0,
      silentSkips: 0,
      lastRms: 0,
      lastChunkBytes: 0,
      lastSampleAt: 0,
    };

    session.keepAlive = window.setInterval(() => {
      if (!this.wanted.has(source) || this.sessions.get(source) !== session) return;
      if (context.state === "suspended") {
        diag("AUDIO_CONTEXT_SUSPENDED", { source, ...this.snapshot(source), ok: false });
        void context.resume().catch(() => undefined);
      }
      diag("AUDIO_SAMPLES_DETECTED", {
        source,
        ok: session.processCount > 0,
        ...this.snapshot(source),
      });
    }, 1000);

    processor.onaudioprocess = (event) => {
      if (!this.wanted.has(source) || this.sessions.get(source) !== session) return;
      const inputData = event.inputBuffer.getChannelData(0);
      session.processCount += 1;
      session.samplesReceived += inputData.length;
      session.lastSampleAt = Date.now();
      session.pending.push(new Float32Array(inputData));
      session.pendingSamples += inputData.length;
      if (session.pendingSamples < session.targetSamples) return;
      const samples = concatFloat32(session.pending, session.pendingSamples);
      session.pending = [];
      session.pendingSamples = 0;
      const level = rms(samples);
      session.lastRms = level;
      if (level < SILENCE_RMS) {
        session.silentSkips += 1;
        diag("WAV_CHUNK_SKIPPED_SILENCE", {
          source,
          ok: false,
          rms: level,
          samples: samples.length,
          ...this.snapshot(source),
        });
        return;
      }
      const wav = encodeWav(samples, context.sampleRate);
      session.chunksEmitted += 1;
      session.lastChunkBytes = wav.size;
      diag("WAV_CHUNK_CREATED", {
        source,
        ok: wav.size > 44,
        bytes: wav.size,
        rms: level,
        samples: samples.length,
        chunkIndex: session.chunksEmitted,
        contextState: context.state,
        trackLive: this.isLive(source),
      });
      this.onChunk?.(wav, source);
    };

    input.connect(processor);
    processor.connect(silent);
    silent.connect(context.destination);
    this.sessions.set(source, session);
    slog("audio", "Capture session live", { source, contextState: context.state });
    diag("AUDIO_TRACK_LIVE", { source, ok: true, ...this.snapshot(source) });

    audioTracks.forEach((track) => {
      track.addEventListener("ended", () => {
        if (!this.wanted.has(source)) return;
        const stillLive = stream.getAudioTracks().some((item) => item.readyState === "live");
        diag("AUDIO_TRACK_ENDED", { source, stillLive, readyState: track.readyState });
        if (!stillLive) this.stop(source, "track-ended");
      });
    });
  }

  private mapAcquireError(source: AudioSource, error: unknown): Error {
    const name = error instanceof DOMException ? error.name : "";
    if (name === "NotAllowedError" || name === "PermissionDeniedError") {
      return new Error(
        source === "mic"
          ? "Microphone permission was denied. Enable Microphone access for Savuor in Windows Settings > Privacy & security > Microphone."
          : "System audio permission was denied. Allow screen/audio capture when Windows prompts you."
      );
    }
    if (name === "NotFoundError") {
      return new Error(
        source === "mic" ? "No microphone was found." : "No system audio source was found."
      );
    }
    if (error instanceof Error) return error;
    return new Error("Audio capture failed.");
  }
}

export const audioManager = new AudioSessionManager();
export const audioCapture = audioManager;
