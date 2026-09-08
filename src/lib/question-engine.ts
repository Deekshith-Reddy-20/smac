import { slog } from "./log";

export type QuestionAssessment = {
  isQuestion: boolean;
  complete: boolean;
  confidence: number;
  reason: string;
};

const FILLER =
  /^(ok(ay)?|yeah|yes|yep|no|nope|thanks|thank you|alright|all right|mm+|uh+|um+|hmm+|got it|sounds good|cool|great|nice|sure|right|let'?s (move on|continue|go|start)|yes that'?s good|next( question)?|continue|please stand by|i'?m sorry)\.?$/i;

const QUESTION_START =
  /^(what|why|how|when|where|who|which|can you|could you|would you|do you|did you|are you|have you|is there|explain|tell me|describe|walk me|compare|define|implement|write|design|code|difference)\b/i;

const QUESTION_BODY =
  /\b(tell me about( a time)?|strengths|weaknesses|why should we hire|introduce yourself|your project|system design|walk me through|how would you|what would you)\b/i;

const DANGLING_TAIL =
  /\b(the|a|an|my|your|our|their|this|that|these|those|of|to|for|with|about|and|or|but|if|on|in|at|from|into|can|could|would|please|explain|tell|describe)\.?$/i;

const CONTINUATION =
  /^(and|or|also|plus|including|specifically|especially|,|then|as well as|what (problem|problems|technologies|tech|dataset|data|contribution|exactly|you used)|how (you|did you|was it)|your contribution|in your resume|during your|what your)\b/i;

const INCOMPLETE_STARTERS =
  /^(can you explain|could you explain|tell me about|walk me through|what is|what are|what was|how does|how do|how would you|why did you|why do you|describe)\s*\.?$/i;

export function stabilityMs(): number {
  const raw = Number((import.meta as ImportMeta & { env?: { VITE_QUESTION_STABILITY_MS?: string } }).env?.VITE_QUESTION_STABILITY_MS);
  return Number.isFinite(raw) && raw >= 400 ? raw : 1100;
}

export function incompleteWaitMs(): number {
  const raw = Number((import.meta as ImportMeta & { env?: { VITE_QUESTION_INCOMPLETE_MS?: string } }).env?.VITE_QUESTION_INCOMPLETE_MS);
  return Number.isFinite(raw) && raw >= 1500 ? raw : 3800;
}

export function normalizeQuestion(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function mergeUtterance(previous: string, incoming: string): string {
  const prev = previous.trim();
  const next = incoming.trim();
  if (!prev) return next;
  if (!next) return prev;
  const prevNorm = normalizeQuestion(prev);
  const nextNorm = normalizeQuestion(next);
  if (!nextNorm) return prev;
  if (nextNorm === prevNorm) return prev;
  if (nextNorm.includes(prevNorm) && nextNorm.length > prevNorm.length) return next;
  if (prevNorm.includes(nextNorm)) return prev;

  const prevWords = prevNorm.split(" ");
  const nextWords = nextNorm.split(" ");
  let overlap = 0;
  const max = Math.min(prevWords.length, nextWords.length, 12);
  for (let size = max; size >= 2; size -= 1) {
    if (prevWords.slice(-size).join(" ") === nextWords.slice(0, size).join(" ")) {
      overlap = size;
      break;
    }
  }
  if (overlap) {
    const rest = next.split(/\s+/).slice(overlap).join(" ");
    return `${prev} ${rest}`.replace(/\s+/g, " ").trim();
  }
  return `${prev} ${next}`.replace(/\s+/g, " ").trim();
}

export function assessUtterance(text: string): QuestionAssessment {
  const value = text.replace(/\s+/g, " ").trim();
  const normalized = normalizeQuestion(value);
  if (!normalized) {
    return { isQuestion: false, complete: false, confidence: 0, reason: "empty" };
  }
  if (FILLER.test(value) || FILLER.test(normalized)) {
    return { isQuestion: false, complete: true, confidence: 0.95, reason: "filler" };
  }
  if (normalized.length < 8 || normalized.split(" ").length < 3) {
    return { isQuestion: false, complete: false, confidence: 0.2, reason: "too-short" };
  }

  const hasMark = /\?/.test(value);
  const startsLikeQuestion = QUESTION_START.test(value);
  const bodyLikeQuestion = QUESTION_BODY.test(value);
  const isQuestion = hasMark || startsLikeQuestion || bodyLikeQuestion;
  if (!isQuestion) {
    return { isQuestion: false, complete: false, confidence: 0.15, reason: "not-a-question" };
  }

  if (INCOMPLETE_STARTERS.test(normalized) || INCOMPLETE_STARTERS.test(value.replace(/\?+$/, "").trim())) {
    return { isQuestion: true, complete: false, confidence: 0.35, reason: "incomplete-starter" };
  }
  if (DANGLING_TAIL.test(normalized)) {
    return { isQuestion: true, complete: false, confidence: 0.4, reason: "dangling-tail" };
  }

  const words = normalized.split(" ").length;
  if (hasMark && words >= 3) {
    return { isQuestion: true, complete: true, confidence: 0.92, reason: "question-mark" };
  }
  if (startsLikeQuestion && words >= 6) {
    return { isQuestion: true, complete: true, confidence: 0.82, reason: "complete-starter" };
  }
  if (bodyLikeQuestion && words >= 5) {
    return { isQuestion: true, complete: true, confidence: 0.8, reason: "complete-body" };
  }
  if (startsLikeQuestion && words >= 4 && !DANGLING_TAIL.test(normalized)) {
    return { isQuestion: true, complete: true, confidence: 0.72, reason: "short-complete" };
  }
  return { isQuestion: true, complete: false, confidence: 0.45, reason: "needs-more" };
}

export function isContinuation(text: string): boolean {
  return CONTINUATION.test(text.trim());
}

export function looksLikeNewQuestion(text: string): boolean {
  const value = text.trim();
  if (isContinuation(value)) return false;
  return QUESTION_START.test(value) || /\?/.test(value);
}

export class QuestionEngine {
  private buffer = "";
  private recent: string[] = [];
  private timer: number | null = null;
  private extraWaits = 0;
  private onPartial: ((text: string) => void) | null = null;
  private onComplete: ((text: string) => void) | null = null;
  private onIdle: (() => void) | null = null;

  configure(handlers: {
    onPartial: (text: string) => void;
    onComplete: (text: string) => void;
    onIdle?: () => void;
  }) {
    this.onPartial = handlers.onPartial;
    this.onComplete = handlers.onComplete;
    this.onIdle = handlers.onIdle ?? null;
  }

  reset() {
    this.clearTimer();
    this.buffer = "";
    this.extraWaits = 0;
  }

  forget() {
    this.recent = [];
  }

  isDuplicate(text: string) {
    const normalized = normalizeQuestion(text);
    if (normalized.length < 8) return true;
    return this.recent.some((prev) => prev === normalized);
  }

  remember(text: string) {
    const normalized = normalizeQuestion(text);
    if (!normalized) return;
    this.recent.push(normalized);
    if (this.recent.length > 10) this.recent.shift();
  }

  push(text: string) {
    const incoming = text.replace(/\s+/g, " ").trim();
    if (!incoming) return;

    slog("transcript", "New text received", { chars: incoming.length });

    const current = this.buffer.trim();
    if (
      current &&
      /[?]$/.test(current) &&
      looksLikeNewQuestion(incoming) &&
      !isContinuation(incoming)
    ) {
      slog("detector", "Follow-up detected; finalizing previous question");
      this.finalize();
    }

    this.buffer = mergeUtterance(this.buffer, incoming);
    this.extraWaits = 0;
    const snapshot = this.buffer;
    const assessment = assessUtterance(snapshot);
    slog("detector", "Waiting for utterance completion", {
      complete: assessment.complete,
      isQuestion: assessment.isQuestion,
      reason: assessment.reason,
      chars: snapshot.length,
    });
    if (assessment.isQuestion || snapshot.length >= 12) {
      this.onPartial?.(snapshot);
    }
    this.arm(assessment);
  }

  private arm(assessment: QuestionAssessment) {
    this.clearTimer();
    const wait = assessment.complete ? stabilityMs() : incompleteWaitMs();
    this.timer = window.setTimeout(() => this.onSilence(), wait);
  }

  private onSilence() {
    this.timer = null;
    const snapshot = this.buffer.trim();
    if (!snapshot) {
      this.onIdle?.();
      return;
    }
    const assessment = assessUtterance(snapshot);
    if (assessment.isQuestion && !assessment.complete && this.extraWaits < 1) {
      this.extraWaits += 1;
      slog("detector", "Incomplete question; waiting once more", { reason: assessment.reason });
      this.timer = window.setTimeout(() => this.onSilence(), incompleteWaitMs());
      return;
    }
    if (!assessment.isQuestion || assessment.confidence < 0.55) {
      slog("detector", "Not a complete interview question", {
        reason: assessment.reason,
        confidence: assessment.confidence,
      });
      this.buffer = "";
      this.extraWaits = 0;
      this.onIdle?.();
      return;
    }
    this.finalize();
  }

  private finalize() {
    this.clearTimer();
    const text = this.buffer.replace(/\s+/g, " ").trim();
    this.buffer = "";
    this.extraWaits = 0;
    if (!text) return;
    const assessment = assessUtterance(text);
    if (!assessment.isQuestion || !assessment.complete) {
      this.onIdle?.();
      return;
    }
    if (this.isDuplicate(text)) {
      slog("detector", "Duplicate question ignored");
      this.onIdle?.();
      return;
    }
    slog("detector", "Complete question detected", { chars: text.length, reason: assessment.reason });
    this.remember(text);
    this.onComplete?.(text);
  }

  private clearTimer() {
    if (this.timer != null) {
      window.clearTimeout(this.timer);
      this.timer = null;
    }
  }
}

export const questionEngine = new QuestionEngine();
