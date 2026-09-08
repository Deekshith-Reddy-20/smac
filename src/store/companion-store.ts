import { create } from "zustand";
import type { CaptureStatus, CompanionMode, MeetingSession } from "../types/companion";

type CompanionUiState = {
  mode: CompanionMode;
  pinned: boolean;
  opacity: number;
  panel: "answer" | "transcript" | "actions" | "translate";
  session: MeetingSession;
  capture: CaptureStatus | null;
  setMode: (mode: CompanionMode) => void;
  setPinned: (pinned: boolean) => void;
  setOpacity: (opacity: number) => void;
  setPanel: (panel: CompanionUiState["panel"]) => void;
  setSession: (session: MeetingSession) => void;
  setCapture: (capture: CaptureStatus) => void;
};

export const useCompanionStore = create<CompanionUiState>((set) => ({
  mode: "full",
  pinned: true,
  opacity: 0.96,
  panel: "answer",
  session: { active: false, screenSharing: false, cueAiMode: "inactive" },
  capture: null,
  setMode: (mode) => set({ mode }),
  setPinned: (pinned) => set({ pinned }),
  setOpacity: (opacity) => set({ opacity }),
  setPanel: (panel) => set({ panel }),
  setSession: (session) => set({ session }),
  setCapture: (capture) => set({ capture }),
}));
