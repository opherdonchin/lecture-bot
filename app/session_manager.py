import json as j
import uuid as uuid_module

import sqlalchemy as sa
import sqlalchemy.orm as sqlalchemy_orm

import app.bot_engine as bot_engine
import app.config as config_module
import app.models as models

_DIALOGUE_AUDIT_TABLE_READY = False


def build_initial_state(lecture_package: dict, topics_sampled: list) -> dict:
    return {
        # tutoring state
        "topics_sampled": topics_sampled,
        "topics_covered": [],
        "mastery": {},
        "evidence_notes": {},
        "turn_count": 0,
        "lecture_title": lecture_package["config"].get("title", lecture_package["lecture_id"]),
        "timeout_warning_sent": False,
        "current_topic_id": None,
        "current_line_status": "unclear",
        "last_challenge_level": 1,
        "must_not_repeat": [],
        "lecture_native_only": True,
        "last_action": None,
        "last_target_topic_id": None,
        "last_reason_code": None,
        "last_repetition_complaint": False,
        "last_assistant_had_content_question": False,
        # routing state
        "last_top_classification": None,
        "last_recommended_policy": None,
        "last_effective_policy": None,
        "consecutive_redirects": 0,
        "consecutive_meta_requests": 0,
        "consecutive_clarifications": 0,
        "last_policy_override_reason": None,
    }


def create_session(db: sqlalchemy_orm.Session, student_id: str, lecture_id: str, lecture_package: dict) -> models.SessionModel:
    session = models.SessionModel(
        session_id=str(uuid_module.uuid4()),
        student_id=student_id,
        lecture_id=lecture_id,
        current_grade=0.0,
    )
    db.add(session)
    db.flush()

    # Parse rubric topics and sample deterministically using session_id
    topic_defs = bot_engine.parse_rubric_topics(lecture_package["rubric"])
    count = config_module.get_settings().sampled_topic_count
    topics_sampled = bot_engine.sample_session_topics(topic_defs, session.session_id, count=count)

    state = models.SessionStateModel(
        session_id=session.session_id,
        state_json=j.dumps(build_initial_state(lecture_package, topics_sampled), ensure_ascii=False),
    )
    db.add(state)
    db.flush()
    return session


def append_message(db: sqlalchemy_orm.Session, session_id: str, role: str, content: str) -> None:
    db.add(models.MessageModel(session_id=session_id, role=role, content=content))


def load_state(db: sqlalchemy_orm.Session, session_id: str) -> dict:
    row = db.query(models.SessionStateModel).filter(models.SessionStateModel.session_id == session_id).first()
    if not row:
        raise ValueError(f"No state found for session {session_id}")
    return j.loads(row.state_json)


def save_state(db: sqlalchemy_orm.Session, session_id: str, state: dict) -> None:
    row = db.query(models.SessionStateModel).filter(models.SessionStateModel.session_id == session_id).first()
    if not row:
        raise ValueError(f"No state found for session {session_id}")
    row.state_json = j.dumps(state, ensure_ascii=False)


def log_classification(
    db: sqlalchemy_orm.Session,
    session_id: str,
    turn_index: int,
    classifier_json: str,
    policy_decision_json: str,
) -> None:
    db.add(models.ClassificationLogModel(
        session_id=session_id,
        turn_index=turn_index,
        classifier_json=classifier_json,
        policy_decision_json=policy_decision_json,
    ))


def _ensure_dialogue_audit_table(db: sqlalchemy_orm.Session) -> None:
    global _DIALOGUE_AUDIT_TABLE_READY
    bind = db.get_bind()
    models.DialogueTurnAuditModel.__table__.create(bind=bind, checkfirst=True)
    inspector = sa.inspect(bind)
    existing = {col["name"] for col in inspector.get_columns(models.DialogueTurnAuditModel.__tablename__)}
    required_columns = {
        "tutor_mode": "VARCHAR(64) DEFAULT 'content_answer'",
        "action_hint_json": "TEXT DEFAULT '{}'",
        "challenge_level": "INTEGER DEFAULT 1",
        "current_topic_id": "VARCHAR(64)",
        "target_topic_id": "VARCHAR(64)",
        "ended_with_content_question": "BOOLEAN DEFAULT 0",
        "repetition_complaint": "BOOLEAN DEFAULT 0",
        "switched_topics": "BOOLEAN DEFAULT 0",
    }
    for column_name, column_sql in required_columns.items():
        if column_name in existing:
            continue
        with bind.begin() as conn:
            conn.execute(sa.text(
                f"ALTER TABLE {models.DialogueTurnAuditModel.__tablename__} "
                f"ADD COLUMN {column_name} {column_sql}"
            ))
    _DIALOGUE_AUDIT_TABLE_READY = True


def log_dialogue_turn_audit(
    db: sqlalchemy_orm.Session,
    session_id: str,
    turn_index: int,
    effective_policy: str,
    prompt_template_name: str,
    dialogue_model: str,
    tutor_mode: str,
    action_hint_json: str,
    challenge_level: int,
    current_topic_id: str | None,
    target_topic_id: str | None,
    ended_with_content_question: bool,
    repetition_complaint: bool,
    switched_topics: bool,
    state_before_json: str,
    recent_messages_json: str,
    user_message: str,
    rendered_system_prompt: str,
) -> None:
    _ensure_dialogue_audit_table(db)
    db.add(models.DialogueTurnAuditModel(
        session_id=session_id,
        turn_index=turn_index,
        effective_policy=effective_policy,
        prompt_template_name=prompt_template_name,
        dialogue_model=dialogue_model,
        tutor_mode=tutor_mode,
        action_hint_json=action_hint_json,
        challenge_level=challenge_level,
        current_topic_id=current_topic_id,
        target_topic_id=target_topic_id,
        ended_with_content_question=ended_with_content_question,
        repetition_complaint=repetition_complaint,
        switched_topics=switched_topics,
        state_before_json=state_before_json,
        recent_messages_json=recent_messages_json,
        user_message=user_message,
        rendered_system_prompt=rendered_system_prompt,
    ))
