import datetime as dt
import json as j
import unittest.mock as mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db_module
import app.models as models
import app.session_manager as session_manager
from app.main import app

# client fixture is provided by tests/conftest.py


def start_session(client):
    response = client.post(
        "/start_session",
        json={"student_id": "student_001", "lecture_id": "lecture_01"},
    )
    assert response.status_code == 200, response.text
    return response.json()["session_id"]


def test_send_message_invalid_session(client):
    response = client.post(
        "/send_message",
        json={"session_id": "does-not-exist", "message": "Hello"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


def _mock_openai_dialogue(
    *,
    reply_text="Test reply.",
    top_classification="content_answer",
    recommended_policy="respond",
    short_reason="Student is answering lecture content.",
):
    """Patch openai.OpenAI so generate_reply returns canned responses.

    Each send_message invocation makes two OpenAI calls via the same client:
    1. classifier call (returns ClassifierResult JSON)
    2. dialogue call (returns assistant_message + updated_state JSON)
    side_effect alternates them for as many turns as needed.
    """
    import json as j

    probs = {
        "content_answer": 0.05,
        "content_question": 0.05,
        "technical_request": 0.05,
        "meta_request": 0.03,
        "off_task": 0.02,
    }
    probs[top_classification] = 0.85

    classifier_resp = mock.MagicMock()
    classifier_resp.choices[0].message.content = j.dumps({
        "top_classification": top_classification,
        "class_probabilities": probs,
        "recommended_policy": recommended_policy,
        "policy_confidence": 0.80,
        "short_reason": short_reason,
    })

    dialogue_resp = mock.MagicMock()
    dialogue_resp.choices[0].message.content = j.dumps({
        "assistant_message": reply_text,
        "updated_state": {"topics_covered": [], "mastery": {}, "evidence_notes": {}, "turn_count": 1},
    })

    mock_client = mock.MagicMock()
    # Alternate classifier / dialogue for up to 20 turns
    mock_client.chat.completions.create.side_effect = [
        classifier_resp, dialogue_resp
    ] * 20
    return mock.patch("openai.OpenAI", return_value=mock_client)


def test_turn_count_persists(client):
    session_id = start_session(client)

    with _mock_openai_dialogue():
        client.post("/send_message", json={"session_id": session_id, "message": "First"})
        client.post("/send_message", json={"session_id": session_id, "message": "Second"})

    db = next(app.dependency_overrides[db_module.get_db]())
    row = db.query(models.SessionStateModel).filter(
        models.SessionStateModel.session_id == session_id
    ).first()

    import json as j
    state = j.loads(row.state_json)
    assert state["turn_count"] == 2


def test_messages_persisted(client):
    session_id = start_session(client)

    with _mock_openai_dialogue():
        client.post("/send_message", json={"session_id": session_id, "message": "Hello"})

    db = next(app.dependency_overrides[db_module.get_db]())
    messages = (
        db.query(models.MessageModel)
        .filter(models.MessageModel.session_id == session_id)
        .filter(models.MessageModel.role.in_(["user", "assistant"]))
        .all()
    )

    roles = {m.role for m in messages}
    assert "user" in roles
    assert "assistant" in roles

    user_msg = next(m for m in messages if m.role == "user")
    assert user_msg.content == "Hello"


def test_dialogue_turn_audit_persisted(client):
    session_id = start_session(client)

    with _mock_openai_dialogue(reply_text="Test reply."):
        response = client.post("/send_message", json={"session_id": session_id, "message": "Hello"})

    assert response.status_code == 200

    db = next(app.dependency_overrides[db_module.get_db]())
    audit_rows = (
        db.query(models.DialogueTurnAuditModel)
        .filter(models.DialogueTurnAuditModel.session_id == session_id)
        .order_by(models.DialogueTurnAuditModel.turn_index.asc())
        .all()
    )

    assert len(audit_rows) == 1
    audit = audit_rows[0]
    assert audit.turn_index == 0
    assert audit.effective_policy == "respond"
    assert audit.prompt_template_name == "tutor_prompt.md"
    assert audit.dialogue_model
    assert audit.user_message == "Hello"
    assert "Recent conversation:" in audit.rendered_system_prompt
    assert audit.tutor_mode == "content_answer"
    assert audit.challenge_level >= 1
    assert audit.action_hint_json
    assert audit.ended_with_content_question is False

    state_before = j.loads(audit.state_before_json)
    assert state_before["turn_count"] == 0


def test_technical_request_re_enters_content_in_same_turn(client):
    session_id = start_session(client)

    with _mock_openai_dialogue(
        reply_text="The fastest way to improve is to hit a higher-ceiling check. What does likelihood hold fixed, and what varies?",
        top_classification="technical_request",
        recommended_policy="provide_technical_support",
        short_reason="The student is steering the session.",
    ):
        response = client.post(
            "/send_message",
            json={"session_id": session_id, "message": "Ask me the kind of question that is most likely to improve my grade."},
        )

    assert response.status_code == 200
    data = response.json()
    assert "What does likelihood hold fixed, and what varies?" in data["message"]
    assert "the next move" not in data["message"].lower()

    db = next(app.dependency_overrides[db_module.get_db]())
    audit = (
        db.query(models.DialogueTurnAuditModel)
        .filter(models.DialogueTurnAuditModel.session_id == session_id)
        .order_by(models.DialogueTurnAuditModel.turn_index.asc())
        .first()
    )
    assert audit.tutor_mode == "technical_request"
    assert audit.ended_with_content_question is True


def test_repetition_complaint_is_logged_and_prompted_as_repair(client):
    session_id = start_session(client)

    with _mock_openai_dialogue(
        reply_text="You already showed the basic point. How would you use it on a fresh case?",
        top_classification="technical_request",
        recommended_policy="provide_technical_support",
        short_reason="The student is objecting to repetition.",
    ):
        response = client.post(
            "/send_message",
            json={"session_id": session_id, "message": "You are repeating yourself. What exactly was missing from my answer?"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "same question again" not in data["message"].lower()

    db = next(app.dependency_overrides[db_module.get_db]())
    audit = (
        db.query(models.DialogueTurnAuditModel)
        .filter(models.DialogueTurnAuditModel.session_id == session_id)
        .order_by(models.DialogueTurnAuditModel.turn_index.asc())
        .first()
    )
    assert audit.repetition_complaint is True
    action_hint = j.loads(audit.action_hint_json)
    assert action_hint["recommended_action"] in {"repair", "switch"}


def test_harder_request_logs_higher_challenge_level(client):
    session_id = start_session(client)

    db = next(app.dependency_overrides[db_module.get_db]())
    state_row = db.query(models.SessionStateModel).filter(models.SessionStateModel.session_id == session_id).first()
    state = j.loads(state_row.state_json)
    state["current_topic_id"] = "T1"
    state["current_line_status"] = "productive"
    state["mastery"] = {"T1": 55}
    state["last_challenge_level"] = 3
    state_row.state_json = j.dumps(state)
    db.commit()

    with _mock_openai_dialogue(
        reply_text="Here is a harder one: how would measurement error change your interpretation of repeated measurements?",
        top_classification="technical_request",
        recommended_policy="provide_technical_support",
        short_reason="The student asked for a harder question.",
    ):
        response = client.post(
            "/send_message",
            json={"session_id": session_id, "message": "That is too easy. Ask me something harder."},
        )

    assert response.status_code == 200
    db = next(app.dependency_overrides[db_module.get_db]())
    audit = (
        db.query(models.DialogueTurnAuditModel)
        .filter(models.DialogueTurnAuditModel.session_id == session_id)
        .order_by(models.DialogueTurnAuditModel.turn_index.asc())
        .first()
    )
    assert audit.challenge_level >= 5


def test_audit_logging_migrates_old_table_schema(tmp_path):
    db_path = tmp_path / "audit.sqlite"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE dialogue_turn_audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id VARCHAR(36) NOT NULL,
                turn_index INTEGER NOT NULL,
                effective_policy VARCHAR(64) NOT NULL,
                prompt_template_name VARCHAR(128) NOT NULL,
                dialogue_model VARCHAR(128) NOT NULL,
                state_before_json TEXT NOT NULL,
                recent_messages_json TEXT NOT NULL,
                user_message TEXT NOT NULL,
                rendered_system_prompt TEXT NOT NULL,
                timestamp DATETIME NOT NULL
            )
            """
        )
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        session_manager.log_dialogue_turn_audit(
            db=db,
            session_id="session-1",
            turn_index=0,
            effective_policy="respond",
            prompt_template_name="tutor_prompt.md",
            dialogue_model="gpt-5.4-mini",
            tutor_mode="content_answer",
            action_hint_json=j.dumps({"recommended_action": "stay"}),
            challenge_level=4,
            current_topic_id="T1",
            target_topic_id="T2",
            ended_with_content_question=True,
            repetition_complaint=False,
            switched_topics=True,
            state_before_json="{}",
            recent_messages_json="[]",
            user_message="Hello",
            rendered_system_prompt="Recent conversation:",
        )
        db.commit()

        inspector = create_engine(f"sqlite:///{db_path}").connect()
        columns = {
            row[1]
            for row in inspector.exec_driver_sql("PRAGMA table_info(dialogue_turn_audits)").fetchall()
        }
        inspector.close()
    finally:
        db.close()

    assert "tutor_mode" in columns
    assert "action_hint_json" in columns
    assert "challenge_level" in columns
    assert "switched_topics" in columns


# ---------------------------------------------------------------------------
# Timeout tests
# ---------------------------------------------------------------------------

def test_session_timeout_returns_final_grade_and_closes_session(client):
    session_id = start_session(client)
    db = next(app.dependency_overrides[db_module.get_db]())
    session_row = db.query(models.SessionModel).filter(
        models.SessionModel.session_id == session_id
    ).first()
    # Set started_at to 25 minutes ago to simulate timeout
    session_row.started_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=25)
    db.commit()

    grading_result = {
        "topic_scores": [
            {"topic_id": "T1", "score": 100, "rationale": "strong"},
            {"topic_id": "T2", "score": 100, "rationale": "strong"},
        ],
        "explanation": "Strong understanding of two core topics.",
        "missing_topics": [],
    }
    with mock.patch("app.bot_engine.generate_topic_scores", return_value=grading_result):
        response = client.post("/send_message", json={"session_id": session_id, "message": "Late message"})

    assert response.status_code == 200
    data = response.json()
    assert data["session_active"] is False
    assert data["ended_reason"] == "timeout"
    assert data["final_grade"] == 80.0
    assert "Thanks for working through this session" in data["message"]


def test_session_timeout_ends_session(client):
    session_id = start_session(client)
    db = next(app.dependency_overrides[db_module.get_db]())
    session_row = db.query(models.SessionModel).filter(
        models.SessionModel.session_id == session_id
    ).first()
    session_row.started_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=25)
    db.commit()

    client.post("/send_message", json={"session_id": session_id, "message": "Late message"})

    db2 = next(app.dependency_overrides[db_module.get_db]())
    updated_row = db2.query(models.SessionModel).filter(
        models.SessionModel.session_id == session_id
    ).first()
    assert updated_row.ended_at is not None


def test_session_timeout_warning_added_in_last_five_minutes(client):
    session_id = start_session(client)
    db = next(app.dependency_overrides[db_module.get_db]())
    session_row = db.query(models.SessionModel).filter(
        models.SessionModel.session_id == session_id
    ).first()
    session_row.started_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=16)
    db.commit()

    with _mock_openai_dialogue(reply_text="Let us keep going."):
        response = client.post("/send_message", json={"session_id": session_id, "message": "Hello"})

    assert response.status_code == 200
    data = response.json()
    assert data["session_active"] is True
    assert "minutes left in this session" in data["message"]

    db2 = next(app.dependency_overrides[db_module.get_db]())
    row = db2.query(models.SessionStateModel).filter(
        models.SessionStateModel.session_id == session_id
    ).first()
    state = j.loads(row.state_json)
    assert state["timeout_warning_sent"] is True


# ---------------------------------------------------------------------------
# Fallback behavior tests
# ---------------------------------------------------------------------------

def test_send_message_fallback_on_openai_error(client):
    """When OpenAI raises inside generate_reply, fallback is used and 200 is returned."""
    session_id = start_session(client)

    # Patch the openai module used inside generate_reply so it raises on .create(...)
    mock_client = mock.MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("API unavailable")

    with mock.patch("openai.OpenAI", return_value=mock_client):
        response = client.post("/send_message", json={"session_id": session_id, "message": "Test"})

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["session_active"] is True


def test_send_message_internal_fallback_used_when_no_api_key(client):
    """When the OpenAI call raises (e.g. quota exceeded), fallback message is returned and turn_count increments."""
    session_id = start_session(client)

    mock_client = mock.MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("quota exceeded")

    with mock.patch("openai.OpenAI", return_value=mock_client):
        response = client.post("/send_message", json={"session_id": session_id, "message": "Hello"})

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["session_active"] is True

    # turn_count must have incremented regardless of fallback
    db = next(app.dependency_overrides[db_module.get_db]())
    row = db.query(models.SessionStateModel).filter(
        models.SessionStateModel.session_id == session_id
    ).first()
    state = j.loads(row.state_json)
    assert state["turn_count"] == 1
