import { BrowserWindow, screen } from "electron";
import { getStoreValue } from "./store";

export type CaptureStatus = {
  requested: boolean;
  applied: boolean;
  supported: boolean;
  message: string;
};

export type MeetingSession = {
  active: boolean;
  screenSharing: boolean;
  meetingId?: string;
  title?: string;
  cueAiMode?: "inactive" | "private" | "live";
};

let session: MeetingSession = {
  active: false,
  screenSharing: false,
  cueAiMode: "inactive",
};

let protectionStatus: CaptureStatus = {
  requested: true,
  applied: false,
  supported: false,
  message: "Not applied yet",
};

export function getMeetingSession(): MeetingSession {
  return { ...session };
}

export function getCaptureProtectionStatus(): CaptureStatus {
  return { ...protectionStatus };
}

export function applyCaptureExclusion(win: BrowserWindow | null): CaptureStatus {
  if (!win || win.isDestroyed()) {
    protectionStatus = {
      requested: true,
      applied: false,
      supported: false,
      message: "Companion window unavailable",
    };
    return getCaptureProtectionStatus();
  }

  if (!getStoreValue("excludeFromCapture")) {
    try {
      win.setContentProtection(false);
    } catch {
      // ignore
    }
    protectionStatus = {
      requested: false,
      applied: false,
      supported: true,
      message: "Capture exclusion disabled",
    };
    return getCaptureProtectionStatus();
  }

  try {
    const current = win.getOpacity();
    win.setOpacity(Math.min(1, Math.max(0.5, current || 0.96)));
    win.setContentProtection(true);
    protectionStatus = {
      requested: true,
      applied: true,
      supported: true,
      message: "Excluded from capture when OS supports it",
    };
  } catch {
    protectionStatus = {
      requested: true,
      applied: false,
      supported: false,
      message: "Capture exclusion not supported on this OS",
    };
  }
  return getCaptureProtectionStatus();
}

export function clampBoundsToVisibleDisplay(bounds: {
  x: number;
  y: number;
  width: number;
  height: number;
}) {
  const display = screen.getDisplayMatching(bounds).workArea;
  const width = Math.min(bounds.width, display.width);
  const height = Math.min(bounds.height, display.height);
  const x = Math.min(Math.max(display.x, bounds.x), display.x + display.width - width);
  const y = Math.min(Math.max(display.y, bounds.y), display.y + display.height - height);
  return { x, y, width, height };
}

export function dockPresenterToEdge(win: BrowserWindow) {
  const display = screen.getDisplayMatching(win.getBounds()).workArea;
  const width = 360;
  const height = 220;
  win.setBounds(
    {
      x: display.x + display.width - width - 16,
      y: display.y + 16,
      width,
      height,
    },
    true
  );
}
