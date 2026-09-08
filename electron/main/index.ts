import { app, BrowserWindow, Menu, Tray, nativeImage, globalShortcut } from "electron";
import { registerIpcHandlers } from "../ipc/handlers";
import { registerMediaPermissions } from "../services/media";
import {
  allowCompanionQuit,
  createCompanionWindow,
  showCompanion,
  toggleCompanion,
} from "../windows/companion-window";

let tray: Tray | null = null;

function createTray() {
  // Minimal PNG tray icon — replace with a branded asset later.
  const icon = nativeImage.createFromDataURL(
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
  );
  tray = new Tray(icon);
  tray.setToolTip("Savuor Companion");
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: "Show companion", click: () => showCompanion() },
      { label: "Toggle", click: () => toggleCompanion() },
      { type: "separator" },
      {
        label: "Quit Savuor",
        click: () => {
          allowCompanionQuit();
          app.quit();
        },
      },
    ])
  );
  tray.on("double-click", () => showCompanion());
}

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => showCompanion());

  app.whenReady().then(() => {
    registerMediaPermissions();
    registerIpcHandlers();
    createCompanionWindow();
    void showCompanion();
    createTray();

    globalShortcut.register("CommandOrControl+Shift+Space", () => toggleCompanion());

    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        createCompanionWindow();
        void showCompanion();
      } else {
        showCompanion();
      }
    });
  });

  app.on("before-quit", () => {
    allowCompanionQuit();
    for (const win of BrowserWindow.getAllWindows()) {
      win.removeAllListeners("close");
    }
  });

  app.on("will-quit", () => {
    globalShortcut.unregisterAll();
    tray?.destroy();
    tray = null;
  });

  app.on("window-all-closed", () => {
    // Keep running in tray on Windows so Esc/hide does not quit.
    if (process.platform === "darwin") app.quit();
  });
}
