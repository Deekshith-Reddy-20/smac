from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models import TranslateRequest, TranslateResponse
from app.routes.errors import groq_error_response
from app.services.groq_service import GroqServiceError, groq_service

router = APIRouter()


@router.post("/translate", response_model=TranslateResponse, response_model_exclude_none=True)
def translate(payload: TranslateRequest) -> TranslateResponse | JSONResponse:
    try:
        translated = groq_service.translate(payload.text, payload.target_language)
    except GroqServiceError as exc:
        return groq_error_response(exc)
    return TranslateResponse(success=True, translated_text=translated)
