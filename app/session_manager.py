import json as j
import uuid as uuid_module

import sqlalchemy.orm as sqlalchemy_orm

import app.bot_engine as bot_engine
import app.config as config_module
import app.models as models


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
        "assisted_turn_streak": 0,
        "recent_explanation_attempts": 0,
        "recent_parroting_streak": 0,
        "recent_unelaborated_agreement_streak": 0,
        "current_line_status": "unclear",
        "student_goal_now": "pick a starting topic and begin explaining in their own words",
        "interaction_state": "opening",
        "current_line": "no content line established yet",
        "what_student_has_shown": "",
        "what_remains_uncertain": "which sampled topic the student wants to start with",
        "why_continue_or_switch": "start with a clear topic choice before probing deeply",
        "do_not_repeat": [],
        "best_next_move": "offer or confirm a starting topic choice",
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
