"""Runtime checks for the interview engine."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

API = "http://127.0.0.1:8000"


def post(path: str, payload: dict, timeout: int = 60) -> dict:
    request = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"success": False, "error": body, "status_code": exc.code}


def visible_text(data: dict) -> str:
    answer = data.get("answer")
    if isinstance(answer, dict):
        return str(answer.get("interview_answer") or answer.get("answer") or "")
    return str(answer or data.get("error") or "")


def forbidden(data: dict) -> bool:
    blob = json.dumps(data).lower()
    return "failed_generation" in blob or "failed to generate json" in blob


def main() -> None:
    results = {}
    session = "engine-v2-test"

    short = post(
        "/api/interview/answer",
        {
            "transcript": "What is Python?",
            "session_id": session,
            "ephemeral": False,
            "force": True,
        },
    )
    short_text = visible_text(short)
    results["short"] = short.get("success") and short.get("is_question") and "python" in short_text.lower() and not forbidden(short)
    print("SHORT", results["short"], short.get("status"), short.get("question"), short_text[:80])

    filler = post(
        "/api/interview/answer",
        {
            "transcript": "Okay, let's continue.",
            "session_id": session,
            "ephemeral": False,
            "force": False,
        },
    )
    filler_ok = filler.get("success") and filler.get("status") in {"skip", "unclear"} and not visible_text(filler)
    if filler.get("is_question") and visible_text(filler):
        filler_ok = False
    results["filler"] = filler_ok and not forbidden(filler)
    print("FILLER", results["filler"], filler.get("status"), visible_text(filler)[:60])

    follow = post(
        "/api/interview/answer",
        {
            "transcript": "Why did you use it?",
            "session_id": session,
            "ephemeral": False,
            "force": True,
        },
    )
    follow_text = visible_text(follow).lower()
    results["followup"] = follow.get("success") and "python" in follow_text and not forbidden(follow)
    print("FOLLOWUP", results["followup"], follow.get("question"), visible_text(follow)[:100])

    long_q = (
        "Can you explain the project you worked on during your internship, what problem it solved, "
        "what technologies you used, and what your contribution was?"
    )
    long_answer = post(
        "/api/interview/answer",
        {
            "transcript": long_q,
            "session_id": session + "-long",
            "ephemeral": False,
            "force": True,
        },
    )
    long_text = visible_text(long_answer)
    results["long"] = (
        long_answer.get("success")
        and long_answer.get("is_question")
        and len(long_text) > 80
        and not long_text.strip().startswith("{")
        and not forbidden(long_answer)
    )
    print("LONG", results["long"], long_answer.get("question", "")[:80], long_text[:100])

    unclear = post(
        "/api/interview/answer",
        {
            "transcript": "Can you explain",
            "session_id": session + "-unclear",
            "ephemeral": False,
            "force": False,
        },
    )
    results["unclear"] = unclear.get("success") and unclear.get("status") in {"skip", "unclear"} and not forbidden(unclear)
    print("UNCLEAR", results["unclear"], unclear.get("status"), visible_text(unclear)[:60])

    resume_req = urllib.request.Request(
        API + "/api/resume/upload",
        method="POST",
    )
    boundary = "----SavuorBoundary"
    resume_body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="session_id"\r\n\r\n'
        f"{session}-resume\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="resume.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n"
        "Littu Patel. Project: Stock Pair Finder. Used Python, Pandas, NumPy, yfinance, Matplotlib "
        "to find correlated stock pairs and visualize spread mean reversion. Contribution: designed "
        "the pairing metric and backtest.\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    resume_req = urllib.request.Request(
        API + "/api/resume/upload",
        data=resume_body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(resume_req, timeout=30) as response:
        uploaded = json.loads(response.read().decode())
    print("RESUME_UPLOAD", uploaded.get("success"))
    resume_answer = post(
        "/api/interview/answer",
        {
            "transcript": "Explain the project in your resume.",
            "session_id": f"{session}-resume",
            "ephemeral": False,
            "force": True,
        },
    )
    resume_text = visible_text(resume_answer).lower()
    results["resume"] = uploaded.get("success") and "stock pair" in resume_text and "pandas" in resume_text and not forbidden(resume_answer)
    print("RESUME", results["resume"], visible_text(resume_answer)[:160])

    json_ok = all(not forbidden(item) for item in (short, filler, follow, long_answer, unclear, resume_answer))
    results["json"] = json_ok
    print("JSON_CLEAN", json_ok)
    print("RESULTS", results)


if __name__ == "__main__":
    main()
