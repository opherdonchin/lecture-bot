import datetime as dt
import json as j_

import fastapi as fa
import sqlalchemy.orm as sqlalchemy_orm
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import app.bot_engine as bot_engine
import app.config as config_module
import app.db as db_module
import app.lecture_loader as lecture_loader
import app.models as models
import app.schema as schema
import app.session_manager as session_manager

app = fa.FastAPI(title="Lecture Bot")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("app/static/bot.svg")


@app.get("/", response_class=HTMLResponse)
def root(request: fa.Request):
    """Serve the chat UI."""
    return templates.TemplateResponse(request, "chat.html")


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/lectures", response_model=list[str])
def list_lectures():
    """List available lecture IDs."""
    lectures_dir = config_module.get_settings().lectures_dir
    if not lectures_dir.exists():
        return []
    return sorted(
        d.name for d in lectures_dir.iterdir()
        if d.is_dir() and (d / "lecture_config.json").exists()
    )


# API endpoints
@app.post("/start_session", response_model=schema.StartSessionResponse)
def start_session(request: schema.StartSessionRequest, db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db)):
    """Start a new tutoring session."""
    settings = config_module.get_settings()
    
    # Load the lecture package
    try:
        lecture_package = lecture_loader.load_lecture_package(settings.lectures_dir, request.lecture_id)
    except lecture_loader.LectureNotFoundError as e:
        raise fa.HTTPException(status_code=404, detail=str(e))
    
    # Create the session
    session = session_manager.create_session(db, request.student_id, request.lecture_id, lecture_package)
    state = session_manager.load_state(db, session.session_id)
    
    # Generate opening message
    opening_message = bot_engine.build_opening_message(
        lecture_package,
        sampled_topic_ids=state.get("topics_sampled", []),
    )
    
    # Save the opening message
    session_manager.append_message(db, session.session_id, "assistant", opening_message)
    db.commit()

    return schema.StartSessionResponse(session_id=session.session_id, message=opening_message)


