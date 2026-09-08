import { app, BrowserWindow, screen } from "electron";
import path from "node:path";
import type { CompanionMode } from "../ipc/channels";
import { getStoreValue, setStoreValue } from "../services/store";
import {
  applyCaptureExclusion,
  clampBoundsToVisibleDisplay,
  dockPresenterToEdge,
} from "../services/capture";

const MODE_SIZE: Record<CompanionMode, { width: number; height: number }> = {
  full: { width: 420, height: 560 },
  mini: { width: 320, height: 280 },
  collapsed: { width: 260, height: 72 },
  presenter: { width: 360, height: 220 },
};

let companionWin: BrowserWindow | null = null;
let allowQuit = false;
let animating = false;
let idleTimer: NodeJS.Timeout | null = null;
let hideTimer: NodeJS.Timeout | null = null;

export function allowCompanionQuit() {
  allowQuit = true;
}

export function getCompanionWindow() {
  return companionWin;
}

export function createCompanionWindow(): BrowserWindow {
  if (companionWin && !companionWin.isDestroyed()) {
    return companionWin;
  }

  const isDev = !app.isPackaged;
  const saved = getStoreValue("companionBounds");
  const mode = getStoreValue("companionMode");
  const size = MODE_SIZE[mode];
  const display = screen.getPrimaryDisplay().workArea;

  const initial = clampBoundsToVisibleDisplay({
    width: saved?.width ?? size.width,
    height: saved?.height ?? size.height,
    x: saved?.x ?? display.x + display.width - (size.width + 24),
    y: saved?.y ?? display.y + Math.round(display.height * 0.12),
  });

  companionWin = new BrowserWindow({
    width: initial.width,
    height: initial.height,
    x: initial.x,
    y: initial.y,
    minWidth: 220,
    minHeight: 64,
    show: false,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    alwaysOnTop: true,
    resizable: true,
    skipTaskbar: false,
    hasShadow: true,
    roundedCorners: true,
    focusable: true,
    title: "Savuor",
    webPreferences: {
      preload: path.join(__dirname, "../preload/index.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      backgroundThrottling: false,
      spellcheck: false,
    },
  });

  companionWin.setAlwaysOnTop(getStoreValue("companionPinned"), "screen-saver");
  companionWin.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  companionWin.setOpacity(getStoreValue("companionOpacity"));
  applyCaptureExclusion(companionWin);

  if (isDev) {
    void companionWin.loadURL("http://localhost:5174");
  } else {
    void companionWin.loadFile(path.join(__dirname, "../../dist/index.html"));
  }

  companionWin.on("close", (e) => {
    if (allowQuit || !companionWin) return;
    e.preventDefault();
    void hideCompanionAnimated();
  });

  companionWin.webContents.on("before-input-event", (event, input) => {
    if (input.type === "keyDown" && input.key === "Escape") {
      event.preventDefault();
      void hideCompanionAnimated();
    }
  });

  companionWin.on("moved", persistBounds);
  companionWin.on("resized", persistBounds);
  companionWin.on("show", () => {
    companionWin?.webContents.setBackgroundThrottling(false);
    applyCaptureExclusion(companionWin);
    resetIdleTimers();
  });
  companionWin.on("hide", () => {
    companionWin?.webContents.setBackgroundThrottling(false);
    clearIdleTimers();
  });
  companionWin.on("blur", () => scheduleAutoHideOrCollapse());
  companionWin.on("focus", () => resetIdleTimers());

  screen.on("display-metrics-changed", () => {
    if (companionWin && !companionWin.isDestroyed()) {
      applyCaptureExclusion(companionWin);
    }
  });

  return companionWin;
}

function persistBounds() {
  if (!companionWin || companionWin.isDestroyed() || animating) return;
  setStoreValue("companionBounds", companionWin.getBounds());
}

function clearIdleTimers() {
  if (idleTimer) clearTimeout(idleTimer);
  if (hideTimer) clearTimeout(hideTimer);
  idleTimer = null;
  hideTimer = null;
}

function resetIdleTimers() {
  clearIdleTimers();
}

function scheduleAutoHideOrCollapse() {
  clearIdleTimers();
  const mode = getStoreValue("companionMode");
  if (getStoreValue("autoCollapse") && mode === "full") {
    idleTimer = setTimeout(() => {
      if (!companionWin?.isFocused()) setCompanionMode("collapsed");
    }, getStoreValue("autoCollapseMs"));
  }
  if (getStoreValue("autoHide")) {
    hideTimer = setTimeout(() => {
      if (!companionWin?.isFocused()) void hideCompanionAnimated();
    }, getStoreValue("autoHideMs"));
  }
}

export function companionUserActivity() {
  resetIdleTimers();
}

async function fadeOpacity(win: BrowserWindow, from: number, to: number, ms = 140) {
  animating = true;
  const steps = 8;
  const dt = ms / steps;
  for (let i = 1; i <= steps; i++) {
    if (win.isDestroyed()) break;
    win.setOpacity(from + (to - from) * (i / steps));
    await new Promise((r) => setTimeout(r, dt));
  }
  animating = false;
}

export async function showCompanionAnimated() {
  const win = createCompanionWindow();
  applyCaptureExclusion(win);
  const target = getStoreValue("companionOpacity");
  if (!win.isVisible()) {
    win.setOpacity(0);
    win.showInactive();
    await fadeOpacity(win, 0, target, 120);
    win.focus();
  } else {
    win.setOpacity(target);
    win.focus();
  }
  win.webContents.send("companion:visibility", true);
}

export async function hideCompanionAnimated() {
  if (!companionWin || companionWin.isDestroyed() || !companionWin.isVisible()) return;
  const from = companionWin.getOpacity();
  await fadeOpacity(companionWin, from, 0, 100);
  if (!companionWin.isDestroyed()) {
    companionWin.hide();
    companionWin.setOpacity(getStoreValue("companionOpacity"));
    companionWin.webContents.send("companion:visibility", false);
  }
}

export function showCompanion() {
  void showCompanionAnimated();
}

export function hideCompanion() {
  void hideCompanionAnimated();
}

export function toggleCompanion() {
  const win = createCompanionWindow();
  if (win.isVisible()) void hideCompanionAnimated();
  else void showCompanionAnimated();
}

export function setCompanionMode(mode: CompanionMode) {
  setStoreValue("companionMode", mode);
  const win = companionWin;
  if (!win || win.isDestroyed()) return;

  if (mode === "presenter") {
    dockPresenterToEdge(win);
  } else {
    const size = MODE_SIZE[mode];
    const [x, y] = win.getPosition();
    const display = screen.getDisplayMatching(win.getBounds()).workArea;
    const next = clampBoundsToVisibleDisplay({ x, y, ...size });
    win.setBounds(
      {
        x: Math.min(Math.max(display.x, next.x), display.x + display.width - size.width),
        y: Math.min(Math.max(display.y, next.y), display.y + display.height - size.height),
        ...size,
      },
      true
    );
  }

  win.webContents.send("companion:mode", mode);
}

export function setCompanionPinned(pinned: boolean) {
  setStoreValue("companionPinned", pinned);
  companionWin?.setAlwaysOnTop(pinned, "screen-saver");
}

export function setCompanionOpacity(opacity: number) {
  const value = Math.min(1, Math.max(0.4, opacity));
  setStoreValue("companionOpacity", value);
  if (companionWin && !companionWin.isDestroyed() && companionWin.isVisible()) {
    companionWin.setOpacity(value);
  }
}
