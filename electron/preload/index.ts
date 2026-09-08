import { contextBridge, ipcRenderer } from "electron";
import { IpcChannels, type CompanionMode } from "../ipc/channels";

type MeetingSession = {
  active: boolean;
  screenSharing: boolean;
  meetingId?: string;
  title?: string;
  cueAiMode?: "inactive" | "private" | "live";
};

type CaptureStatus = {
  requested: boolean;
  applied: boolean;
  supported: boolean;
  message: string;
};

/** Companion-only preload — no cueDesktop / main-window APIs. */
const cueai = {
  minimize: () => ipcRenderer.invoke(IpcChannels.COMPANION_MINIMIZE),
  hide: () => ipcRenderer.invoke(IpcChannels.COMPANION_HIDE),
  setMode: (mode: CompanionMode) => ipcRenderer.invoke(IpcChannels.COMPANION_SET_MODE, mode),
  pin: (pinned: boolean) => ipcRenderer.invoke(IpcChannels.COMPANION_PIN, pinned),
  setOpacity: (opacity: number) => ipcRenderer.invoke(IpcChannels.COMPANION_SET_OPACITY, opacity),
  openDashboard: () => ipcRenderer.invoke(IpcChannels.COMPANION_OPEN_DASHBOARD),
  toggle: () => ipcRenderer.invoke(IpcChannels.COMPANION_TOGGLE),
  activity: () => ipcRenderer.invoke(IpcChannels.COMPANION_ACTIVITY),
  getCaptureStatus: () =>
    ipcRenderer.invoke(IpcChannels.COMPANION_GET_CAPTURE_STATUS) as Promise<CaptureStatus>,
  setExcludeCapture: (enabled: boolean) =>
    ipcRenderer.invoke(IpcChannels.COMPANION_SET_EXCLUDE_CAPTURE, enabled) as Promise<CaptureStatus>,
  getSession: () =>
    ipcRenderer.invoke(IpcChannels.MEETING_GET_SESSION) as Promise<MeetingSession>,
  onMode: (cb: (mode: CompanionMode) => void) => {
    const listener = (_: Electron.IpcRendererEvent, mode: CompanionMode) => cb(mode);
    ipcRenderer.on("companion:mode", listener);
    return () => ipcRenderer.removeListener("companion:mode", listener);
  },
  onSession: (cb: (session: MeetingSession) => void) => {
    const listener = (_: Electron.IpcRendererEvent, s: MeetingSession) => cb(s);
    ipcRenderer.on("companion:session", listener);
    return () => ipcRenderer.removeListener("companion:session", listener);
  },
  onCaptureStatus: (cb: (status: CaptureStatus) => void) => {
    const listener = (_: Electron.IpcRendererEvent, s: CaptureStatus) => cb(s);
    ipcRenderer.on("companion:capture-status", listener);
    return () => ipcRenderer.removeListener("companion:capture-status", listener);
  },
};

contextBridge.exposeInMainWorld("cueai", cueai);
