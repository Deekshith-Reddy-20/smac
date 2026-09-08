import { app, ipcMain, shell } from "electron";
import { IpcChannels, type CompanionMode } from "./channels";
import {
  applyCaptureExclusion,
  getCaptureProtectionStatus,
  getMeetingSession,
} from "../services/capture";
import { getStoreValue, setStoreValue } from "../services/store";
import {
  companionUserActivity,
  getCompanionWindow,
  hideCompanion,
  setCompanionMode,
  setCompanionOpacity,
  setCompanionPinned,
  showCompanion,
  toggleCompanion,
} from "../windows/companion-window";

export function registerIpcHandlers() {
  ipcMain.handle(IpcChannels.COMPANION_SHOW, () => showCompanion());
  ipcMain.handle(IpcChannels.COMPANION_HIDE, () => hideCompanion());
  ipcMain.handle(IpcChannels.COMPANION_TOGGLE, () => toggleCompanion());
  ipcMain.handle(IpcChannels.COMPANION_MINIMIZE, () => getCompanionWindow()?.minimize());
  ipcMain.handle(IpcChannels.COMPANION_SET_MODE, (_e, mode: CompanionMode) => {
    setCompanionMode(mode);
  });
  ipcMain.handle(IpcChannels.COMPANION_PIN, (_e, pinned: boolean) => {
    setCompanionPinned(Boolean(pinned));
  });
  ipcMain.handle(IpcChannels.COMPANION_SET_OPACITY, (_e, opacity: number) => {
    setCompanionOpacity(Number(opacity));
  });
  ipcMain.handle(IpcChannels.COMPANION_OPEN_DASHBOARD, async () => {
    // Lit is companion-only — open web dashboard in the default browser if available.
    await shell.openExternal("http://localhost:3000/dashboard");
  });
  ipcMain.handle(IpcChannels.COMPANION_ACTIVITY, () => {
    companionUserActivity();
  });
  ipcMain.handle(IpcChannels.COMPANION_GET_CAPTURE_STATUS, () => getCaptureProtectionStatus());
  ipcMain.handle(IpcChannels.COMPANION_SET_EXCLUDE_CAPTURE, (_e, enabled: boolean) => {
    setStoreValue("excludeFromCapture", Boolean(enabled));
    const win = getCompanionWindow();
    if (!win) return getCaptureProtectionStatus();
    if (enabled) return applyCaptureExclusion(win);
    try {
      win.setContentProtection(false);
    } catch {
      // ignore
    }
    return getCaptureProtectionStatus();
  });
  ipcMain.handle(IpcChannels.MEETING_GET_SESSION, () => getMeetingSession());
  ipcMain.handle(IpcChannels.APP_QUIT, () => {
    app.quit();
  });
}
