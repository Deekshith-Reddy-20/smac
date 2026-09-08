import type {
  ActionsResponse,
  AskContext,
  ChatResponse,
  InterviewAnswerResponse,
  TranscribeResponse,
  TranslateResponse,
} from "../types/api";
import { errorMessage } from "../lib/interview";

const DEV_API_BASE = "http://127.0.0.1:8000";
let apiBase = DEV_API_BASE;

export function setApiBase(url: string) {
  if (url?.trim()) apiBase = url.replace(/\/$/, "");
}

export function getApiBase() {
  return apiBase;
}

const unavailable = "Savuor backend could not be started.";

async function readJson<T>(response: Response): Promise<T> {
  try {
    return (await response.json()) as T;
  } catch {
    throw new Error(unavailable);
  }
}

async function postJson<T extends { success: boolean; error?: string }>(
  path: string,
  body: unknown
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBase}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error(unavailable);
  }
  const data = await readJson<T>(response);
  if (!data.success) {
    throw new Error(data.error || unavailable);
  }
  return data;
}

export const AIService = {
  async ask(prompt: string, context?: AskContext) {
    const data = await postJson<ChatResponse>("/api/chat", {
      message: prompt,
      context: context ?? {},
    });
    if (!data.answer) throw new Error(data.error || unavailable);
    return { answer: data.answer, confidence: 0.9 };
  },
};

export const InterviewService = {
  async answer(payload: {
    transcript?: string;
    message?: string;
    ephemeral: boolean;
    session_id: string;
    force?: boolean;
    reset_context?: boolean;
  }) {
    return postJson<InterviewAnswerResponse>("/api/interview/answer", payload);
  },
};

export const TranscriptService = {
  async send(transcript: string) {
    return postJson("/api/transcript", { transcript });
  },
};

export const TranscriptionService = {
  async transcribe(blob: Blob, source: "mic" | "system") {
    const form = new FormData();
    const extension = blob.type.includes("wav") ? "wav" : blob.type.includes("mp4") ? "mp4" : "webm";
    form.append("file", blob, `capture.${extension}`);
    form.append("source", source);
    let response: Response;
    try {
      response = await fetch(`${apiBase}/api/transcribe`, {
        method: "POST",
        body: form,
      });
    } catch {
      throw new Error(unavailable);
    }
    const data = await readJson<TranscribeResponse>(response);
    if (!data.success) throw new Error(data.error || unavailable);
    return data.text || "";
  },
};

export const TranslationService = {
  async translate(text: string, targetLang: string) {
    const data = await postJson<TranslateResponse>("/api/translate", {
      text,
      target_language: targetLang,
    });
    return {
      sourceLang: "en",
      targetLang,
      text: data.translated_text || "",
    };
  },
};

export const ActionsService = {
  async extract(transcript: string) {
    const data = await postJson<ActionsResponse>("/api/actions", { transcript });
    return data.actions ?? [];
  },
};

export const ResumeService = {
  async upload(file: File, sessionId: string) {
    const form = new FormData();
    form.append("file", file);
    form.append("session_id", sessionId);
    let response: Response;
    try {
      response = await fetch(`${apiBase}/api/resume/upload`, {
        method: "POST",
        body: form,
      });
    } catch {
      throw new Error(unavailable);
    }
    const data = await readJson<{
      success: boolean;
      filename?: string;
      characters?: number;
      message?: string;
      error?: string;
    }>(response);
    if (!data.success) throw new Error(data.error || unavailable);
    return data;
  },
};

export { errorMessage };
