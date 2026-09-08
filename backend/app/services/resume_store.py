"""In-memory resume text for the active companion session. Not written to disk."""

from threading import Lock

_lock = Lock()
_resumes: dict[str, str] = {}


def set_resume(session_id: str, text: str) -> None:
    key = session_id or "default"
    with _lock:
        _resumes[key] = text


def get_resume(session_id: str) -> str | None:
    key = session_id or "default"
    with _lock:
        return _resumes.get(key)


def clear_resume(session_id: str) -> None:
    key = session_id or "default"
    with _lock:
        _resumes.pop(key, None)
