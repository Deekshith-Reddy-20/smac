import { app, safeStorage } from "electron";
import fs from "node:fs";
import path from "node:path";

function credentialPath() {
  return path.join(app.getPath("userData"), "credentials.bin");
}

export function saveGroqKey(key: string) {
  const value = key.trim();
  if (!value) {
    try {
      fs.unlinkSync(credentialPath());
    } catch {
      // ignore
    }
    return;
  }
  fs.mkdirSync(app.getPath("userData"), { recursive: true });
  const payload = safeStorage.isEncryptionAvailable()
    ? safeStorage.encryptString(value)
    : Buffer.from(value, "utf8");
  fs.writeFileSync(credentialPath(), payload);
}

export function loadGroqKey(): string {
  try {
    const raw = fs.readFileSync(credentialPath());
    if (!raw.length) return "";
    if (safeStorage.isEncryptionAvailable()) {
      try {
        return safeStorage.decryptString(raw);
      } catch {
        return "";
      }
    }
    return raw.toString("utf8");
  } catch {
    return "";
  }
}

export function hasGroqKey(): boolean {
  return Boolean(loadGroqKey().trim());
}
