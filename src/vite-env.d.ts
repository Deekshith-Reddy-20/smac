import type { CompanionAPI } from "./types/companion";

declare global {
  interface Window {
    cueai?: CompanionAPI;
  }
}

export {};
