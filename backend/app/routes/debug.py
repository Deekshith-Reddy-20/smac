"""Temporary runtime diagnostics for the continuous audio pipeline."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()

ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = Path(os.environ.get("TEMP", str(Path.home()))) / "savuor-diag-audio.jsonl"
COMMAND_PATH = Path(os.environ.get("TEMP", str(Path.home()))) / "savuor-diag-command.json"


class TracePayload(BaseModel):
    model_config = {"extra": "allow"}

    stage: str
    source: str | None = None
    ok: bool | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


@router.post("/debug/trace")
def trace(payload: TracePayload) -> dict[str, Any]:
    record = payload.model_dump()
    record["server_ts"] = datetime.now(timezone.utc).isoformat()
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, default=str) + "\n")
    return {"success": True}


@router.get("/debug/command")
def get_command() -> dict[str, Any]:
    if not COMMAND_PATH.exists():
        return {"success": True, "command": None}
    try:
        data = json.loads(COMMAND_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = None
    COMMAND_PATH.unlink(missing_ok=True)
    return {"success": True, "command": data}


@router.post("/debug/command")
def set_command(payload: dict[str, Any]) -> dict[str, Any]:
    COMMAND_PATH.write_text(json.dumps(payload), encoding="utf-8")
    return {"success": True, "command": payload}


@router.post("/debug/reset")
def reset() -> dict[str, Any]:
    LOG_PATH.write_text("", encoding="utf-8")
    COMMAND_PATH.unlink(missing_ok=True)
    return {"success": True}


@router.get("/debug/log")
def read_log() -> dict[str, Any]:
    if not LOG_PATH.exists():
        return {"success": True, "events": []}
    events = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            events.append({"stage": "PARSE_ERROR", "raw": line})
    return {"success": True, "events": events}
