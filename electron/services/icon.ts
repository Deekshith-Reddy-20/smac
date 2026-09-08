import { app } from "electron";
import path from "node:path";

export function appIconPath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "icon.png");
  }
  return path.join(app.getAppPath(), "build", "icon.png");
}
