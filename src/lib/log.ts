/** Structured logs for the interview pipeline. Never log keys or full resumes. */

const PREFIX: Record<string, string> = {
  audio: "[Audio]",
  transcript: "[Transcript]",
  detector: "[QuestionDetector]",
  interview: "[Interview]",
  groq: "[Groq]",
  resume: "[Resume]",
  ui: "[UI]",
};

export function slog(
  scope: keyof typeof PREFIX,
  message: string,
  extra?: Record<string, unknown>
) {
  const label = PREFIX[scope];
  if (extra && Object.keys(extra).length) {
    console.info(label, message, extra);
  } else {
    console.info(label, message);
  }
}
