import logging

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.models import TranscribeResponse
from app.routes.errors import groq_error_response
from app.services.groq_service import GroqServiceError, groq_service

logger = logging.getLogger("savuor")
router = APIRouter()


@router.post("/transcribe", response_model=TranscribeResponse, response_model_exclude_none=True)
async def transcribe(
    file: UploadFile = File(...),
    source: str = Form("unknown"),
) -> TranscribeResponse | JSONResponse:
    audio = await file.read()
    if not audio:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Empty audio upload."},
        )

    filename = file.filename or "audio.webm"
    try:
        text = groq_service.transcribe(audio, filename)
    except GroqServiceError as exc:
        return groq_error_response(exc)

    is_wav = audio[:4] == b"RIFF" and audio[8:12] == b"WAVE"
    logger.info("[Transcript] New text received source=%s bytes=%s wav=%s chars=%s text=%r",
        source,
        len(audio),
        is_wav,
        len(text),
        text[:180],
    )
    return TranscribeResponse(success=True, text=text, source=source)
