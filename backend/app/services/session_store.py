"""In-memory interview context. Nothing is written to disk."""

from collections import defaultdict, deque
from threading import Lock

_lock = Lock()
_sessions: dict[str, deque[dict[str, str]]] = defaultdict(lambda: deque(maxlen=16))


def get_history(session_id: str, limit: int) -> list[dict[str, str]]:
    key = session_id or "default"
    with _lock:
        items = list(_sessions[key])
    return items[-limit:]


def append_turn(session_id: str, question: str, answer: str) -> None:
    key = session_id or "default"
    with _lock:
        _sessions[key].append({"question": question, "answer": answer})


def clear_session(session_id: str) -> None:
    key = session_id or "default"
    with _lock:
        _sessions.pop(key, None)
