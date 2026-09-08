"""Environment configuration. The Groq API key never leaves the backend."""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Settings(BaseModel):
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="openai/gpt-oss-120b", alias="GROQ_MODEL")
    groq_transcribe_model: str = Field(
        default="whisper-large-v3-turbo", alias="GROQ_TRANSCRIBE_MODEL"
    )
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")
    question_stability_ms: int = Field(default=1100, alias="QUESTION_STABILITY_MS")
    question_incomplete_ms: int = Field(default=3800, alias="QUESTION_INCOMPLETE_MS")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @property
    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if not raw or raw == "*":
            return ["*"]
        return [item.strip() for item in raw.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    import os

    return Settings(
        GROQ_API_KEY=os.getenv("GROQ_API_KEY", ""),
        GROQ_MODEL=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        GROQ_TRANSCRIBE_MODEL=os.getenv("GROQ_TRANSCRIBE_MODEL", "whisper-large-v3-turbo"),
        CORS_ORIGINS=os.getenv("CORS_ORIGINS", "*"),
        QUESTION_STABILITY_MS=int(os.getenv("QUESTION_STABILITY_MS", "1100")),
        QUESTION_INCOMPLETE_MS=int(os.getenv("QUESTION_INCOMPLETE_MS", "3800")),
    )
