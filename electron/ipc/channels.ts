export const IpcChannels = {
  COMPANION_SHOW: "companion:show",
  COMPANION_HIDE: "companion:hide",
  COMPANION_TOGGLE: "companion:toggle",
  COMPANION_SET_MODE: "companion:set-mode",
  COMPANION_MINIMIZE: "companion:minimize",
  COMPANION_PIN: "companion:pin",
  COMPANION_SET_OPACITY: "companion:set-opacity",
  COMPANION_OPEN_DASHBOARD: "companion:open-dashboard",
  COMPANION_ACTIVITY: "companion:activity",
  COMPANION_GET_CAPTURE_STATUS: "companion:get-capture-status",
  COMPANION_SET_EXCLUDE_CAPTURE: "companion:set-exclude-capture",
  MEETING_GET_SESSION: "meeting:get-session",
  APP_QUIT: "app:quit",
} as const;

export type CompanionMode = "full" | "mini" | "collapsed" | "presenter";

export type LitStoreSchema = {
  companionBounds: { x: number; y: number; width: number; height: number } | null;
  companionMode: CompanionMode;
  companionOpacity: number;
  companionPinned: boolean;
  excludeFromCapture: boolean;
  autoCollapse: boolean;
  autoCollapseMs: number;
  autoHide: boolean;
  autoHideMs: number;
};
