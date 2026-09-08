"""One-shot spoken runtime test for the continuous audio pipeline."""

from __future__ import annotations

import json
import subprocess
import time
import urllib.request

API = "http://127.0.0.1:8000"

QUESTIONS = [
    "What is HTML?",
    "What is Java?",
    "What is React?",
    "What is Node?",
    "What is AWS?",
]


def req(method: str, path: str, data: dict | None = None):
    body = None if data is None else json.dumps(data).encode()
    request = urllib.request.Request(
        API + path,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body else {},
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode())


def speak(text: str) -> None:
    payload = json.dumps(text)
    script = f"""
    Add-Type -AssemblyName System.Speech
    $wsh = New-Object -ComObject WScript.Shell
    1..8 | ForEach-Object {{ $wsh.SendKeys([char]175) }}
    $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $s.Rate = 0
    $s.Volume = 100
    $s.Speak({payload})
    """
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)


def counts(events: list[dict]) -> str:
    stages = [event.get("stage") for event in events]
    return (
        f"created={stages.count('WAV_CHUNK_CREATED')} "
        f"transcribe={stages.count('TRANSCRIPTION_TEXT_RECEIVED')} "
        f"questions={stages.count('QUESTION_DETECTED')} "
        f"groq={stages.count('GROQ_RESPONSE_RECEIVED')} "
        f"answers={stages.count('ANSWER_DISPLAYED')} "
        f"stops={stages.count('AUDIO_SESSION_STOP')}"
    )


INTERESTING = {
    "AUDIO_TRACK_LIVE",
    "WAV_CHUNK_CREATED",
    "WAV_CHUNK_SKIPPED_SILENCE",
    "TRANSCRIPTION_REQUEST_SENT",
    "TRANSCRIPTION_TEXT_RECEIVED",
    "TRANSCRIPTION_FAILED",
    "QUESTION_DETECTED",
    "QUESTION_SKIPPED",
    "GROQ_REQUEST_SENT",
    "GROQ_RESPONSE_RECEIVED",
    "ANSWER_DISPLAYED",
    "AUDIO_TRACK_STILL_LIVE",
    "AUDIO_SESSION_STOP",
    "AUDIO_CONTEXT_SUSPENDED",
    "DIAG_COMMAND_ERROR",
}


def wait_for_silence_boundary(timeout: float = 8.0) -> None:
    deadline = time.time() + timeout
    before = len(req("GET", "/api/debug/log").get("events", []))
    while time.time() < deadline:
        events = req("GET", "/api/debug/log").get("events", [])
        new = events[before:]
        if any(event.get("stage") == "WAV_CHUNK_SKIPPED_SILENCE" for event in new):
            return
        time.sleep(0.25)


def main() -> None:
    print("snapshot-before", req("POST", "/api/debug/command", {"action": "snapshot"}), flush=True)
    time.sleep(1)
    start_answers = sum(
        1 for event in req("GET", "/api/debug/log").get("events", []) if event.get("stage") == "ANSWER_DISPLAYED"
    )
    for index, question in enumerate(QUESTIONS, 1):
        print(f"Q{index} align-to-chunk", flush=True)
        wait_for_silence_boundary()
        print(f"Q{index} SPEAK {question}", flush=True)
        speak(question)
        print(f"Q{index} SPOKEN, waiting", flush=True)
        time.sleep(10)
        events = req("GET", "/api/debug/log").get("events", [])
        answers = sum(1 for event in events if event.get("stage") == "ANSWER_DISPLAYED")
        print(f"Q{index} {counts(events)} new_answers={answers - start_answers}", flush=True)

    print("final wait", flush=True)
    time.sleep(12)
    events = req("GET", "/api/debug/log").get("events", [])
    print("FINAL_COUNT", len(events), counts(events), flush=True)
    for event in events:
        if event.get("stage") not in INTERESTING:
            continue
        detail = event.get("detail") or {}
        text = (
            detail.get("text")
            or detail.get("question")
            or detail.get("transcript")
            or detail.get("error")
            or ""
        )
        live = detail.get("live")
        system = detail.get("system")
        if isinstance(system, dict):
            live = system.get("live", live)
        print(
            f"{event.get('server_ts', '')[11:23]} {event.get('stage')} "
            f"text={str(text)[:120]!r} bytes={detail.get('bytes') or ''} "
            f"rms={detail.get('rms') or ''} live={live} "
            f"ctx={detail.get('contextState')} chunks={detail.get('chunksEmitted')} "
            f"proc={detail.get('processCount')}",
            flush=True,
        )


if __name__ == "__main__":
    main()
