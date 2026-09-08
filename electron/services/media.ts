import { desktopCapturer, session } from "electron";

const MEDIA_PERMISSIONS = new Set([
  "media",
  "display-capture",
  "audioCapture",
  "videoCapture",
  "mediaKeySystem",
]);

export function registerMediaPermissions() {
  const ses = session.defaultSession;

  ses.setPermissionRequestHandler((_webContents, permission, callback) => {
    callback(MEDIA_PERMISSIONS.has(permission));
  });

  ses.setPermissionCheckHandler((_webContents, permission) => {
    return MEDIA_PERMISSIONS.has(permission) || permission === "clipboard-sanitized-write";
  });

  ses.setDisplayMediaRequestHandler(async (_request, callback) => {
    try {
      const sources = await desktopCapturer.getSources({
        types: ["screen"],
        thumbnailSize: { width: 1, height: 1 },
      });
      const source = sources[0];
      if (!source) {
        callback({});
        return;
      }
      callback({
        video: source,
        audio: "loopback",
      });
    } catch {
      callback({});
    }
  });
}