@app.post("/send_message", response_model=schema.SendMessageResponse)
def send_message(request: schema.SendMessageRequest, db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db)):
    """Send a message in an active session."""
    session = db.query(models.SessionModel).filter(models.SessionModel.session_id == request.session_id).first()
    if not session:
        raise fa.HTTPException(status_code=404, detail="Session not found")

    if session.ended_at is not None:
        raise fa.HTTPException(status_code=400, detail="Session has ended")

    settings = config_module.get_settings()
    state = session_manager.load_state(db, request.session_id)

    # Enforce session timeout
    now = dt.datetime.now(dt.timezone.utc)
    started_at = session.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=dt.timezone.utc)
    timeout_at = started_at + dt.timedelta(minutes=settings.session_timeout_minutes)
    if now > timeout_at:
        grade_snapshot = _compute_authoritative_grade_snapshot(db, session, state)
        payload = {
            "candidate_grade": grade_snapshot["candidate_grade"],
            "accepted_as_current": grade_snapshot["accepted_as_current"],
            "topic_scores": grade_snapshot["topic_scores"],
            "explanation": grade_snapshot["explanation"],
            "missing_topics": grade_snapshot["missing_topics"],
        }
        _record_grade_event(
            db,
            session.session_id,
            event_type="grade",
            grade=grade_snapshot["candidate_grade"],
            payload=payload,
        )
        closing_message = _build_timeout_closing_message(settings, grade_snapshot["grade"])
        session_manager.append_message(db, request.session_id, "assistant", closing_message)
        session.ended_at = now
        db.commit()
        return schema.SendMessageResponse(
            message=closing_message,
            session_active=False,
            ended_reason="timeout",
            final_grade=grade_snapshot["grade"],
            final_grade_explanation=grade_snapshot["explanation"],
            final_missing_topics=grade_snapshot["missing_topics"],
        )

    # Reload lecture package
    try:
        lecture_package = lecture_loader.load_lecture_package(settings.lectures_dir, session.lecture_id)
    except lecture_loader.LectureNotFoundError as e:
        raise fa.HTTPException(status_code=404, detail=str(e))

    # Fetch recent messages in chronological order
    all_msgs = (
        db.query(models.MessageModel)
        .filter(models.MessageModel.session_id == request.session_id)
        .order_by(models.MessageModel.id.asc())
        .all()
    )
    recent_rows = all_msgs[-settings.recent_message_limit:]
    recent_messages = bot_engine.serialize_messages(recent_rows)

    remaining_seconds = max(0.0, (timeout_at - now).total_seconds())
    should_warn_timeout = (
        remaining_seconds <= settings.session_warning_minutes * 60
        and not state.get("timeout_warning_sent", False)
    )

    bot_reply, updated_state = bot_engine.generate_reply(
        db=db,
        session_id=request.session_id,
        turn_index=state.get("turn_count", 0),
        lecture_package=lecture_package,
        recent_messages=recent_messages,
        state=state,
        user_message=request.message,
    )

    if should_warn_timeout:
        minutes_left = max(1, int((remaining_seconds + 59) // 60))
        bot_reply = (
            f"{bot_reply}\n\n"
            f"We have about {minutes_left} minutes left in this session. "
            "When time runs out, I'll wrap up with your final grade and you can start a new session if you'd like."
        )
        updated_state["timeout_warning_sent"] = True

    session_manager.append_message(db, request.session_id, "user", request.message)
    session_manager.append_message(db, request.session_id, "assistant", bot_reply)
    session_manager.save_state(db, request.session_id, updated_state)

    db.commit()

    return schema.SendMessageResponse(message=bot_reply, session_active=True)


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


def _get_authoritative_grading_payload(db: sqlalchemy_orm.Session, session_id: str) -> dict | None:
    """Return the payload dict from the highest accepted grading event (grade or report), or None.

    Searches both event types so that a high-grade report event is visible to get_grade,
    and a high-grade grade event is visible to generate_report.
    Returns the most-recent accepted event's payload (most-recent = highest accepted, given
    the monotone rule).
    """
    events = (
        db.query(models.GradeEventModel)
        .filter(models.GradeEventModel.session_id == session_id)
        .filter(models.GradeEventModel.event_type.in_(["grade", "report"]))
        .order_by(models.GradeEventModel.id.desc())
        .all()
    )
    for event in events:
        payload = j_.loads(event.payload_json or "{}")
        if payload.get("accepted_as_current"):
            return payload
    return None


def _compute_authoritative_grade_snapshot(
    db: sqlalchemy_orm.Session,
    session: models.SessionModel,
    state: dict,
) -> dict:
    """Compute the authoritative grading snapshot for a session."""
    settings = config_module.get_settings()
    try:
        lecture_package = lecture_loader.load_lecture_package(settings.lectures_dir, session.lecture_id)
    except lecture_loader.LectureNotFoundError as e:
        raise fa.HTTPException(status_code=404, detail=str(e))

    all_msgs = (
        db.query(models.MessageModel)
        .filter(models.MessageModel.session_id == session.session_id)
        .order_by(models.MessageModel.id.asc())
        .all()
    )
    messages = bot_engine.serialize_messages(all_msgs)

    grading_result = bot_engine.generate_topic_scores(
        lecture_package=lecture_package,
        messages=messages,
        state=state,
    )

    candidate_grade = bot_engine.compute_weighted_grade(grading_result["topic_scores"])
    stored_grade = session.current_grade or 0.0
    accepted_as_current = candidate_grade > stored_grade

    if accepted_as_current:
        session.current_grade = float(candidate_grade)
        auth_grade = float(candidate_grade)
        auth_explanation = grading_result["explanation"]
        auth_missing = grading_result["missing_topics"]
        auth_topic_scores = grading_result["topic_scores"]
    else:
        auth_grade = float(session.current_grade or 0.0)
        prior = _get_authoritative_grading_payload(db, session.session_id)
        if prior:
            auth_explanation = prior.get("explanation", "")
            auth_missing = prior.get("missing_topics", [])
            auth_topic_scores = prior.get("topic_scores", [])
        else:
            auth_explanation = grading_result["explanation"]
            auth_missing = grading_result["missing_topics"]
            auth_topic_scores = grading_result["topic_scores"]

    return {
        "lecture_package": lecture_package,
        "messages": messages,
        "candidate_grade": candidate_grade,
        "accepted_as_current": accepted_as_current,
        "grade": auth_grade,
        "topic_scores": auth_topic_scores,
        "explanation": auth_explanation,
        "missing_topics": auth_missing,
    }


def _record_grade_event(
    db: sqlalchemy_orm.Session,
    session_id: str,
    *,
    event_type: str,
    grade: float,
    payload: dict,
) -> None:
    db.add(models.GradeEventModel(
        session_id=session_id,
        event_type=event_type,
        grade=float(grade),
        payload_json=j_.dumps(payload, ensure_ascii=False),
    ))


def _build_timeout_closing_message(settings: config_module.Settings, final_grade: float) -> str:
    grade_text = int(final_grade) if float(final_grade).is_integer() else round(final_grade, 1)
    return (
        f"Thanks for working through this session with me. "
        f"The {settings.session_timeout_minutes}-minute session has ended. "
        f"Your final grade for this session is {grade_text} / 100. "
        "You can start a new session anytime if you'd like to keep practicing."
    )


@app.post("/get_grade", response_model=schema.GradeResponse)
def get_grade(request: schema.SessionIdRequest, db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db)):
    """Compute and return the current grade using real LLM grading."""
    session = _get_active_session(db, request.session_id)
    state = session_manager.load_state(db, session.session_id)
    grade_snapshot = _compute_authoritative_grade_snapshot(db, session, state)
    payload = {
        "candidate_grade": grade_snapshot["candidate_grade"],
        "accepted_as_current": grade_snapshot["accepted_as_current"],
        "topic_scores": grade_snapshot["topic_scores"],
        "explanation": grade_snapshot["explanation"],
        "missing_topics": grade_snapshot["missing_topics"],
    }
    _record_grade_event(
        db,
        session.session_id,
        event_type="grade",
        grade=grade_snapshot["candidate_grade"],
        payload=payload,
    )
    db.commit()

    return schema.GradeResponse(
        grade=grade_snapshot["grade"],
        explanation=grade_snapshot["explanation"],
        missing_topics=grade_snapshot["missing_topics"],
    )


@app.post("/generate_report", response_model=schema.ReportResponse)
def generate_report(request: schema.SessionIdRequest, db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db)):
    """Generate a final session report using real LLM grading and report generation."""
    session = _get_active_session(db, request.session_id)
    state = session_manager.load_state(db, session.session_id)
    settings = config_module.get_settings()
    grade_snapshot = _compute_authoritative_grade_snapshot(db, session, state)

    timestamp_iso = dt.datetime.now(dt.timezone.utc).isoformat()

    grading_result = {
        "final_grade": grade_snapshot["grade"],
        "topic_scores": grade_snapshot["topic_scores"],
        "explanation": grade_snapshot["explanation"],
        "missing_topics": grade_snapshot["missing_topics"],
        "accepted_as_current": grade_snapshot["accepted_as_current"],
    }

    report_result = bot_engine.generate_report(
        lecture_package=grade_snapshot["lecture_package"],
        messages=grade_snapshot["messages"],
        state=state,
        grading_result=grading_result,
        session_id=session.session_id,
        student_id=session.student_id,
        timestamp_iso=timestamp_iso,
    )

    report_payload = {
        "candidate_grade": grade_snapshot["candidate_grade"],
        "accepted_as_current": grade_snapshot["accepted_as_current"],
        "topic_scores": grade_snapshot["topic_scores"],
        "explanation": grade_snapshot["explanation"],
        "missing_topics": grade_snapshot["missing_topics"],
        "report_text": report_result["report_text"],
    }
    _record_grade_event(
        db,
        session.session_id,
        event_type="report",
        grade=grade_snapshot["grade"],
        payload=report_payload,
    )
    db.commit()

    return schema.ReportResponse(
        report_text=report_result["report_text"],
        report_json=schema.ReportJson(
            session_id=session.session_id,
            student_id=session.student_id,
            lecture_id=session.lecture_id,
            started_at=session.started_at.isoformat(),
            timestamp=timestamp_iso,
            final_grade=grade_snapshot["grade"],
        ),
    )


@app.post("/restart_session", response_model=schema.StartSessionResponse)
def restart_session(request: schema.RestartSessionRequest, db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db)):
    """End the current session and create a fresh one for the same student/lecture."""
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
    state = session_manager.load_state(db, new_session.session_id)
    opening_message = bot_engine.build_opening_message(
        lecture_package,
        sampled_topic_ids=state.get("topics_sampled", []),
    )
    session_manager.append_message(db, new_session.session_id, "assistant", opening_message)
    db.commit()

    return schema.StartSessionResponse(session_id=new_session.session_id, message=opening_message)
