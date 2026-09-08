from fastapi.responses import JSONResponse

from app.services.groq_service import GroqServiceError


def groq_error_response(exc: GroqServiceError) -> JSONResponse:
    lowered = exc.message.lower()
    if (
        "failed_generation" in lowered
        or "structured_generation_failed" in lowered
        or "failed to generate json" in lowered
    ):
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "status": "unclear",
                "is_question": False,
                "question_complete": False,
                "question": "",
                "category": "",
                "answer": None,
                "confidence": 0,
            },
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.message},
    )
