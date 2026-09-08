"""Production entry for the bundled Savuor FastAPI backend."""

from __future__ import annotations

import logging
import os
import socket
import sys
from pathlib import Path


def _prepare_environment() -> None:
    if getattr(sys, "frozen", False):
        bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        os.chdir(bundle_dir)
        if str(bundle_dir) not in sys.path:
            sys.path.insert(0, str(bundle_dir))
    else:
        backend_dir = Path(__file__).resolve().parent
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))


def _configure_logging() -> None:
    from app.paths import logs_dir

    log_file = logs_dir() / "backend.log"
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    try:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    except OSError:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=handlers,
        force=True,
    )


def _bind_host() -> str:
    host = (os.environ.get("SAVUOR_HOST") or "127.0.0.1").strip()
    if host not in {"127.0.0.1", "localhost"}:
        host = "127.0.0.1"
    return host


def _resolve_port(host: str) -> int:
    requested = int(os.environ.get("SAVUOR_PORT") or "0")
    if requested > 0:
        probe = socket.socket()
        try:
            probe.bind((host, requested))
            probe.close()
            return requested
        except OSError as exc:
            probe.close()
            raise SystemExit(f"SAVUOR_PORT_IN_USE {requested}") from exc
    probe = socket.socket()
    probe.bind((host, 0))
    port = int(probe.getsockname()[1])
    probe.close()
    return port


def main() -> None:
    _prepare_environment()
    _configure_logging()
    host = _bind_host()
    port = _resolve_port(host)
    os.environ["SAVUOR_PORT"] = str(port)

    import uvicorn
    from app.main import app

    print(f"SAVUOR_READY port={port}", flush=True)
    uvicorn.run(app, host=host, port=port, log_level="info", access_log=False)


if __name__ == "__main__":
    main()
