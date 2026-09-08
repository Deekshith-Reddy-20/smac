# Savuor — companion-only Windows app

Standalone Electron app that runs **only** the floating companion overlay.

## Development

```bash
npm install
npm run dev
```

Backend (separate terminal):

```bash
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Shortcut: `Ctrl+Shift+Space` toggles the companion. Esc / X hides to tray. Quit from the tray menu.

## Production installer (Windows x64)

The packaged app includes the FastAPI backend. End users do not need Python, Node, or Cursor.

```bash
npm install
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-build.txt
cd ..
npm run package
```

Output:

`release/SavuorSetup.exe`

Do not package `backend/.env` or any Groq API key. Each user enters their own key on first launch.
