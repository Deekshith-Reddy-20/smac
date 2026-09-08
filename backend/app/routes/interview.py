import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models import InterviewAnswerRequest, InterviewAnswerResponse
from app.routes.errors import groq_error_response
from app.services import resume_store, session_store
from app.services.groq_service import GroqServiceError, groq_service

logger = logging.getLogger("savuor")
router = APIRouter()


@router.post("/interview/answer", response_model=InterviewAnswerResponse, response_model_exclude_none=True)
def interview_answer(payload: InterviewAnswerRequest) -> InterviewAnswerResponse | JSONResponse:
    if payload.reset_context:
        session_store.clear_session(payload.session_id)
        logger.info("[Interview] Context reset")

    history = session_store.get_history(payload.session_id, 2 if payload.ephemeral else 8)
    logger.info("[Interview] Generating answer")
    try:
        result = groq_service.interview_answer(
            transcript=payload.transcript,
            message=payload.message,
            history=history,
            force=payload.force or bool(payload.message),
            resume_text=resume_store.get_resume(payload.session_id),
        )
    except GroqServiceError as exc:
        return groq_error_response(exc)

    if result["status"] == "answer" and result["answer"].interview_answer:
        session_store.append_turn(
            payload.session_id,
            result["question"] or (payload.message or ""),
            result["answer"].interview_answer,
        )

    logger.info(
        "[Interview] Answer validated status=%s category=%s question=%r",
        result["status"],
        result["category"],
        (result["question"] or "")[:180],
    )

    return InterviewAnswerResponse(
        success=True,
        status=result["status"],
        is_question=result["is_question"],
        question_complete=result["question_complete"],
        question=result["question"],
        category=result["category"],
        answer=result["answer"],
        example=result["example"],
        confidence=result["confidence"],
    )
