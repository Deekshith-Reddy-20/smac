import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const localBuild = path.join(os.homedir(), "Library", "Caches", "Savuor-build");
const backendDist = path.join(localBuild, "backend-dist");
const installerOut = path.join(localBuild, "out");
const pythonCandidates = [
  path.join(root, "backend", ".venv", "bin", "python"),
  path.join(root, "backend", ".venv", "bin", "python3"),
];

function run(command, args, cwd, extraEnv = {}, useShell = false) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd,
      stdio: "inherit",
      shell: useShell,
      env: { ...process.env, ...extraEnv },
    });
    child.on("error", (error) => {
      reject(new Error(`${command} ${args.join(" ")} failed: ${error.message}`));
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
  const python = pythonCandidates.find((item) => fs.existsSync(item));
  if (!python) {
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
  const binary = path.join(bundled, "savuor-backend");
  if (!fs.existsSync(binary)) {
    throw new Error("PyInstaller did not produce savuor-backend");
  }
  fs.chmodSync(binary, 0o755);
  copyDir(bundled, path.join(root, "backend-dist", "savuor-backend"));
}

async function main() {
  if (process.platform !== "darwin") {
    throw new Error("macOS DMG/ZIP must be built on a Mac. This Windows machine cannot create a working macOS app.");
  }
  fs.mkdirSync(localBuild, { recursive: true });
  fs.mkdirSync(path.join(root, "release"), { recursive: true });
  fs.mkdirSync(path.join(root, "backend-dist"), { recursive: true });
  await buildBackend();
  console.log("Building Electron UI…");
  await run("npm", ["run", "build"], root, {}, true);
  console.log("Creating Savuor macOS DMG and ZIP…");
  const builderCli = path.join(root, "node_modules", "electron-builder", "cli.js");
  await run(process.execPath, [builderCli, "--mac", "dmg", "--mac", "zip", `-c.directories.output=${installerOut}`], root, {
    CSC_IDENTITY_AUTO_DISCOVERY: "false",
  });
  const artifacts = fs
    .readdirSync(installerOut)
    .filter((name) => name.endsWith(".dmg") || (name.endsWith(".zip") && name.startsWith("Savuor")));
  if (!artifacts.length) {
    throw new Error("No Savuor .dmg or .zip was created.");
  }
  for (const name of artifacts) {
    fs.copyFileSync(path.join(installerOut, name), path.join(root, "release", name));
    console.log(`Installer ready: ${path.join(root, "release", name)}`);
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
