from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models import ActionsRequest, ActionsResponse
from app.routes.errors import groq_error_response
from app.services.groq_service import GroqServiceError, groq_service

router = APIRouter()


@router.post("/actions", response_model=ActionsResponse, response_model_exclude_none=True)
def actions(payload: ActionsRequest) -> ActionsResponse | JSONResponse:
    text = (payload.transcript or payload.message or "").strip()
    if not text:
        return ActionsResponse(success=True, actions=[])
    try:
        items = groq_service.extract_actions(text)
    except GroqServiceError as exc:
        return groq_error_response(exc)
    return ActionsResponse(success=True, actions=items)
