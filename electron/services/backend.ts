import { spawn, type ChildProcess } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import net from "node:net";
import path from "node:path";
import { app } from "electron";
import { loadGroqKey, saveGroqKey } from "./credentials";
import { appendDesktopLog, logsDir } from "./logging";

export type BackendRuntime = {
  apiBase: string;
  port: number;
  packaged: boolean;
  hasApiKey: boolean;
  backendError: string | null;
};

const DEFAULT_DEV_PORT = 8000;

let child: ChildProcess | null = null;
let runtime: BackendRuntime = {
  apiBase: `http://127.0.0.1:${DEFAULT_DEV_PORT}`,
  port: DEFAULT_DEV_PORT,
  packaged: false,
  hasApiKey: false,
  backendError: null,
};

export function getBackendRuntime(): BackendRuntime {
  return { ...runtime };
}

export function backendExePath() {
  const names = process.platform === "win32" ? ["savuor-backend.exe"] : ["savuor-backend"];
  const roots = [
    path.join(process.resourcesPath, "backend"),
    path.join(process.resourcesPath, "backend", "savuor-backend"),
  ];
  for (const root of roots) {
    for (const name of names) {
      const candidate = path.join(root, name);
      if (fs.existsSync(candidate)) return candidate;
    }
  }
  return path.join(process.resourcesPath, "backend", names[0]);
}

function backendPidPath() {
  return path.join(app.getPath("userData"), "backend.pid");
}

function writeBackendPid(pid: number) {
  try {
    fs.mkdirSync(app.getPath("userData"), { recursive: true });
    fs.writeFileSync(backendPidPath(), String(pid), "utf8");
  } catch {
    // ignore
  }
}

function clearBackendPid() {
  try {
    fs.unlinkSync(backendPidPath());
  } catch {
    // ignore
  }
}

function killStaleBackend() {
  try {
    const pid = Number(fs.readFileSync(backendPidPath(), "utf8"));
    if (pid > 0) {
      appendDesktopLog("Backend", "Stopping leftover backend process", { pid });
      killProcessTree(pid);
    }
  } catch {
    // ignore
  }
  clearBackendPid();
}

function findFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      const port = typeof address === "object" && address ? address.port : 0;
      server.close((error) => {
        if (error) reject(error);
        else resolve(port);
      });
    });
  });
}

export function waitForHealth(port: number, timeoutMs = 45000): Promise<void> {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const attempt = () => {
      const request = http.get(
        { host: "127.0.0.1", port, path: "/api/health", timeout: 1500 },
        (response) => {
          response.resume();
          if (response.statusCode && response.statusCode >= 200 && response.statusCode < 300) {
            resolve();
            return;
          }
          retry();
        }
      );
      request.on("error", retry);
      request.on("timeout", () => {
        request.destroy();
        retry();
      });
    };
    const retry = () => {
      if (Date.now() - started > timeoutMs) {
        reject(new Error("Savuor backend could not be started."));
        return;
      }
      setTimeout(attempt, 250);
    };
    attempt();
  });
}

function postJson(port: number, pathname: string, body: unknown): Promise<{ status: number; json: Record<string, unknown> }> {
  return new Promise((resolve, reject) => {
    const payload = Buffer.from(JSON.stringify(body));
    const request = http.request(
      {
        host: "127.0.0.1",
        port,
        path: pathname,
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": payload.length,
        },
        timeout: 25000,
      },
      (response) => {
        const chunks: Buffer[] = [];
        response.on("data", (chunk) => chunks.push(chunk as Buffer));
        response.on("end", () => {
          let json: Record<string, unknown> = {};
          try {
            json = JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}") as Record<string, unknown>;
          } catch {
            json = {};
          }
          resolve({ status: response.statusCode || 0, json });
        });
      }
    );
    request.on("error", reject);
    request.on("timeout", () => {
      request.destroy();
      reject(new Error("AI service unavailable. Check your Internet connection."));
    });
    request.write(payload);
    request.end();
  });
}

