import { app } from "electron";
import fs from "node:fs";
import path from "node:path";

export function logsDir() {
  const dir = path.join(app.getPath("userData"), "logs");
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function redact(value: string) {
  return value
    .replace(/gsk_[A-Za-z0-9_-]+/g, "gsk_[redacted]")
    .replace(/GROQ_API_KEY\s*[=:]\s*\S+/gi, "GROQ_API_KEY=[redacted]");
}

export function appendDesktopLog(scope: string, message: string, extra?: Record<string, unknown>) {
  const line = `${new Date().toISOString()} [${scope}] ${redact(message)}${
    extra ? ` ${redact(JSON.stringify(extra))}` : ""
  }\n`;
  try {
    fs.appendFileSync(path.join(logsDir(), "desktop.log"), line, "utf8");
  } catch {
    // ignore
  }
}
