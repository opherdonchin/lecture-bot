from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class StartSessionRequest(BaseModel):
    student_id: str = Field(min_length=1, max_length=64)
    lecture_id: str = Field(min_length=1, max_length=128)


class StartSessionResponse(BaseModel):
    session_id: str
    message: str


class SendMessageRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1)


class SendMessageResponse(BaseModel):
    message: str
    session_active: bool = True