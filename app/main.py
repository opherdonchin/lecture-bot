import fastapi as fa
import pydantic as pd
import sqlalchemy.orm as sqlalchemy_orm
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import app.bot_engine as bot_engine
import app.config as config_module
import app.db as db_module
import app.lecture_loader as lecture_loader
import app.models as models
import app.session_manager as session_manager

app = fa.FastAPI(title="Lecture Bot")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def root(request: fa.Request):
    """Serve the chat UI."""
    return templates.TemplateResponse(request, "chat.html")


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


# Request/Response models
class StartSessionRequest(pd.BaseModel):
    student_id: str
    lecture_id: str


class StartSessionResponse(pd.BaseModel):
    session_id: str
    message: str


class SendMessageRequest(pd.BaseModel):
    session_id: str
    message: str


class SendMessageResponse(pd.BaseModel):
    message: str
    session_active: bool


# API endpoints
@app.post("/start_session", response_model=StartSessionResponse)
def start_session(request: StartSessionRequest, db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db)):
    """Start a new tutoring session."""
    settings = config_module.get_settings()
    
    # Load the lecture package
    try:
        lecture_package = lecture_loader.load_lecture_package(settings.lectures_dir, request.lecture_id)
    except lecture_loader.LectureNotFoundError as e:
        raise fa.HTTPException(status_code=404, detail=str(e))
    
    # Create the session
    session = session_manager.create_session(db, request.student_id, request.lecture_id, lecture_package)
    
    # Generate opening message
    opening_message = bot_engine.build_opening_message(lecture_package)
    
    # Save the opening message
    session_manager.append_message(db, session.session_id, "assistant", opening_message)
    db.commit()

    return StartSessionResponse(session_id=session.session_id, message=opening_message)


@app.post("/send_message", response_model=SendMessageResponse)
def send_message(request: SendMessageRequest, db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db)):
    """Send a message in an active session."""
    session = db.query(models.SessionModel).filter(models.SessionModel.session_id == request.session_id).first()
    if not session:
        raise fa.HTTPException(status_code=404, detail="Session not found")

    if session.ended_at is not None:
        raise fa.HTTPException(status_code=400, detail="Session has ended")

    state = session_manager.load_state(db, request.session_id)

    bot_reply, updated_state = bot_engine.generate_reply(request.message, state)

    session_manager.append_message(db, request.session_id, "user", request.message)
    session_manager.append_message(db, request.session_id, "assistant", bot_reply)
    session_manager.save_state(db, request.session_id, updated_state)

    db.commit()

    return SendMessageResponse(message=bot_reply, session_active=True)


# ---------------------------------------------------------------------------
# Control action models
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Control action endpoints
# ---------------------------------------------------------------------------

def _get_active_session(db: sqlalchemy_orm.Session, session_id: str) -> models.SessionModel:
    """Return session or raise 404. Does not check ended_at — callers decide."""
    session = db.query(models.SessionModel).filter(
        models.SessionModel.session_id == session_id
    ).first()
    if not session:
        raise fa.HTTPException(status_code=404, detail="Session not found")
    return session


@app.post("/get_grade", response_model=GradeResponse)
def get_grade(request: SessionIdRequest, db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db)):
    """Return a stub current grade. Real grading will call the LLM."""
    session = _get_active_session(db, request.session_id)
    state = session_manager.load_state(db, session.session_id)

    # Stub: return stored grade and state info until LLM grading is wired in
    grade = session.current_grade or 0.0
    covered = state.get("topics_covered", [])
    sampled = state.get("topics_sampled", [])
    missing = [t for t in sampled if t not in covered]

    return GradeResponse(
        grade=grade,
        explanation=f"Stub grade based on {len(covered)} covered topic(s) out of {len(sampled)} sampled.",
        missing_topics=missing,
    )


@app.post("/generate_report", response_model=ReportResponse)
def generate_report(request: SessionIdRequest, db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db)):
    """Return a stub final report. Real report will call the LLM."""
    import datetime as dt

    session = _get_active_session(db, request.session_id)
    state = session_manager.load_state(db, session.session_id)

    grade = session.current_grade or 0.0
    turn_count = state.get("turn_count", 0)
    covered = state.get("topics_covered", [])

    report_text = (
        f"Session report for {session.student_id} — {session.lecture_id}. "
        f"Turns: {turn_count}. Topics covered: {len(covered)}. "
        f"Current grade: {grade}/100. "
        "(Stub — full LLM-generated report coming once OpenAI is integrated.)"
    )

    return ReportResponse(
        report_text=report_text,
        report_json=ReportJson(
            session_id=session.session_id,
            student_id=session.student_id,
            timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
            final_grade=grade,
        ),
    )


@app.post("/restart_session", response_model=StartSessionResponse)
def restart_session(request: RestartSessionRequest, db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db)):
    """End the current session and create a fresh one for the same student/lecture."""
    import datetime as dt

    old_session = _get_active_session(db, request.session_id)

    # End the old session
    old_session.ended_at = dt.datetime.now(dt.timezone.utc)
    db.flush()

    # Load lecture package for new session
    settings = config_module.get_settings()
    try:
        lecture_package = lecture_loader.load_lecture_package(settings.lectures_dir, request.lecture_id)
    except lecture_loader.LectureNotFoundError as e:
        raise fa.HTTPException(status_code=404, detail=str(e))

    new_session = session_manager.create_session(db, request.student_id, request.lecture_id, lecture_package)
    opening_message = bot_engine.build_opening_message(lecture_package)
    session_manager.append_message(db, new_session.session_id, "assistant", opening_message)
    db.commit()

    return StartSessionResponse(session_id=new_session.session_id, message=opening_message)
