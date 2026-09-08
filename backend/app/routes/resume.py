from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.models import ResumeUploadResponse
from app.services.resume_parser import ResumeParseError, extract_resume_text
from app.services.resume_store import set_resume

router = APIRouter()


@router.post("/resume/upload", response_model=ResumeUploadResponse, response_model_exclude_none=True)
async def upload_resume(
    file: UploadFile = File(...),
    session_id: str = Form("default"),
) -> ResumeUploadResponse | JSONResponse:
    data = await file.read()
    filename = file.filename or "resume"
    try:
        text = extract_resume_text(filename, data)
    except ResumeParseError as exc:
        return JSONResponse(status_code=400, content={"success": False, "error": str(exc)})

    set_resume(session_id, text)
    return ResumeUploadResponse(
        success=True,
        filename=filename,
        characters=len(text),
        message="Resume received for this session.",
    )
