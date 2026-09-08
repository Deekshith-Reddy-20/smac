import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routes import actions, chat, debug, health, interview, resume, transcribe, transcript, translate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

settings = get_settings()

app = FastAPI(
    title="Savuor API",
    description="Backend for the Savuor interview companion. Open /docs to try the endpoints.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(transcript.router, prefix="/api", tags=["transcript"])
app.include_router(transcribe.router, prefix="/api", tags=["transcribe"])
app.include_router(interview.router, prefix="/api", tags=["interview"])
app.include_router(resume.router, prefix="/api", tags=["resume"])
app.include_router(translate.router, prefix="/api", tags=["translate"])
app.include_router(actions.router, prefix="/api", tags=["actions"])
app.include_router(debug.router, prefix="/api", tags=["debug"])


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, _exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": "Invalid request data. Check the message and context fields.",
        },
    )
