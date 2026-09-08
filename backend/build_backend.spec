# PyInstaller spec for the Savuor FastAPI backend.
# Build with: pyinstaller --noconfirm build_backend.spec

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = [
    "app",
    "app.main",
    "app.config",
    "app.models",
    "app.paths",
    "app.routes",
    "app.routes.actions",
    "app.routes.chat",
    "app.routes.errors",
    "app.routes.health",
    "app.routes.interview",
    "app.routes.resume",
    "app.routes.settings",
    "app.routes.transcribe",
    "app.routes.transcript",
    "app.routes.translate",
    "app.services",
    "app.services.groq_service",
    "app.services.resume_parser",
    "app.services.resume_store",
    "app.services.session_store",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "multipart",
    "pydantic",
    "anyio",
    "starlette",
    "groq",
    "httpx",
    "docx",
    "fitz",
    "pymupdf",
]

for package in ("fitz", "pymupdf", "groq", "uvicorn", "fastapi", "starlette", "pydantic", "docx"):
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception:
        hiddenimports += collect_submodules(package)

a = Analysis(
    ["run.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy.tests", "pytest", "watchfiles"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="savuor-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="savuor-backend",
)
