import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const localBuild = path.join(os.homedir(), "AppData", "Local", "Savuor-build");
const backendDist = path.join(localBuild, "backend-dist");
const installerOut = path.join(localBuild, "out");
const python = path.join(root, "backend", ".venv", "Scripts", "python.exe");
const backendOnly = process.argv.includes("--backend-only");

function run(command, args, cwd, extraEnv = {}, useShell = false) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd,
      stdio: "inherit",
      shell: useShell,
      env: { ...process.env, ...extraEnv },
    });
    child.on("exit", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${command} ${args.join(" ")} failed with code ${code}`));
    });
  });
}

function copyDir(from, to) {
  fs.rmSync(to, { recursive: true, force: true });
  fs.mkdirSync(path.dirname(to), { recursive: true });
  fs.cpSync(from, to, { recursive: true });
}

async function buildBackend() {
  if (!fs.existsSync(python)) {
    throw new Error("Missing backend/.venv. Create it and install requirements before packaging.");
  }
  console.log("Installing backend build dependencies…");
  await run(python, ["-m", "pip", "install", "-r", "requirements.txt", "-r", "requirements-build.txt"], path.join(root, "backend"));
  console.log("Building bundled FastAPI backend…");
  await run(
    python,
    [
      "-m",
      "PyInstaller",
      "--noconfirm",
      "--clean",
      "--distpath",
      backendDist,
      "--workpath",
      path.join(localBuild, "backend-work"),
      "build_backend.spec",
    ],
    path.join(root, "backend")
  );
  const bundled = path.join(backendDist, "savuor-backend");
  if (!fs.existsSync(path.join(bundled, "savuor-backend.exe"))) {
    throw new Error("PyInstaller did not produce savuor-backend.exe");
  }
  copyDir(bundled, path.join(root, "backend-dist", "savuor-backend"));
}

async function main() {
  fs.mkdirSync(localBuild, { recursive: true });
  fs.mkdirSync(path.join(root, "release"), { recursive: true });
  fs.mkdirSync(path.join(root, "backend-dist"), { recursive: true });
  await buildBackend();
  if (backendOnly) {
    console.log("Backend bundle ready: backend-dist/savuor-backend/savuor-backend.exe");
    return;
  }
  console.log("Building Electron UI…");
  await run(process.platform === "win32" ? "npm.cmd" : "npm", ["run", "build"], root, {}, true);
  console.log("Creating SavuorSetup.exe…");
  const builderCli = path.join(root, "node_modules", "electron-builder", "cli.js");
  await run(
    process.execPath,
    [builderCli, "--win", "nsis", `-c.directories.output=${installerOut.replace(/\\/g, "/")}`],
    root,
    { CSC_IDENTITY_AUTO_DISCOVERY: "false" }
  );
  const setup = path.join(installerOut, "SavuorSetup.exe");
  if (!fs.existsSync(setup)) {
    throw new Error("SavuorSetup.exe was not created.");
  }
  const releaseSetup = path.join(root, "release", "SavuorSetup.exe");
  fs.copyFileSync(setup, releaseSetup);
  fs.copyFileSync(path.join(root, "build", "README.txt"), path.join(root, "release", "README.txt"));
  console.log(`Installer ready: ${releaseSetup}`);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
