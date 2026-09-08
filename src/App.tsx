import { useEffect, useRef, useState, type ChangeEvent, type FormEvent, type ReactNode, type UIEvent } from "react";
import {
  Bookmark,
  Copy,
  ExternalLink,
  EyeOff,
  FileText,
  GripVertical,
  Languages,
  ListTodo,
  Mic,
  Minimize2,
  Pin,
  Presentation,
  RefreshCw,
  Search,
  Settings,
  Shield,
  Sparkles,
  Volume2,
  X,
} from "lucide-react";
import { cn } from "./lib/utils";
import { errorMessage } from "./lib/interview";
import { questionEngine } from "./lib/question-engine";
import { slog } from "./lib/log";
import { useCompanionStore } from "./store/companion-store";
import {
  ActionsService,
  InterviewService,
  ResumeService,
  TranscriptService,
  TranscriptionService,
  TranslationService,
  setApiBase,
} from "./services";
import { audioManager } from "./services/audio";
import { diag, pollDiagCommand } from "./services/diag";
import type { ActionItem, ChatMessage, TranscriptLine } from "./types/api";

export default function App() {
  const {
    mode,
    pinned,
    opacity,
    panel,
    session,
    capture,
    setMode,
    setPinned,
    setOpacity,
    setPanel,
    setSession,
    setCapture,
  } = useCompanionStore();

  const [ask, setAsk] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [confidence, setConfidence] = useState(0);
  const [bookmarkCount, setBookmarkCount] = useState(2);
  const [translated, setTranslated] = useState<string | null>(null);
  const [micOn, setMicOn] = useState(false);
  const [systemOn, setSystemOn] = useState(false);
  const [ephemeralOn, setEphemeralOn] = useState(true);
  const [lines, setLines] = useState<TranscriptLine[]>([]);
  const [actionItems, setActionItems] = useState<ActionItem[]>([]);
  const [captureError, setCaptureError] = useState<string | null>(null);
  const [resumeName, setResumeName] = useState<string | null>(null);
  const [appReady, setAppReady] = useState(false);
  const [packaged, setPackaged] = useState(false);
  const [needsSetup, setNeedsSetup] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [groqKeyInput, setGroqKeyInput] = useState("");
  const [setupError, setSetupError] = useState<string | null>(null);
  const [setupSaving, setSetupSaving] = useState(false);

  const sessionIdRef = useRef(crypto.randomUUID());
  const ephemeralRef = useRef(true);
  const systemOnRef = useRef(false);
  const micOnRef = useRef(false);
  const resetContextRef = useRef(false);
  const answeringRef = useRef(false);
  const transcribeChain = useRef(Promise.resolve());
  const answerQueue = useRef<Array<{ transcript?: string; message?: string }>>([]);
  const stickToBottom = useRef(true);
  const answerRef = useRef<HTMLDivElement>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const resumeInputRef = useRef<HTMLInputElement>(null);
  const handleChunkRef = useRef<(blob: Blob, source: "mic" | "system") => void>(() => undefined);
  const pendingInterviewerIdRef = useRef<string | null>(null);
  const enqueueAnswerRef = useRef<(payload: { transcript?: string; message?: string }) => void>(() => undefined);

  const latestAnswer =
    [...messages].reverse().find((item) => item.role === "savuor" && !item.pending)?.content ||
    "Waiting for an interview question…";

  useEffect(() => {
    void (async () => {
      const runtime = await window.cueai?.getRuntime?.();
      if (runtime?.apiBase) setApiBase(runtime.apiBase);
      setPackaged(Boolean(runtime?.packaged));
      if (runtime?.backendError) {
        setBackendError(runtime.backendError);
        setAppReady(true);
        return;
      }
      setNeedsSetup(Boolean(runtime?.packaged) && !runtime?.hasApiKey);
      setAppReady(true);
    })();
  }, []);

  useEffect(() => {
    void window.cueai?.setMode(mode);
  }, [mode]);

  useEffect(() => {
    void window.cueai?.pin(pinned);
  }, [pinned]);

  useEffect(() => {
    void window.cueai?.setOpacity(opacity);
  }, [opacity]);

  useEffect(() => {
    void window.cueai?.getCaptureStatus().then((s) => s && setCapture(s));
    void window.cueai?.getSession().then((s) => s && setSession(s));
    const offMode = window.cueai?.onMode((m) => setMode(m));
    const offSession = window.cueai?.onSession((s) => setSession(s));
    const offCapture = window.cueai?.onCaptureStatus((s) => setCapture(s));
    return () => {
      offMode?.();
      offSession?.();
      offCapture?.();
    };
  }, [setCapture, setMode, setSession]);

  useEffect(() => {
    ephemeralRef.current = ephemeralOn;
  }, [ephemeralOn]);

  useEffect(() => {
    systemOnRef.current = systemOn;
  }, [systemOn]);

  useEffect(() => {
    micOnRef.current = micOn;
  }, [micOn]);

  useEffect(() => {
    audioManager.configure({
      onChunk: (blob, source) => handleChunkRef.current(blob, source),
      onStop: (source, reason) => {
        if (reason === "replace") return;
        if (source === "mic") setMicOn(false);
        if (source === "system") setSystemOn(false);
        if (reason === "track-ended") {
          setCaptureError(
            source === "system"
              ? "System audio source ended. Turn System on again to reconnect."
              : "Microphone source ended. Turn Mic on again to reconnect."
          );
        }
      },
    });
    questionEngine.configure({
      onPartial: (text) => {
        slog("ui", "Listening for complete question");
        setPanel("answer");
        stickToBottom.current = true;
        setMessages((current) => upsertPendingInterviewer(current, text, pendingInterviewerIdRef));
      },
      onComplete: (text) => {
        slog("detector", "Complete question detected");
        setPanel("answer");
        stickToBottom.current = true;
        setMessages((current) => finalizePendingInterviewer(current, text, pendingInterviewerIdRef));
        enqueueAnswerRef.current({ transcript: text });
      },
      onIdle: () => {
        setMessages((current) => dropPendingInterviewer(current, pendingInterviewerIdRef));
      },
    });
    const cleanup = () => audioManager.stopAll();
    window.addEventListener("beforeunload", cleanup);
    const sync = window.setInterval(() => {
      setMicOn(audioManager.isWanted("mic") && audioManager.isLive("mic"));
      setSystemOn(audioManager.isWanted("system") && audioManager.isLive("system"));
    }, 1500);
    const commands = packaged
      ? 0
      : window.setInterval(() => {
      void (async () => {
        const command = await pollDiagCommand();
        const action = typeof command?.action === "string" ? command.action : "";
        if (!action) return;
        diag("DIAG_COMMAND", { action });
        try {
          if (action === "start-system") {
            if (!audioManager.isWanted("system") || !audioManager.isLive("system")) {
              await audioManager.startSystem();
              setSystemOn(true);
            }
            diag("AUDIO_TRACK_LIVE", { ...audioManager.snapshot("system"), ok: audioManager.isLive("system") });
          } else if (action === "start-mic") {
            if (!audioManager.isWanted("mic") || !audioManager.isLive("mic")) {
              await audioManager.startMic();
              setMicOn(true);
            }
            diag("AUDIO_TRACK_LIVE", { ...audioManager.snapshot("mic"), ok: audioManager.isLive("mic") });
          } else if (action === "stop-system") {
            audioManager.stop("system", "diag");
            setSystemOn(false);
          } else if (action === "stop-mic") {
            audioManager.stop("mic", "diag");
            setMicOn(false);
          } else if (action === "snapshot") {
            diag("SNAPSHOT", {
              mic: audioManager.snapshot("mic"),
              system: audioManager.snapshot("system"),
            });
          } else if (action === "reload") {
            window.location.reload();
          }
        } catch (error) {
          const message = errorMessage(error, "Diagnostic capture command failed.");
          diag("DIAG_COMMAND_ERROR", { action, error: message, ok: false });
          setCaptureError(message);
        }
      })();
    }, 400);
    return () => {
      window.removeEventListener("beforeunload", cleanup);
      window.clearInterval(sync);
      window.clearInterval(commands);
    };
  }, [packaged]);

  useEffect(() => {
    const el = answerRef.current;
    if (el && stickToBottom.current) el.scrollTop = el.scrollHeight;
  }, [messages, streaming]);

  useEffect(() => {
    const el = transcriptRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines]);

  useEffect(() => {
    if (panel !== "actions") return;
    const transcript = lines.map((line) => line.text).join("\n");
    if (!transcript.trim()) {
      setActionItems([]);
      return;
    }
    void ActionsService.extract(transcript)
      .then(setActionItems)
      .catch(() => setActionItems([]));
  }, [panel, lines]);

  function bumpActivity() {
    void window.cueai?.activity();
  }

  function onAnswerScroll(event: UIEvent<HTMLDivElement>) {
    const el = event.currentTarget;
    stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 48;
  }

  async function handleAudioChunk(blob: Blob, source: "mic" | "system") {
    const snapBefore = audioManager.snapshot(source);
    diag("TRANSCRIPTION_REQUEST_SENT", {
      source,
      ok: blob.size > 44,
      bytes: blob.size,
      type: blob.type,
      ...snapBefore,
    });
    try {
      const text = await TranscriptionService.transcribe(blob, source);
      diag("TRANSCRIPTION_TEXT_RECEIVED", {
        source,
        ok: Boolean(text.trim()),
        chars: text.trim().length,
        text: text.trim().slice(0, 240),
      });
      if (!text.trim()) return;
      slog("transcript", "New text received", { source, chars: text.trim().length });
      const line: TranscriptLine = {
        id: crypto.randomUUID(),
        source,
        text: text.trim(),
      };
      setLines((current) => [...current, line].slice(-80));
      void TranscriptService.send(line.text).catch(() => undefined);

      const shouldAutoAnswer =
        source === "system" || (source === "mic" && !systemOnRef.current);
      if (!shouldAutoAnswer) {
        slog("detector", "Skipping auto-answer while system audio is active");
        return;
      }
      questionEngine.push(text);
    } catch (error) {
      diag("TRANSCRIPTION_FAILED", {
        source,
        ok: false,
        error: errorMessage(error, "A transcript chunk failed; still listening."),
      });
      setCaptureError(errorMessage(error, "A transcript chunk failed; still listening."));
    }
  }

  handleChunkRef.current = (blob, source) => {
    transcribeChain.current = transcribeChain.current
      .then(() => handleAudioChunk(blob, source))
      .catch(() => undefined);
  };

  function enqueueAnswer(payload: { transcript?: string; message?: string }) {
    if (answerQueue.current.length >= 3) answerQueue.current.shift();
    answerQueue.current.push(payload);
    void pumpAnswers();
  }
  enqueueAnswerRef.current = enqueueAnswer;

  async function pumpAnswers() {
    if (answeringRef.current) return;
    const next = answerQueue.current.shift();
    if (!next) return;
    answeringRef.current = true;
    setStreaming(true);
    setPanel("answer");
    stickToBottom.current = true;
    const questionText = next.transcript || next.message || "";
    slog("interview", "Generating answer");
    diag("GROQ_REQUEST_SENT", {
      ok: true,
      transcript: (next.transcript || "").slice(0, 240),
      message: (next.message || "").slice(0, 240),
      mic: audioManager.snapshot("mic"),
      system: audioManager.snapshot("system"),
    });
    try {
      const result = await InterviewService.answer({
        transcript: next.transcript,
        message: next.message,
        ephemeral: ephemeralRef.current,
        session_id: sessionIdRef.current,
        force: Boolean(next.message),
        reset_context: resetContextRef.current,
      });
      resetContextRef.current = false;
      const spoken = result.answer?.interview_answer?.trim() || "";
      const status = result.status || (result.is_question && spoken ? "answer" : "skip");
      slog("interview", "Answer validated", { status, chars: spoken.length });
      diag("GROQ_RESPONSE_RECEIVED", {
        ok: status === "answer" && Boolean(spoken),
        is_question: result.is_question,
        question: (result.question || "").slice(0, 240),
        category: result.category,
        chars: spoken.length,
      });
      if (status === "answer" && spoken) {
        questionEngine.remember(result.question || questionText);
        const answerMessage: ChatMessage = {
          id: crypto.randomUUID(),
          role: "savuor",
          content: spoken,
          timestamp: new Date().toISOString(),
          category: result.category,
          confidence: result.confidence || 0.9,
        };
        setMessages((current) => [...current, answerMessage].slice(-40));
        setConfidence(result.confidence || 0.9);
        setTranslated(null);
        slog("ui", "Answer appended");
        diag("ANSWER_DISPLAYED", {
          ok: true,
          question: (result.question || questionText).slice(0, 240),
          chars: spoken.length,
          system: audioManager.snapshot("system"),
          mic: audioManager.snapshot("mic"),
        });
        diag("AUDIO_TRACK_STILL_LIVE", {
          ok: audioManager.isLive("system") || audioManager.isLive("mic"),
          system: audioManager.snapshot("system"),
          mic: audioManager.snapshot("mic"),
        });
      } else if (status === "unclear") {
        slog("interview", "Question unclear; continuing to listen");
        setMessages((current) => dropPendingInterviewer(current, pendingInterviewerIdRef));
      }
    } catch (error) {
      const message = errorMessage(error);
      slog("groq", "Response failed", { error: message });
      diag("GROQ_RESPONSE_RECEIVED", { ok: false, error: message });
      if (next.message) {
        setMessages((current) => [
          ...current,
          {
            id: crypto.randomUUID(),
            role: "savuor",
            content: message,
            timestamp: new Date().toISOString(),
          },
        ]);
      }
      setConfidence(0);
    } finally {
      answeringRef.current = false;
      setStreaming(false);
      if (answerQueue.current.length) void pumpAnswers();
    }
  }

  async function toggleMic() {
    bumpActivity();
    setCaptureError(null);
    if (audioManager.isWanted("mic") || audioManager.isLive("mic")) {
      audioManager.stop("mic");
      setMicOn(false);
      return;
    }
    try {
      await audioManager.startMic();
      setMicOn(true);
    } catch (error) {
      setMicOn(false);
      setCaptureError(errorMessage(error, "Could not start the microphone."));
    }
  }

  async function toggleSystem() {
    bumpActivity();
    setCaptureError(null);
    if (audioManager.isWanted("system") || audioManager.isLive("system")) {
      audioManager.stop("system");
      setSystemOn(false);
      return;
    }
    try {
      await audioManager.startSystem();
      setSystemOn(true);
    } catch (error) {
      setSystemOn(false);
      setCaptureError(errorMessage(error, "Could not start system audio capture."));
    }
  }

  function toggleEphemeral() {
    bumpActivity();
    setEphemeralOn((current) => {
      const next = !current;
      if (next) {
        resetContextRef.current = true;
        questionEngine.forget();
      }
      return next;
    });
  }

  async function onResumeSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    bumpActivity();
    try {
      const result = await ResumeService.upload(file, sessionIdRef.current);
      setResumeName(result.filename || file.name);
      slog("resume", "Resume uploaded", { filename: result.filename || file.name });
      setCaptureError(null);
    } catch (error) {
      setResumeName(null);
      setCaptureError(errorMessage(error, "Could not upload the resume."));
    }
  }

  async function saveGroqKey() {
    const key = groqKeyInput.trim();
    if (!key || setupSaving) return;
    setSetupSaving(true);
    setSetupError(null);
    try {
      const result = await window.cueai?.saveGroqKey?.(key);
      setGroqKeyInput("");
      if (!result?.success) {
        setSetupError(result?.error || "Groq API key is invalid. Please check the key and try again.");
        return;
      }
      setNeedsSetup(false);
      setSettingsOpen(false);
      setCaptureError(null);
    } catch {
      setSetupError("Groq API key is invalid. Please check the key and try again.");
    } finally {
      setSetupSaving(false);
    }
  }

  async function onAsk(e: FormEvent) {
    e.preventDefault();
    const prompt = ask.trim();
    if (!prompt || streaming) return;
    setAsk("");
    bumpActivity();
    setLines((current) => [
      ...current,
      { id: crypto.randomUUID(), source: "typed", text: prompt },
    ]);
    const interviewer: ChatMessage = {
      id: crypto.randomUUID(),
      role: "interviewer",
      content: prompt,
      timestamp: new Date().toISOString(),
    };
    pendingInterviewerIdRef.current = null;
    setMessages((current) => [...current, interviewer].slice(-40));
    setPanel("answer");
    stickToBottom.current = true;
    enqueueAnswer({ message: prompt, transcript: prompt });
  }

  const presenting = mode === "presenter" || session.screenSharing;

  return (
    <div
      className="flex h-full flex-col p-2"
      onMouseMove={bumpActivity}
      onFocus={bumpActivity}
    >
      <div
        className={cn(
          "glass flex h-full flex-col overflow-hidden rounded-2xl transition-[box-shadow,opacity] duration-150",
          "shadow-[0_0_0_1px_rgba(45,212,191,0.25),0_0_24px_rgba(20,184,166,0.18)]",
          presenting && "shadow-[0_0_0_1px_rgba(45,212,191,0.15)]",
          mode === "collapsed" && "justify-center"
        )}
      >
        <header className="drag-region flex items-center gap-2 border-b border-white/10 px-3 py-2">
          <GripVertical className="h-4 w-4 text-zinc-500" />
          <Sparkles className="h-3.5 w-3.5 text-teal-400" />
          <span className="text-xs font-semibold tracking-tight">Savuor</span>
          {session.cueAiMode === "private" && (
            <span
              className={cn(
                "rounded-md border px-1.5 py-0.5 text-[10px] font-medium",
                capture?.applied
                  ? "border-teal-500/30 bg-teal-500/15 text-teal-300"
                  : "border-amber-500/30 bg-amber-500/10 text-amber-200"
              )}
              title={capture?.message || "Capture status"}
            >
              <span className="inline-flex items-center gap-1">
                <EyeOff className="h-2.5 w-2.5" /> Private
              </span>
            </span>
          )}
          {session.cueAiMode === "live" && (
            <span className="rounded-md border border-teal-500/20 bg-teal-500/10 px-1.5 py-0.5 text-[10px] text-teal-300">
              Live
            </span>
          )}
          {(!session.cueAiMode || session.cueAiMode === "inactive") && capture?.applied === false && (
            <span className="rounded-md border border-white/10 px-1.5 py-0.5 text-[10px] text-zinc-500">
              Local only
            </span>
          )}
          <div className="no-drag ml-auto flex items-center gap-0.5">
            <IconBtn
              label={pinned ? "Unpin" : "Pin always on top"}
              onClick={() => {
                bumpActivity();
                setPinned(!pinned);
              }}
            >
              <Pin className={cn("h-3.5 w-3.5", pinned && "text-teal-400")} />
            </IconBtn>
            <IconBtn
              label="Presenter mode"
              onClick={() => {
                bumpActivity();
                setMode(mode === "presenter" ? "full" : "presenter");
              }}
            >
              <Presentation className={cn("h-3.5 w-3.5", presenting && "text-teal-400")} />
            </IconBtn>
            {!presenting && (
              <IconBtn
                label="Mini"
                onClick={() => {
                  bumpActivity();
                  setMode(mode === "mini" ? "full" : "mini");
                }}
              >
                <Minimize2 className="h-3.5 w-3.5" />
              </IconBtn>
            )}
            <IconBtn
              label="Settings"
              onClick={() => {
                bumpActivity();
                setSettingsOpen((open) => !open);
              }}
            >
              <Settings className={cn("h-3.5 w-3.5", settingsOpen && "text-teal-400")} />
            </IconBtn>
            <IconBtn label="Hide" onClick={() => void window.cueai?.hide()}>
              <X className="h-3.5 w-3.5" />
            </IconBtn>
          </div>
        </header>

        {(!appReady || backendError || needsSetup || settingsOpen) && (
          <div className="no-drag flex min-h-0 flex-1 flex-col justify-center gap-3 p-4">
            {!appReady && !backendError && (
              <p className="text-center text-xs text-zinc-400">Starting Savuor…</p>
            )}
            {backendError && (
              <div className="space-y-2 text-center">
                <p className="text-sm font-medium text-zinc-100">Savuor backend could not be started.</p>
                <p className="text-[11px] text-zinc-500">Close any other Savuor window and try again.</p>
                <button
                  type="button"
                  className="text-[11px] text-teal-300 hover:text-teal-200"
                  onClick={() => void window.cueai?.openLogs?.()}
                >
                  Open logs
                </button>
              </div>
            )}
            {appReady && !backendError && (needsSetup || settingsOpen) && (
              <div className="space-y-3">
                <div>
                  <p className="text-sm font-semibold text-zinc-100">
                    {needsSetup ? "Welcome to Savuor" : "Groq API Key"}
                  </p>
                  <p className="mt-1 text-[11px] leading-relaxed text-zinc-400">
                    {needsSetup
                      ? "Add your Groq API key to start using AI interview assistance."
                      : "Stored securely on this computer. It is never bundled with the installer."}
                  </p>
                </div>
                <label className="block text-[11px] text-zinc-400">
                  Groq API Key
                  <input
                    type="password"
                    autoComplete="off"
                    value={groqKeyInput}
                    onChange={(event) => setGroqKeyInput(event.target.value)}
                    placeholder="Paste your key"
                    className="mt-1 h-9 w-full rounded-xl border border-white/10 bg-black/30 px-3 text-xs text-white outline-none placeholder:text-zinc-600 focus:border-teal-500/50"
                  />
                </label>
                {setupError && <p className="text-[11px] text-amber-200">{setupError}</p>}
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={setupSaving || !groqKeyInput.trim()}
                    onClick={() => void saveGroqKey()}
                    className="btn-gradient h-8 rounded-xl px-3 text-xs font-medium text-white disabled:opacity-60"
                  >
                    {needsSetup ? "Save & Continue" : "Save"}
                  </button>
                  {!needsSetup && (
                    <button
                      type="button"
                      className="h-8 rounded-xl px-2 text-[11px] text-zinc-500 hover:text-zinc-300"
                      onClick={() => {
                        setSettingsOpen(false);
                        setGroqKeyInput("");
                        setSetupError(null);
                      }}
                    >
                      Close
                    </button>
                  )}
                  <button
                    type="button"
                    className="ml-auto text-[11px] text-zinc-500 hover:text-zinc-300"
                    onClick={() => void window.cueai?.openLogs?.()}
                  >
                    Open logs
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {appReady && !backendError && !needsSetup && !settingsOpen && (mode === "collapsed" ? (
          <div className="flex items-center justify-between px-4 py-3">
            <div className="flex items-center gap-2 text-xs text-zinc-400">
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-teal-400 opacity-60" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-teal-400" />
              </span>
              Listening · private
            </div>
            <button
              className="no-drag rounded-lg px-2 py-1 text-[10px] text-zinc-400 hover:bg-white/5"
              onClick={() => setMode("full")}
            >
              Expand
            </button>
          </div>
        ) : (
          <div className="no-drag flex min-h-0 flex-1 flex-col gap-2.5 p-3">
            {mode === "full" && (
              <div className="flex items-center gap-3 text-[11px] text-zinc-400">
                <button
                  type="button"
                  aria-pressed={micOn}
                  title={micOn ? "Stop microphone" : "Start microphone"}
                  onClick={() => void toggleMic()}
                  className={cn(
                    "inline-flex items-center gap-1",
                    micOn ? "text-teal-400" : "text-zinc-500"
                  )}
                >
                  <Mic className="h-3 w-3" /> Mic
                </button>
                <button
                  type="button"
                  aria-pressed={systemOn}
                  title={systemOn ? "Stop system audio" : "Start system audio"}
                  onClick={() => void toggleSystem()}
                  className={cn(
                    "inline-flex items-center gap-1",
                    systemOn ? "text-teal-400" : "text-zinc-500"
                  )}
                >
                  <Volume2 className="h-3 w-3" /> System
                </button>
                <button
                  type="button"
                  aria-pressed={ephemeralOn}
                  title={
                    ephemeralOn
                      ? "Ephemeral on: short-lived context only"
                      : "Ephemeral off: keep recent interview context"
                  }
                  onClick={toggleEphemeral}
                  className={cn(
                    "inline-flex items-center gap-1",
                    ephemeralOn ? "text-teal-300" : "text-zinc-500"
                  )}
                >
                  <Shield className="h-3 w-3" /> Ephemeral
                </button>
                <button
                  type="button"
                  title={resumeName ? `Resume: ${resumeName}` : "Upload resume (PDF, DOCX, TXT)"}
                  onClick={() => resumeInputRef.current?.click()}
                  className={cn(
                    "inline-flex items-center gap-1",
                    resumeName ? "text-teal-400" : "text-zinc-500"
                  )}
                >
                  <FileText className="h-3 w-3" /> Resume
                </button>
                <input
                  ref={resumeInputRef}
                  type="file"
                  accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
                  className="hidden"
                  onChange={(event) => void onResumeSelected(event)}
                />
                <label className="ml-auto inline-flex items-center gap-1.5">
                  <span className="text-zinc-500">Opacity</span>
                  <input
                    type="range"
                    min={0.5}
                    max={1}
                    step={0.05}
                    value={opacity}
                    onChange={(e) => setOpacity(Number(e.target.value))}
                    className="w-16 accent-teal-500"
                    aria-label="Window opacity"
                  />
                </label>
              </div>
            )}

            {mode === "full" && captureError && (
              <p className="text-[11px] leading-relaxed text-amber-200">{captureError}</p>
            )}

            {mode === "full" && (
              <div className="flex gap-1">
                {(
                  [
                    ["answer", "Answer"],
                    ["transcript", "Transcript"],
                    ["actions", "Actions"],
                    ["translate", "Translate"],
                  ] as const
                ).map(([id, label]) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => {
                      bumpActivity();
                      setPanel(id);
                    }}
                    className={cn(
                      "rounded-lg px-2 py-1 text-[11px]",
                      panel === id
                        ? "bg-teal-500/20 text-teal-200"
                        : "text-zinc-500 hover:bg-white/5 hover:text-zinc-300"
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}

            {mode === "full" && panel === "transcript" && (
              <div
                ref={transcriptRef}
                className="scroll-panel max-h-36 space-y-1.5 overflow-y-auto rounded-xl bg-black/25 p-2.5 text-xs"
              >
                {lines.length === 0 ? (
                  <p className="text-zinc-500">
                    {captureError || "No live transcript yet. Enable Mic or System to start."}
                  </p>
                ) : (
                  lines.map((line) => (
                    <p key={line.id}>
                      <span className="font-medium text-teal-400">
                        {line.source === "system"
                          ? "Interviewer"
                          : line.source === "mic"
                            ? "You"
                            : "Ask"}
                        :
                      </span>{" "}
                      <span className="text-zinc-300">{line.text}</span>
                    </p>
                  ))
                )}
              </div>
            )}

            {mode === "full" && panel === "actions" && (
              <div className="scroll-panel max-h-36 space-y-1.5 overflow-y-auto rounded-xl bg-black/25 p-2.5 text-xs text-zinc-300">
                <p className="inline-flex items-center gap-1.5 text-teal-300">
                  <ListTodo className="h-3 w-3" /> Suggested next steps
                </p>
                {actionItems.length === 0 ? (
                  <p className="text-zinc-500">No action items yet. Capture a transcript first.</p>
                ) : (
                  actionItems.map((item) => (
                    <button
                      key={item.task}
                      type="button"
                      className="block w-full rounded-lg px-2 py-1.5 text-left hover:bg-white/5"
                      onClick={() => {
                        setAsk(item.task);
                        setPanel("answer");
                      }}
                    >
                      {item.task}
                      <span className="ml-2 text-[10px] uppercase text-zinc-500">{item.priority}</span>
                    </button>
                  ))
                )}
                <p className="pt-1 text-[10px] text-zinc-500">From live transcript</p>
              </div>
            )}

            {mode === "full" && panel === "translate" && (
              <div className="space-y-2 rounded-xl bg-black/25 p-2.5 text-xs">
                <p className="inline-flex items-center gap-1 text-teal-300">
                  <Languages className="h-3 w-3" /> Live translation
                </p>
                <div className="flex gap-1">
                  {["es", "fr", "de", "ja"].map((lang) => (
                    <button
                      key={lang}
                      type="button"
                      className="rounded-lg border border-white/10 px-2 py-1 uppercase text-zinc-400 hover:border-teal-500/40 hover:text-teal-200"
                      onClick={() => {
                        void TranslationService.translate(latestAnswer, lang)
                          .then((r) => setTranslated(r.text))
                          .catch((error) => setTranslated(errorMessage(error)));
                      }}
                    >
                      {lang}
                    </button>
                  ))}
                </div>
                <p className="scroll-panel max-h-24 overflow-y-auto text-zinc-300">
                  {translated || latestAnswer}
                </p>
              </div>
            )}

            {(panel === "answer" || mode !== "full") && (
              <div
                className={cn(
                  "flex min-h-0 flex-col rounded-2xl border border-teal-500/25 bg-teal-500/10 p-3",
                  presenting && "flex-1 border-teal-500/15 bg-teal-500/8"
                )}
              >
                <div className="mb-1 flex items-center gap-1.5 text-[11px] font-medium text-teal-300">
                  <Sparkles className="h-3 w-3" />
                  {presenting ? "Presenter answer" : "AI Answer"}
                  {streaming && (
                    <span className="ml-auto text-[10px] text-zinc-500">Answering…</span>
                  )}
                  {!streaming && confidence > 0 && (
                    <span className="ml-auto text-[10px] text-zinc-500">
                      {Math.round(confidence * 100)}%
                    </span>
                  )}
                </div>
                <div
                  ref={answerRef}
                  onScroll={onAnswerScroll}
                  onWheel={(event) => event.stopPropagation()}
                  className={cn(
                    "answer-scroll min-h-0 space-y-2 pr-1",
                    presenting && "h-full max-h-full flex-1"
                  )}
                >
                  {mode === "mini" ? (
                    <p className="text-xs leading-relaxed text-zinc-100">{latestAnswer}</p>
                  ) : messages.length === 0 && !streaming ? (
                    <p className="text-sm leading-relaxed text-zinc-100">{latestAnswer}</p>
                  ) : (
                    messages.map((item) => (
                      <div
                        key={item.id}
                        className={cn(
                          "chat-row",
                          item.role === "interviewer" ? "chat-row-interviewer" : "chat-row-savuor"
                        )}
                      >
                        <div
                          className={cn(
                            "chat-bubble",
                            item.role === "interviewer" ? "chat-bubble-interviewer" : "chat-bubble-savuor"
                          )}
                        >
                          <p className="text-[10px] font-medium text-teal-300">
                            {item.role === "interviewer" ? "Interviewer" : "Savuor"}
                            {item.pending ? (
                              <span className="ml-2 text-zinc-500">Listening…</span>
                            ) : null}
                          </p>
                          <p className="mt-1 text-sm leading-relaxed text-zinc-100">{item.content}</p>
                        </div>
                      </div>
                    ))
                  )}
                  {streaming && (
                    <div className="flex gap-1 py-2" aria-label="Generating answer">
                      {[0, 1, 2].map((i) => (
                        <span
                          key={i}
                          className="typing-dot h-2 w-2 rounded-full bg-teal-400"
                          style={{ animationDelay: `${i * 0.2}s` }}
                        />
                      ))}
                    </div>
                  )}
                </div>
                {!streaming && mode !== "mini" && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    <Chip
                      onClick={() => {
                        bumpActivity();
                        setBookmarkCount((n) => n + 1);
                      }}
                    >
                      <Pin className="h-3 w-3" /> Pin
                    </Chip>
                    <Chip onClick={() => void navigator.clipboard.writeText(latestAnswer)}>
                      <Copy className="h-3 w-3" />
                    </Chip>
                    <Chip
                      onClick={() => {
                        void enqueueAnswer({
                          message: "Regenerate the previous answer more clearly.",
                        });
                      }}
                    >
                      <RefreshCw className="h-3 w-3" />
                    </Chip>
                    {!presenting && (
                      <>
                        <Chip onClick={() => setBookmarkCount((n) => n + 1)}>
                          <Bookmark className="h-3 w-3" /> {bookmarkCount}
                        </Chip>
                        <Chip onClick={() => setAsk("Explain this simply")}>
                          <Search className="h-3 w-3" /> Explain
                        </Chip>
                      </>
                    )}
                  </div>
                )}
              </div>
            )}

            {!presenting && mode !== "mini" && (
              <form className="flex gap-2" onSubmit={(e) => void onAsk(e)}>
                <input
                  value={ask}
                  onChange={(e) => setAsk(e.target.value)}
                  placeholder="Ask Savuor…"
                  disabled={streaming}
                  className="h-9 flex-1 rounded-xl border border-white/10 bg-black/30 px-3 text-xs text-white outline-none placeholder:text-zinc-500 focus:border-teal-500/50 disabled:opacity-60"
                />
                <button
                  type="submit"
                  disabled={streaming}
                  className="btn-gradient h-9 rounded-xl px-3 text-xs font-medium text-white disabled:opacity-60"
                >
                  Ask
                </button>
              </form>
            )}

            {mode === "full" && panel === "answer" && (
              <div className="flex flex-wrap items-center gap-1.5">
                {(["Summarize", "Actions", "Risks"] as const).map((q) => (
                  <button
                    key={q}
                    type="button"
                    className="rounded-lg border border-white/10 px-2 py-1 text-[11px] text-zinc-400 hover:border-white/20 hover:text-white"
                    onClick={() => setAsk(q)}
                  >
                    {q}
                  </button>
                ))}
                <button
                  type="button"
                  className="ml-auto inline-flex items-center gap-1 text-[10px] text-zinc-500 hover:text-zinc-300"
                  onClick={() => void window.cueai?.openLogs?.()}
                >
                  Logs <ExternalLink className="h-3 w-3" />
                </button>
              </div>
            )}

            {mode === "mini" && (
              <button
                type="button"
                className="text-[10px] text-zinc-500 hover:text-zinc-300"
                onClick={() => setMode("collapsed")}
              >
                Collapse · Esc hides
              </button>
            )}

            {presenting && (
              <p className="text-center text-[10px] text-zinc-500">
                Docked · reduced UI · capture exclusion when OS allows
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function IconBtn({
  children,
  onClick,
  label,
}: {
  children: ReactNode;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className="rounded-lg p-1.5 text-zinc-400 hover:bg-white/5 hover:text-white"
    >
      {children}
    </button>
  );
}

function Chip({
  children,
  onClick,
}: {
  children: ReactNode;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-black/20 px-2 py-1 text-[11px] text-zinc-300 hover:border-white/20"
    >
      {children}
    </button>
  );
}

function upsertPendingInterviewer(
  current: ChatMessage[],
  text: string,
  idRef: { current: string | null }
): ChatMessage[] {
  const pendingId = idRef.current;
  if (pendingId) {
    return current.map((item) =>
      item.id === pendingId ? { ...item, content: text, pending: true } : item
    );
  }
  const created: ChatMessage = {
    id: crypto.randomUUID(),
    role: "interviewer",
    content: text,
    timestamp: new Date().toISOString(),
    pending: true,
  };
  idRef.current = created.id;
  return [...current, created].slice(-40);
}

function finalizePendingInterviewer(
  current: ChatMessage[],
  text: string,
  idRef: { current: string | null }
): ChatMessage[] {
  const pendingId = idRef.current;
  idRef.current = null;
  if (pendingId && current.some((item) => item.id === pendingId)) {
    return current.map((item) =>
      item.id === pendingId ? { ...item, content: text, pending: false } : item
    );
  }
  return [
    ...current,
    {
      id: crypto.randomUUID(),
      role: "interviewer",
      content: text,
      timestamp: new Date().toISOString(),
    },
  ].slice(-40);
}

function dropPendingInterviewer(
  current: ChatMessage[],
  idRef: { current: string | null }
): ChatMessage[] {
  const pendingId = idRef.current;
  if (!pendingId) return current;
  idRef.current = null;
  return current.filter((item) => item.id !== pendingId);
}
