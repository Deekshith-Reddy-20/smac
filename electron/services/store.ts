import { app } from "electron";
import fs from "node:fs";
import path from "node:path";
import type { LitStoreSchema } from "../ipc/channels";

const defaults: LitStoreSchema = {
  companionBounds: null,
  companionMode: "full",
  companionOpacity: 0.96,
  companionPinned: true,
  excludeFromCapture: true,
  autoCollapse: true,
  autoCollapseMs: 45000,
  autoHide: false,
  autoHideMs: 90000,
};

function storePath() {
  return path.join(app.getPath("userData"), "cueai-lit-store.json");
}

function readStore(): LitStoreSchema {
  try {
    const raw = fs.readFileSync(storePath(), "utf8");
    return { ...defaults, ...(JSON.parse(raw) as Partial<LitStoreSchema>) };
  } catch {
    return { ...defaults };
  }
}

function writeStore(data: LitStoreSchema) {
  fs.mkdirSync(path.dirname(storePath()), { recursive: true });
  fs.writeFileSync(storePath(), JSON.stringify(data, null, 2), "utf8");
}

let cache: LitStoreSchema | null = null;

function ensure(): LitStoreSchema {
  if (!cache) cache = readStore();
  return cache;
}

export function getStoreValue<K extends keyof LitStoreSchema>(key: K): LitStoreSchema[K] {
  return ensure()[key];
}

export function setStoreValue<K extends keyof LitStoreSchema>(
  key: K,
  value: LitStoreSchema[K]
): void {
  const next = { ...ensure(), [key]: value };
  cache = next;
  writeStore(next);
}
