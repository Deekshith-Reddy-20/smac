from pydantic import BaseModel, Field, field_validator, model_validator


class ChatContext(BaseModel):
    transcript: str | None = None
    system: str | None = None
    ephemeral: str | None = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    context: ChatContext | None = None

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message cannot be empty")
        return stripped


class ChatResponse(BaseModel):
    success: bool
    answer: str | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str


class TranscriptRequest(BaseModel):
    transcript: str = Field(..., min_length=1)

    @field_validator("transcript")
    @classmethod
    def transcript_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("transcript cannot be empty")
        return stripped


class TranscriptResponse(BaseModel):
    success: bool
    message: str
    error: str | None = None


class InterviewAnswerRequest(BaseModel):
    transcript: str | None = None
    message: str | None = None
    ephemeral: bool = True
    session_id: str = "default"
    force: bool = False
    reset_context: bool = False

    @model_validator(mode="after")
    def require_text(self) -> "InterviewAnswerRequest":
        transcript = (self.transcript or "").strip()
        message = (self.message or "").strip()
        if not transcript and not message:
            raise ValueError("transcript or message is required")
        self.transcript = transcript or None
        self.message = message or None
        return self


class InterviewAnswerBlock(BaseModel):
    direct: str = ""
    explanation: str = ""
    example: str = ""
    interview_answer: str = ""


class InterviewAnswerResponse(BaseModel):
    success: bool
    status: str = "skip"
    is_question: bool = False
    question_complete: bool = False
    question: str = ""
    category: str = ""
    answer: InterviewAnswerBlock | None = None
    example: str = ""
    confidence: float = 0
    error: str | None = None


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    target_language: str = Field(..., min_length=2)

    @field_validator("text", "target_language")
    @classmethod
    def not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value cannot be empty")
        return stripped


class TranslateResponse(BaseModel):
    success: bool
    translated_text: str | None = None
    error: str | None = None


class ActionItem(BaseModel):
    task: str
    priority: str = "medium"


class ActionsRequest(BaseModel):
    transcript: str | None = None
    message: str | None = None


class ActionsResponse(BaseModel):
    success: bool
    actions: list[ActionItem] = Field(default_factory=list)
    error: str | None = None


class TranscribeResponse(BaseModel):
    success: bool
    text: str = ""
    source: str | None = None
    error: str | None = None


class ResumeUploadResponse(BaseModel):
    success: bool
    filename: str | None = None
    characters: int | None = None
    message: str | None = None
    error: str | None = None
