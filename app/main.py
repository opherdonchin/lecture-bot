import datetime as dt
import json as j_

import fastapi as fa
import sqlalchemy.orm as sqlalchemy_orm
from fastapi.responses import HTMLResponse
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


@app.get("/", response_class=HTMLResponse)
def root(request: fa.Request):
    """Serve the chat UI."""
    return templates.TemplateResponse(request, "chat.html")


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


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
    
    # Generate opening message
    opening_message = bot_engine.build_opening_message(lecture_package)
    
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

    # Enforce session timeout
    started_at = session.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=dt.timezone.utc)
    timeout_at = started_at + dt.timedelta(minutes=settings.session_timeout_minutes)
    if dt.datetime.now(dt.timezone.utc) > timeout_at:
        session.ended_at = dt.datetime.now(dt.timezone.utc)
        db.commit()
        raise fa.HTTPException(status_code=400, detail="Session has timed out")

    state = session_manager.load_state(db, request.session_id)

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

    bot_reply, updated_state = bot_engine.generate_reply(
        lecture_package=lecture_package,
        recent_messages=recent_messages,
        state=state,
        user_message=request.message,
    )

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


@app.post("/get_grade", response_model=schema.GradeResponse)
def get_grade(request: schema.SessionIdRequest, db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db)):
    """Compute and return the current grade using real LLM grading."""
    session = _get_active_session(db, request.session_id)
    state = session_manager.load_state(db, session.session_id)

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

    payload = {
        "candidate_grade": candidate_grade,
        "accepted_as_current": accepted_as_current,
        "topic_scores": grading_result["topic_scores"],
        "explanation": grading_result["explanation"],
        "missing_topics": grading_result["missing_topics"],
    }
    db.add(models.GradeEventModel(
        session_id=session.session_id,
        event_type="grade",
        grade=float(candidate_grade),
        payload_json=j_.dumps(payload, ensure_ascii=False),
    ))
    db.commit()

    # Use the authoritative accepted payload for the response
    if accepted_as_current:
        auth_explanation = grading_result["explanation"]
        auth_missing = grading_result["missing_topics"]
        auth_grade = float(candidate_grade)
    else:
        prior = _get_authoritative_grading_payload(db, session.session_id)
        if prior:
            auth_explanation = prior.get("explanation", "")
            auth_missing = prior.get("missing_topics", [])
        else:
            auth_explanation = grading_result["explanation"]
            auth_missing = grading_result["missing_topics"]
        auth_grade = float(session.current_grade or 0.0)

    return schema.GradeResponse(
        grade=auth_grade,
        explanation=auth_explanation,
        missing_topics=auth_missing,
    )


@app.post("/generate_report", response_model=schema.ReportResponse)
def generate_report(request: schema.SessionIdRequest, db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db)):
    """Generate a final session report using real LLM grading and report generation."""
    session = _get_active_session(db, request.session_id)
    state = session_manager.load_state(db, session.session_id)

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

    raw_grading = bot_engine.generate_topic_scores(
        lecture_package=lecture_package,
        messages=messages,
        state=state,
    )

    candidate_grade = bot_engine.compute_weighted_grade(raw_grading["topic_scores"])
    stored_grade = session.current_grade or 0.0
    accepted_as_current = candidate_grade > stored_grade

    if accepted_as_current:
        session.current_grade = float(candidate_grade)
        auth_grade = float(candidate_grade)
        auth_explanation = raw_grading["explanation"]
        auth_missing = raw_grading["missing_topics"]
        auth_topic_scores = raw_grading["topic_scores"]
    else:
        auth_grade = float(session.current_grade or 0.0)
        prior = _get_authoritative_grading_payload(db, session.session_id)
        if prior:
            auth_explanation = prior.get("explanation", "")
            auth_missing = prior.get("missing_topics", [])
            auth_topic_scores = prior.get("topic_scores", [])
        else:
            auth_explanation = raw_grading["explanation"]
            auth_missing = raw_grading["missing_topics"]
            auth_topic_scores = raw_grading["topic_scores"]

    timestamp_iso = dt.datetime.now(dt.timezone.utc).isoformat()

    grading_result = {
        "final_grade": auth_grade,
        "topic_scores": auth_topic_scores,
        "explanation": auth_explanation,
        "missing_topics": auth_missing,
        "accepted_as_current": accepted_as_current,
    }

    report_result = bot_engine.generate_report(
        lecture_package=lecture_package,
        messages=messages,
        state=state,
        grading_result=grading_result,
        session_id=session.session_id,
        student_id=session.student_id,
        timestamp_iso=timestamp_iso,
    )

    report_payload = {
        "candidate_grade": candidate_grade,
        "accepted_as_current": accepted_as_current,
        "topic_scores": auth_topic_scores,
        "explanation": auth_explanation,
        "missing_topics": auth_missing,
        "report_text": report_result["report_text"],
    }
    db.add(models.GradeEventModel(
        session_id=session.session_id,
        event_type="report",
        grade=float(auth_grade),
        payload_json=j_.dumps(report_payload, ensure_ascii=False),
    ))
    db.commit()

    return schema.ReportResponse(
        report_text=report_result["report_text"],
        report_json=schema.ReportJson(
            session_id=session.session_id,
            student_id=session.student_id,
            timestamp=timestamp_iso,
            final_grade=auth_grade,
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
    opening_message = bot_engine.build_opening_message(lecture_package)
    session_manager.append_message(db, new_session.session_id, "assistant", opening_message)
    db.commit()

    return schema.StartSessionResponse(session_id=new_session.session_id, message=opening_message)
