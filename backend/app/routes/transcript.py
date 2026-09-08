from fastapi import APIRouter

from app.models import TranscriptRequest, TranscriptResponse

router = APIRouter()

_latest_transcript: str | None = None


def get_latest_transcript() -> str | None:
    return _latest_transcript


@router.post("/transcript", response_model=TranscriptResponse, response_model_exclude_none=True)
def receive_transcript(payload: TranscriptRequest) -> TranscriptResponse:
    global _latest_transcript
    _latest_transcript = payload.transcript
    return TranscriptResponse(success=True, message="Transcript received")
