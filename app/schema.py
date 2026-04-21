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
    ended_reason: str | None = None
    final_grade: float | None = None
    final_grade_explanation: str | None = None
    final_scored_topics: list[str] = pd.Field(default_factory=list)
    final_missing_topics: list[str] = pd.Field(default_factory=list)
    final_report: "ReportResponse | None" = None


class SessionIdRequest(pd.BaseModel):
    session_id: str


class RestartSessionRequest(pd.BaseModel):
    session_id: str
    student_id: str
    lecture_id: str


class GradeResponse(pd.BaseModel):
    grade: float
    explanation: str
    scored_topics: list[str]
    missing_topics: list[str]
    minutes_elapsed: int
    minutes_remaining: int
    session_duration_minutes: int


class ReportJson(pd.BaseModel):
    session_id: str
    student_id: str
    lecture_id: str
    started_at: str
    timestamp: str
    final_grade: float
    minutes_elapsed: int
    minutes_remaining: int
    session_duration_minutes: int


class ReportResponse(pd.BaseModel):
    report_text: str
    report_json: ReportJson


SendMessageResponse.model_rebuild()
