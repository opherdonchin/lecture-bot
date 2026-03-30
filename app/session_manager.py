import json
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import MessageModel, SessionModel, SessionStateModel


def build_initial_state(lecture_package: dict) -> dict:
    return {
        "topics_sampled": [],
        "topics_covered": [],
        "mastery": {},
        "turn_count": 0,
        "confidence": 0.0,
        "lecture_title": lecture_package["config"].get("title", lecture_package["lecture_id"]),
    }


def create_session(db: Session, student_id: str, lecture_id: str, lecture_package: dict) -> SessionModel:
    session = SessionModel(
        session_id=str(uuid4()),
        student_id=student_id,
        lecture_id=lecture_id,
        current_grade=0.0,
    )
    db.add(session)
    db.flush()

    state = SessionStateModel(
        session_id=session.session_id,
        state_json=json.dumps(build_initial_state(lecture_package), ensure_ascii=False),
    )
    db.add(state)
    db.commit()
    db.refresh(session)
    return session


def append_message(db: Session, session_id: str, role: str, content: str) -> None:
    db.add(MessageModel(session_id=session_id, role=role, content=content))
    db.commit()