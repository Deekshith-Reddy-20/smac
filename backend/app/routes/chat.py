from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models import ChatRequest, ChatResponse
from app.routes.errors import groq_error_response
from app.services.groq_service import GroqServiceError, groq_service

router = APIRouter()


@router.post("/chat", response_model=ChatResponse, response_model_exclude_none=True)
def chat(payload: ChatRequest) -> ChatResponse | JSONResponse:
    context = None
    if payload.context is not None:
        context = payload.context.model_dump()
    try:
        answer = groq_service.chat(payload.message, context)
        return ChatResponse(success=True, answer=answer)
    except GroqServiceError as exc:
        return groq_error_response(exc)
