from typing import Literal

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
    final_missing_topics: list[str] = pd.Field(default_factory=list)


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
    lecture_id: str
    started_at: str
    timestamp: str
    final_grade: float


class ReportResponse(pd.BaseModel):
    report_text: str
    report_json: ReportJson


# ---------------------------------------------------------------------------
# Classifier and policy routing schemas
# ---------------------------------------------------------------------------

class ClassifierMessage(pd.BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ClassifierStateExcerpt(pd.BaseModel):
    last_top_classification: str | None = None
    last_recommended_policy: str | None = None
    last_effective_policy: str | None = None
    consecutive_redirects: int = 0
    consecutive_meta_requests: int = 0
    consecutive_clarifications: int = 0
    last_policy_override_reason: str | None = None


class ClassifierInput(pd.BaseModel):
    latest_user_message: str = pd.Field(..., min_length=1)
    recent_messages: list[ClassifierMessage] = pd.Field(default_factory=list)
    state: ClassifierStateExcerpt = pd.Field(default_factory=ClassifierStateExcerpt)


class ClassifierResult(pd.BaseModel):
    top_classification: Literal[
        "content_answer",
        "content_question",
        "technical_request",
        "meta_request",
        "off_task",
    ]
    class_probabilities: dict[str, float]
    recommended_policy: Literal[
        "respond",
        "provide_content_support",
        "provide_technical_support",
        "redirect",
    ]
    policy_confidence: float
    short_reason: str


class PolicyDecision(pd.BaseModel):
    effective_policy: Literal[
        "respond",
        "provide_content_support",
        "provide_technical_support",
        "redirect",
        "seek_clarification",
    ]
    used_classifier_recommendation: bool
    override_reason: str | None = None
    matched_backstop: str | None = None
    ambiguity_summary: str | None = None
