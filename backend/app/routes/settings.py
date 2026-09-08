from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.config import apply_groq_api_key, get_settings
from app.models import SettingsStatusResponse
from app.routes.errors import groq_error_response
from app.services.groq_service import GroqServiceError, groq_service

router = APIRouter()


class GroqKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=1)


@router.get("/settings/status", response_model=SettingsStatusResponse)
def settings_status() -> SettingsStatusResponse:
    return SettingsStatusResponse(success=True, has_api_key=bool(get_settings().groq_api_key.strip()))


@router.post("/settings/groq-key", response_model=SettingsStatusResponse)
def save_groq_key(payload: GroqKeyRequest) -> SettingsStatusResponse | JSONResponse:
    key = payload.api_key.strip()
    try:
        groq_service.validate_api_key(key)
    except GroqServiceError as exc:
        return groq_error_response(exc)
    apply_groq_api_key(key)
    groq_service.reset_client()
    return SettingsStatusResponse(success=True, has_api_key=True)
