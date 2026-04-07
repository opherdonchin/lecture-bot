import json as j
import uuid as uuid_module

import sqlalchemy.orm as sqlalchemy_orm

import app.bot_engine as bot_engine
import app.models as models


def build_initial_state(lecture_package: dict, topics_sampled: list) -> dict:
    return {
        "topics_sampled": topics_sampled,
        "topics_covered": [],
        "mastery": {},
        "turn_count": 0,
        "confidence": 0.0,
        "lecture_title": lecture_package["config"].get("title", lecture_package["lecture_id"]),
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
    topics_sampled = bot_engine.sample_session_topics(topic_defs, session.session_id)

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