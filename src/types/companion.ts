export type CompanionMode = "full" | "mini" | "collapsed" | "presenter";

export type MeetingSession = {
  active: boolean;
  screenSharing: boolean;
  meetingId?: string;
  title?: string;
  cueAiMode?: "inactive" | "private" | "live";
};

export type CaptureStatus = {
  requested: boolean;
  applied: boolean;
  supported: boolean;
  message: string;
};

export type RuntimeConfig = {
  apiBase: string;
  packaged: boolean;
  hasApiKey: boolean;
  backendError: string | null;
};

export type CompanionAPI = {
  minimize: () => Promise<void>;
  hide: () => Promise<void>;
  setMode: (mode: CompanionMode) => Promise<void>;
  pin: (pinned: boolean) => Promise<void>;
  setOpacity: (opacity: number) => Promise<void>;
  openDashboard: () => Promise<void>;
  toggle: () => Promise<void>;
  activity: () => Promise<void>;
  getCaptureStatus: () => Promise<CaptureStatus>;
  setExcludeCapture: (enabled: boolean) => Promise<CaptureStatus>;
  getSession: () => Promise<MeetingSession>;
  getRuntime: () => Promise<RuntimeConfig>;
  hasGroqKey: () => Promise<boolean>;
  saveGroqKey: (key: string) => Promise<{ success: boolean; error?: string }>;
  openLogs: () => Promise<void>;
  onMode: (cb: (mode: CompanionMode) => void) => () => void;
  onSession: (cb: (session: MeetingSession) => void) => () => void;
  onCaptureStatus: (cb: (status: CaptureStatus) => void) => () => void;
};
