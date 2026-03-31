import pydantic as pd


class HealthResponse(pd.BaseModel):
    status: str = "ok"


class StartSessionRequest(pd.BaseModel):
    student_id: str = pd.Field(min_length=1, max_length=64)
    lecture_id: str = pd.Field(min_length=1, max_length=128)


class StartSessionResponse(pd.BaseModel):
    session_id: str
    message: str


class SendMessageRequest(pd.BaseModel):
    session_id: str
    message: str = pd.Field(min_length=1)


class SendMessageResponse(pd.BaseModel):
    message: str
    session_active: bool = True