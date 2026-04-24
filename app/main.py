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
import app.language_policy as language_policy
import app.lecture_loader as lecture_loader
import app.models as models
import app.root_path as root_path_module
import app.schema as schema
import app.session_manager as session_manager

app = fa.FastAPI(title="Lecture Bot", root_path=config_module.get_settings().student_root_path)
app.add_middleware(
    root_path_module.RootPathStripMiddleware,
    configured_root_path=config_module.get_settings().student_root_path,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def _url_path(request: fa.Request, route_name: str, **path_params: str) -> str:
    return request.url_for(route_name, **path_params).path


def _student_route_config(request: fa.Request) -> dict[str, str]:
    return {
        "list_lectures": _url_path(request, "list_lectures"),
        "start_session": _url_path(request, "start_session"),
        "send_message": _url_path(request, "send_message"),
        "get_grade": _url_path(request, "get_grade"),
        "generate_report": _url_path(request, "generate_report"),
        "restart_session": _url_path(request, "restart_session"),
    }


@app.get("/favicon.ico", include_in_schema=False, name="favicon")
async def favicon():
    return FileResponse("app/static/bot.svg")


@app.get("/", response_class=HTMLResponse, name="student_root")
def root(request: fa.Request):
    """Serve the chat UI."""
    return templates.TemplateResponse(
        request,
        "chat.html",
        {
            "url_path": lambda route_name, **path_params: _url_path(request, route_name, **path_params),
            "app_routes": _student_route_config(request),
        },
    )


@app.get("/health", name="health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/lectures", response_model=list[str], name="list_lectures")
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
@app.post("/start_session", response_model=schema.StartSessionResponse, name="start_session")
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


@app.post("/send_message", response_model=schema.SendMessageResponse, name="send_message")
def send_message(request: schema.SendMessageRequest, db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db)):
    """Send a message in an active session."""
    session = db.query(models.SessionModel).filter(models.SessionModel.session_id == request.session_id).first()
    if not session:
        raise fa.HTTPException(status_code=404, detail="Session not found")

    if session.ended_at is not None:
        raise fa.HTTPException(status_code=400, detail="Session has ended")

    settings = config_module.get_settings()
    state = session_manager.load_state(db, request.session_id)

    if not language_policy.is_english_text(request.message):
        refusal_message = language_policy.ENGLISH_ONLY_STUDENT_MESSAGE
        session_manager.append_message(db, request.session_id, "user", request.message)
        session_manager.append_message(db, request.session_id, "assistant", refusal_message)
        session_manager.save_state(db, request.session_id, state)
        db.commit()
        return schema.SendMessageResponse(message=refusal_message, session_active=True)

    # Enforce session timeout
    now = dt.datetime.now(dt.timezone.utc)
    started_at = session.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=dt.timezone.utc)
    timeout_at = started_at + dt.timedelta(minutes=settings.session_timeout_minutes)
    if now > timeout_at:
        grade_snapshot = _compute_authoritative_grade_snapshot(
            db,
            session=session,
            state=state,
        )
        _record_grade_event(
            db,
            session_id=session.session_id,
            event_type="grade",
            grade=grade_snapshot["candidate_grade"],
            payload=grade_snapshot["payload"],
        )
        final_report = _generate_authoritative_report_result(
            db,
            session=session,
            state=state,
            grade_snapshot=grade_snapshot,
        )
        closing_message = _build_timeout_closing_message(settings, grade_snapshot["grade"])
        session_manager.append_message(db, request.session_id, "assistant", closing_message)
        session_manager.save_state(db, request.session_id, state)
        session.ended_at = now
        db.commit()
        return schema.SendMessageResponse(
            message=closing_message,
            session_active=False,
            ended_reason="timeout",
            final_grade=grade_snapshot["grade"],
            final_grade_explanation=grade_snapshot["explanation"],
            final_scored_topics=grade_snapshot["scored_topics"],
            final_missing_topics=grade_snapshot["missing_topics"],
            final_report=final_report,
        )

    # Reload lecture package
    lecture_package = _load_lecture_package_for_session(session)
    _update_backend_grade_state(
        db,
        session=session,
        state=state,
        lecture_package=lecture_package,
    )

    # Fetch recent messages in chronological order
    all_messages = _load_session_messages(db, request.session_id)
    recent_messages = all_messages[-settings.recent_message_limit:]

    remaining_seconds = max(0.0, (timeout_at - now).total_seconds())
    elapsed_seconds = max(0.0, (now - started_at).total_seconds())
    minutes_left = max(1, int((remaining_seconds + 59) // 60))
    should_warn_timeout = (
        remaining_seconds <= settings.session_warning_minutes * 60
        and not state.get("timeout_warning_sent", False)
    )
    timing_context = {
        "minutes_remaining": minutes_left,
        "minutes_elapsed": int(elapsed_seconds // 60),
        "session_duration_minutes": settings.session_timeout_minutes,
        "closing_mode": remaining_seconds <= settings.session_warning_minutes * 60,
        "timeout_warning_sent": bool(state.get("timeout_warning_sent", False)),
        "timing_reliable": True,
    }

    normalized_user_message = bot_engine.rewrite_opening_topic_selection(
        lecture_package=lecture_package,
        state=state,
        user_message=request.message,
    )
    topic_defs = bot_engine.resolve_topic_defs(lecture_package)
    lecture_context = bot_engine.build_dialogue_context(
        lecture_package,
        settings.max_dialogue_context_chars,
    )
    rendered_system_prompt = bot_engine.build_dialogue_system_prompt(
        lecture_package=lecture_package,
        state=state,
        topic_defs=topic_defs,
        lecture_context=lecture_context,
        timing_context=timing_context,
        private_artifact_schema_json=session.private_artifact_schema_json,
    )

    bot_reply, updated_state, private_artifact = bot_engine.generate_reply(
        lecture_package=lecture_package,
        recent_messages=recent_messages,
        state=state,
        user_message=request.message,
        timing_context=timing_context,
        private_artifact_schema_json=session.private_artifact_schema_json,
    )
    validation_error = None
    if session.private_artifact_schema_json is not None:
        validation_error = bot_engine.validate_private_artifact(
            private_artifact,
            session.private_artifact_schema_json,
        )
        if validation_error is not None:
            repair_instruction = _build_private_artifact_repair_instruction(validation_error)
            rendered_system_prompt = _append_repair_instruction(
                rendered_system_prompt,
                repair_instruction,
            )
            bot_reply, updated_state, private_artifact = bot_engine.generate_reply(
                lecture_package=lecture_package,
                recent_messages=recent_messages,
                state=state,
                user_message=request.message,
                timing_context=timing_context,
                private_artifact_schema_json=session.private_artifact_schema_json,
                repair_instruction=repair_instruction,
            )
            validation_error = bot_engine.validate_private_artifact(
                private_artifact,
                session.private_artifact_schema_json,
            )
            if validation_error is not None:
                fallback_state = dict(state)
                fallback_state["turn_count"] = state.get("turn_count", 0) + 1
                bot_reply = bot_engine._FALLBACK_DIALOGUE_MESSAGE
                updated_state = fallback_state
                private_artifact = None

    if should_warn_timeout:
        updated_state["timeout_warning_sent"] = True

    _update_backend_grade_state(
        db,
        session=session,
        state=updated_state,
        lecture_package=lecture_package,
    )
    turn_index = int(updated_state.get("turn_count", state.get("turn_count", 0) + 1))
    _record_dialogue_turn_audit(
        db,
        session_id=request.session_id,
        turn_index=turn_index,
        state_before=state,
        recent_messages=recent_messages,
        normalized_user_message=normalized_user_message,
        rendered_system_prompt=rendered_system_prompt,
        prompt_template_name=bot_engine.get_tutor_prompt_template(lecture_package),
        settings=settings,
        updated_state=updated_state,
        bot_reply=bot_reply,
        original_user_message=request.message,
    )
    if session.private_artifact_schema_json is not None:
        _record_private_artifact_log(
            db,
            session_id=request.session_id,
            turn_index=turn_index,
            private_artifact=private_artifact,
            validation_error=validation_error,
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


def _topic_id_to_label_map(lecture_package: dict) -> dict[str, str]:
    topic_defs = bot_engine.resolve_topic_defs(lecture_package)
    return {topic["topic_id"]: topic["label"] for topic in topic_defs}


def _labelled_scored_topics(topic_scores: list[dict], topic_id_to_label: dict[str, str]) -> list[str]:
    scored_topic_ids = {
        str(ts.get("topic_id", ""))
        for ts in topic_scores
        if isinstance(ts, dict) and str(ts.get("topic_id", "")) in topic_id_to_label
    }
    return [
        label
        for topic_id, label in topic_id_to_label.items()
        if topic_id in scored_topic_ids
    ]


def _coerce_mastery_map(raw_mastery: dict | None, allowed_topic_ids: set[str]) -> dict[str, int]:
    if not isinstance(raw_mastery, dict):
        return {}
    mastery: dict[str, int] = {}
    for topic_id, score in raw_mastery.items():
        if not isinstance(topic_id, str) or topic_id not in allowed_topic_ids:
            continue
        try:
            mastery[topic_id] = max(0, min(100, int(score)))
        except (TypeError, ValueError):
            continue
    return mastery


def _join_labels(labels: list[str]) -> str:
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


def _load_lecture_package_for_session(session: models.SessionModel) -> dict:
    settings = config_module.get_settings()
    try:
        return lecture_loader.load_lecture_package(settings.lectures_dir, session.lecture_id)
    except lecture_loader.LectureNotFoundError as e:
        raise fa.HTTPException(status_code=404, detail=str(e))


def _load_session_messages(db: sqlalchemy_orm.Session, session_id: str) -> list[dict]:
    all_msgs = (
        db.query(models.MessageModel)
        .filter(models.MessageModel.session_id == session_id)
        .order_by(models.MessageModel.id.asc())
        .all()
    )
    return bot_engine.serialize_messages(all_msgs)


def _record_grade_event(
    db: sqlalchemy_orm.Session,
    *,
    session_id: str,
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


def _build_private_artifact_repair_instruction(validation_error: str) -> str:
    return (
        "Your previous JSON output violated the private artifact contract: "
        f"{validation_error}. Return the full response JSON for the same student turn again. "
        "Because private_artifact_schema_json is present, include a top-level private_artifact "
        "that conforms exactly to the injected schema. Keep private_artifact out of "
        "assistant_message and updated_state."
    )


def _append_repair_instruction(rendered_system_prompt: str, repair_instruction: str) -> str:
    return f"{rendered_system_prompt}\n\nRepair instruction\n\n{repair_instruction.strip()}"


def _extract_turn_target_topic_id(updated_state: dict) -> str | None:
    current_topic_id = updated_state.get("current_topic_id")
    if isinstance(current_topic_id, str) and current_topic_id:
        return current_topic_id
    mastery = updated_state.get("mastery")
    if isinstance(mastery, dict) and mastery:
        topic_id = next(iter(mastery))
        if isinstance(topic_id, str) and topic_id:
            return topic_id
    return None


def _record_private_artifact_log(
    db: sqlalchemy_orm.Session,
    *,
    session_id: str,
    turn_index: int,
    private_artifact: object,
    validation_error: str | None,
) -> None:
    artifact_json = None
    if private_artifact is not None:
        artifact_json = j_.dumps(private_artifact, ensure_ascii=False)
    db.add(models.PrivateArtifactLogModel(
        session_id=session_id,
        turn_index=int(turn_index),
        artifact_json=artifact_json,
        validation_error=validation_error,
    ))


def _record_dialogue_turn_audit(
    db: sqlalchemy_orm.Session,
    *,
    session_id: str,
    turn_index: int,
    state_before: dict,
    recent_messages: list[dict],
    normalized_user_message: str,
    rendered_system_prompt: str,
    prompt_template_name: str,
    settings: config_module.Settings,
    updated_state: dict,
    bot_reply: str,
    original_user_message: str,
) -> None:
    repetition_markers = ("repeat", "repeating", "already asked", "already did", "again")
    repetition_complaint = any(marker in original_user_message.lower() for marker in repetition_markers)
    current_topic_before = state_before.get("current_topic_id")
    current_topic_after = updated_state.get("current_topic_id")
    db.add(models.DialogueTurnAuditModel(
        session_id=session_id,
        turn_index=int(turn_index),
        effective_policy="default",
        prompt_template_name=prompt_template_name,
        dialogue_model=settings.openai_model,
        state_before_json=j_.dumps(state_before, ensure_ascii=False),
        recent_messages_json=j_.dumps(recent_messages, ensure_ascii=False),
        user_message=normalized_user_message,
        rendered_system_prompt=rendered_system_prompt,
        tutor_mode="content_answer",
        action_hint_json="{}",
        challenge_level=1,
        current_topic_id=current_topic_before if isinstance(current_topic_before, str) else None,
        target_topic_id=_extract_turn_target_topic_id(updated_state),
        ended_with_content_question=bot_reply.strip().endswith("?"),
        repetition_complaint=repetition_complaint,
        switched_topics=(
            isinstance(current_topic_before, str)
            and isinstance(current_topic_after, str)
            and current_topic_before != current_topic_after
        ),
    ))


def _build_session_timing_snapshot(
    session: models.SessionModel,
    settings: config_module.Settings,
    *,
    now: dt.datetime | None = None,
) -> dict[str, int]:
    now = now or dt.datetime.now(dt.timezone.utc)
    started_at = session.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=dt.timezone.utc)
    elapsed_seconds = max(0.0, (now - started_at).total_seconds())
    remaining_seconds = max(0.0, settings.session_timeout_minutes * 60 - elapsed_seconds)
    return {
        "minutes_elapsed": int(elapsed_seconds // 60),
        "minutes_remaining": int((remaining_seconds + 59) // 60) if remaining_seconds > 0 else 0,
        "session_duration_minutes": settings.session_timeout_minutes,
    }


def _update_backend_grade_state(
    db: sqlalchemy_orm.Session,
    *,
    session: models.SessionModel,
    state: dict,
    lecture_package: dict,
) -> None:
    topic_id_to_label = _topic_id_to_label_map(lecture_package)
    allowed_topic_ids = set(topic_id_to_label)

    current_mastery = _coerce_mastery_map(state.get("mastery"), allowed_topic_ids)
    best_mastery = _coerce_mastery_map(state.get("best_mastery"), allowed_topic_ids)

    if not best_mastery:
        prior = _get_authoritative_grading_payload(db, session.session_id)
        if prior:
            for topic_score in prior.get("topic_scores", []):
                if not isinstance(topic_score, dict):
                    continue
                topic_id = str(topic_score.get("topic_id", ""))
                if topic_id not in allowed_topic_ids:
                    continue
                try:
                    best_mastery[topic_id] = max(
                        best_mastery.get(topic_id, 0),
                        max(0, min(100, int(topic_score.get("score", 0)))),
                    )
                except (TypeError, ValueError):
                    continue

    for topic_id, score in current_mastery.items():
        best_mastery[topic_id] = max(best_mastery.get(topic_id, 0), score)

    best_mastery = {
        topic_id: score
        for topic_id, score in best_mastery.items()
        if score > 0
    }
    topic_scores = [
        {"topic_id": topic_id, "score": score}
        for topic_id, score in best_mastery.items()
    ]
    current_grade = float(bot_engine.compute_weighted_grade(topic_scores))

    state["mastery"] = current_mastery
    state["best_mastery"] = best_mastery
    state["current_grade"] = current_grade
    session.current_grade = max(float(session.current_grade or 0.0), current_grade)


def _build_grade_snapshot_from_state(
    *,
    session: models.SessionModel,
    state: dict,
    lecture_package: dict,
    messages: list[dict],
) -> dict:
    topic_defs = bot_engine.resolve_topic_defs(lecture_package)
    topic_id_to_label = {topic["topic_id"]: topic["label"] for topic in topic_defs}
    best_mastery = _coerce_mastery_map(state.get("best_mastery"), set(topic_id_to_label))
    evidence_notes = state.get("evidence_notes", {})

    topic_scores = []
    for topic in topic_defs:
        topic_id = topic["topic_id"]
        score = best_mastery.get(topic_id, 0)
        if score <= 0:
            continue
        topic_scores.append({
            "topic_id": topic_id,
            "score": score,
            "rationale": str(evidence_notes.get(topic_id, "")),
        })

    scored_topics = [topic_id_to_label[ts["topic_id"]] for ts in topic_scores]
    missing_topics = [
        topic["label"]
        for topic in topic_defs
        if topic["topic_id"] not in best_mastery
    ]
    sorted_scores = sorted(topic_scores, key=lambda ts: (-ts["score"], ts["topic_id"]))
    strongest_topics = [
        topic_id_to_label[ts["topic_id"]]
        for ts in sorted_scores[:2]
    ]
    if not scored_topics:
        explanation = (
            "No strong footholds yet. Keep going with one lecture idea and show a clear distinction, explanation, or application."
        )
    elif len(scored_topics) == 1:
        explanation = f"Best demonstrated understanding so far is in {scored_topics[0]}."
    else:
        explanation = (
            f"Best demonstrated understanding so far covers {_join_labels(scored_topics)}. "
            f"Strongest evidence is in {_join_labels(strongest_topics)}."
        )

    grade = max(
        float(state.get("current_grade", 0.0) or 0.0),
        float(session.current_grade or 0.0),
    )
    payload = {
        "candidate_grade": grade,
        "accepted_as_current": True,
        "topic_scores": topic_scores,
        "explanation": explanation,
        "scored_topics": scored_topics,
        "missing_topics": missing_topics,
    }
    return {
        "lecture_package": lecture_package,
        "messages": messages,
        "candidate_grade": grade,
        "accepted_as_current": True,
        "payload": payload,
        "grade": grade,
        "explanation": explanation,
        "scored_topics": scored_topics,
        "missing_topics": missing_topics,
        "topic_scores": topic_scores,
    }


def _compute_authoritative_grade_snapshot(
    db: sqlalchemy_orm.Session,
    *,
    session: models.SessionModel,
    state: dict,
    lecture_package: dict | None = None,
    messages: list[dict] | None = None,
) -> dict:
    lecture_package = lecture_package or _load_lecture_package_for_session(session)
    messages = messages or _load_session_messages(db, session.session_id)
    _update_backend_grade_state(
        db,
        session=session,
        state=state,
        lecture_package=lecture_package,
    )
    return _build_grade_snapshot_from_state(
        session=session,
        state=state,
        lecture_package=lecture_package,
        messages=messages,
    )


def _generate_authoritative_report_result(
    db: sqlalchemy_orm.Session,
    *,
    session: models.SessionModel,
    state: dict,
    grade_snapshot: dict,
) -> schema.ReportResponse:
    timestamp_iso = dt.datetime.now(dt.timezone.utc).isoformat()
    settings = config_module.get_settings()
    timing = _build_session_timing_snapshot(session, settings)
    grading_result = {
        "final_grade": grade_snapshot["grade"],
        "topic_scores": grade_snapshot["topic_scores"],
        "explanation": grade_snapshot["explanation"],
        "scored_topics": grade_snapshot["scored_topics"],
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
        "scored_topics": grade_snapshot["scored_topics"],
        "missing_topics": grade_snapshot["missing_topics"],
        "report_text": report_result["report_text"],
    }
    _record_grade_event(
        db,
        session_id=session.session_id,
        event_type="report",
        grade=grade_snapshot["grade"],
        payload=report_payload,
    )

    return schema.ReportResponse(
        report_text=report_result["report_text"],
        report_json=schema.ReportJson(
            session_id=session.session_id,
            student_id=session.student_id,
            lecture_id=session.lecture_id,
            started_at=session.started_at.isoformat(),
            timestamp=timestamp_iso,
            final_grade=grade_snapshot["grade"],
            minutes_elapsed=timing["minutes_elapsed"],
            minutes_remaining=timing["minutes_remaining"],
            session_duration_minutes=timing["session_duration_minutes"],
        ),
    )


def _build_timeout_closing_message(settings: config_module.Settings, final_grade: float) -> str:
    grade_text = int(final_grade) if float(final_grade).is_integer() else round(final_grade, 1)
    return (
        f"Thanks for working through this session with me. "
        f"The {settings.session_timeout_minutes}-minute session has ended. "
        f"Your final grade for this session is {grade_text} / 100. "
        "I've included your final report below."
    )


@app.post("/get_grade", response_model=schema.GradeResponse, name="get_grade")
def get_grade(request: schema.SessionIdRequest, db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db)):
    """Compute and return the current grade using real LLM grading."""
    session = _get_active_session(db, request.session_id)
    state = session_manager.load_state(db, session.session_id)
    settings = config_module.get_settings()
    grade_snapshot = _compute_authoritative_grade_snapshot(
        db,
        session=session,
        state=state,
    )
    _record_grade_event(
        db,
        session_id=session.session_id,
        event_type="grade",
        grade=grade_snapshot["candidate_grade"],
        payload=grade_snapshot["payload"],
    )
    db.commit()
    timing = _build_session_timing_snapshot(session, settings)

    return schema.GradeResponse(
        grade=grade_snapshot["grade"],
        explanation=grade_snapshot["explanation"],
        scored_topics=grade_snapshot["scored_topics"],
        missing_topics=grade_snapshot["missing_topics"],
        minutes_elapsed=timing["minutes_elapsed"],
        minutes_remaining=timing["minutes_remaining"],
        session_duration_minutes=timing["session_duration_minutes"],
    )


@app.post("/generate_report", response_model=schema.ReportResponse, name="generate_report")
def generate_report(request: schema.SessionIdRequest, db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db)):
    """Generate a final session report using real LLM grading and report generation."""
    session = _get_active_session(db, request.session_id)
    state = session_manager.load_state(db, session.session_id)
    grade_snapshot = _compute_authoritative_grade_snapshot(
        db,
        session=session,
        state=state,
    )
    report_response = _generate_authoritative_report_result(
        db,
        session=session,
        state=state,
        grade_snapshot=grade_snapshot,
    )
    db.commit()
    return report_response


@app.post("/restart_session", response_model=schema.StartSessionResponse, name="restart_session")
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