function killProcessTree(pid: number) {
  if (process.platform === "win32") {
    spawn("taskkill", ["/pid", String(pid), "/T", "/F"], {
      windowsHide: true,
      stdio: "ignore",
    });
    return;
  }
  try {
    process.kill(pid, "SIGTERM");
  } catch {
    // ignore
  }
}

export async function startBackend(): Promise<BackendRuntime> {
  runtime.packaged = app.isPackaged;
  runtime.hasApiKey = Boolean(loadGroqKey());
  runtime.backendError = null;

  if (!app.isPackaged) {
    runtime.port = DEFAULT_DEV_PORT;
    runtime.apiBase = `http://127.0.0.1:${DEFAULT_DEV_PORT}`;
    appendDesktopLog("Backend", "Development mode; expecting local uvicorn on 8000");
    try {
      await waitForHealth(DEFAULT_DEV_PORT, 2500);
    } catch {
      runtime.backendError = null;
      appendDesktopLog("Backend", "Development backend not running yet");
    }
    return getBackendRuntime();
  }

  if (child) stopBackend();
  killStaleBackend();

  const exe = backendExePath();
  if (!fs.existsSync(exe)) {
    runtime.backendError = "Savuor backend could not be started.";
    appendDesktopLog("Backend", "Bundled backend executable is missing", { exe });
    return getBackendRuntime();
  }

  const port = await findFreePort();
  runtime.port = port;
  runtime.apiBase = `http://127.0.0.1:${port}`;
  appendDesktopLog("Backend", "Starting bundled backend", { port });

  child = spawn(exe, [], {
    cwd: path.dirname(exe),
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
    env: {
      ...process.env,
      SAVUOR_HOST: "127.0.0.1",
      SAVUOR_PORT: String(port),
      SAVUOR_DATA_DIR: app.getPath("userData"),
      SAVUOR_ENV: "production",
      SAVUOR_PARENT_PID: String(process.pid),
      GROQ_API_KEY: loadGroqKey(),
      PYTHONUNBUFFERED: "1",
    },
  });

  const pid = child.pid;
  if (pid) writeBackendPid(pid);
  child.stdout?.on("data", (chunk: Buffer) => {
    const text = chunk.toString("utf8").trim();
    if (text) appendDesktopLog("Backend", text.slice(0, 400));
  });
  child.stderr?.on("data", (chunk: Buffer) => {
    const text = chunk.toString("utf8").trim();
    if (text) appendDesktopLog("Backend", text.slice(0, 400));
  });
  child.on("exit", (code, signal) => {
    appendDesktopLog("Backend", "Process exited", { code, signal, pid });
    if (child && child.pid === pid) child = null;
    clearBackendPid();
  });

  try {
    await waitForHealth(port);
    appendDesktopLog("Backend", "Health check passed", { port });
  } catch (error) {
    runtime.backendError = "Savuor backend could not be started.";
    appendDesktopLog("Backend", "Health check failed", {
      error: error instanceof Error ? error.message : "unknown",
    });
    stopBackend();
  }
  return getBackendRuntime();
}

export async function applyGroqKey(apiKey: string): Promise<{ success: boolean; error?: string }> {
  const key = apiKey.trim();
  if (!key) {
    return { success: false, error: "Groq API key is invalid. Please check the key and try again." };
  }
  if (!runtime.port || runtime.backendError) {
    return { success: false, error: "Savuor backend could not be started." };
  }
  try {
    const result = await postJson(runtime.port, "/api/settings/groq-key", { api_key: key });
    const success = result.status >= 200 && result.status < 300 && result.json.success === true;
    if (!success) {
      const error =
        typeof result.json.error === "string" && result.json.error.trim()
          ? result.json.error
          : "Groq API key is invalid. Please check the key and try again.";
      return { success: false, error };
    }
    saveGroqKey(key);
    runtime.hasApiKey = true;
    return { success: true };
  } catch {
    return { success: false, error: "AI service unavailable. Check your Internet connection." };
  }
}

export function stopBackend() {
  if (!child) return;
  const pid = child.pid;
  appendDesktopLog("Backend", "Stopping backend", { pid });
  try {
    child.kill();
  } catch {
    // ignore
  }
  if (pid) killProcessTree(pid);
  child = null;
  clearBackendPid();
}

export { logsDir };
