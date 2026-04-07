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


class SessionIdRequest(pd.BaseModel):
    session_id: str


class RestartSessionRequest(pd.BaseModel):
    session_id: str
    student_id: str
    lecture_id: str


class GradeResponse(pd.BaseModel):
    grade: float
    explanation: str
    missing_topics: list[str]


class ReportJson(pd.BaseModel):
    session_id: str
    student_id: str
    timestamp: str
    final_grade: float


class ReportResponse(pd.BaseModel):
    report_text: str
    report_json: ReportJson