export { normalizeQuestion } from "./question-engine";
import { assessUtterance } from "./question-engine";

export function mightBeInterviewQuestion(text: string): boolean {
  return assessUtterance(text).isQuestion;
}

export function errorMessage(error: unknown, fallback = "Savuor is unavailable. Try again."): string {
  const raw = extractError(error, fallback);
  const lowered = raw.toLowerCase();
  if (
    lowered.includes("failed_generation") ||
    lowered.includes("failed to generate json") ||
    lowered.includes("json_validate") ||
    lowered === "[object object]"
  ) {
    return "Waiting for a clearer question…";
  }
  if (
    lowered.includes("failed to fetch") ||
    lowered.includes("networkerror") ||
    lowered.includes("err_internet")
  ) {
    return "AI service unavailable. Check your Internet connection.";
  }
  return raw;
}

function extractError(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message && error.message !== "[object Object]") {
    return error.message;
  }
  if (typeof error === "string" && error.trim()) return error;
  if (error && typeof error === "object") {
    const record = error as { error?: unknown; message?: unknown };
    if (typeof record.error === "string" && record.error.trim()) return record.error;
    if (typeof record.message === "string" && record.message.trim()) return record.message;
  }
  return fallback;
}
