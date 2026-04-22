import datetime as dt
import json as j
import unittest.mock as mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db_module
import app.bot_engine as bot_engine
import app.models as models
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


def _mock_openai_dialogue(reply_text="Test reply."):
    """Patch openai.OpenAI so generate_reply returns a canned JSON response."""
    import json as j
    mock_resp = mock.MagicMock()
    mock_resp.choices[0].message.content = j.dumps({
        "assistant_message": reply_text,
        "updated_state": {
            "topics_covered": [],
            "mastery": {},
            "evidence_notes": {},
            "current_topic_id": None,
            "tutor_comment": "",
        },
        "decision_trace": {
            "step_1_current_topic_option": {
                "topic_id": "T1",
                "why_consider": "",
            },
            "step_2_alternative_topic_option": {
                "topic_id": "T2",
                "why_consider": "",
            },
            "step_3_current_topic_value": {
                "topic_id": "T1",
                "grade_value": 3,
                "pedagogical_value": 3,
                "engagement_value": 3,
                "reason": "",
            },
            "step_4_alternative_topic_value": {
                "topic_id": "T2",
                "grade_value": 3,
                "pedagogical_value": 3,
                "engagement_value": 3,
                "reason": "",
            },
            "step_5_weighted_topic_comparison": {
                "grade_weight": 3,
                "pedagogical_weight": 4,
                "engagement_weight": 3,
                "current_topic_total": 27,
                "alternative_topic_total": 24,
                "preferred_topic_id": "T1",
                "reason": "",
            },
            "step_6_chosen_topic": {
                "topic_id": "T1",
                "choice_type": "stay",
                "reason": "",
            },
            "step_7_student_model": {
                "understanding": "",
                "uncertainty": "",
                "failure_mode": "",
            },
            "step_8_evidence_target": {
                "topic_id": "T1",
                "element": "",
                "target_type": "criterion",
                "why_now": "",
            },
            "step_9_move_candidates": [],
            "step_10_choice": {
                "chosen_move": "open_probe",
                "reason": "",
            },
            "step_11_reply_draft": {"draft": ""},
            "step_12_reply_check": {
                "most_productive": True,
                "minimally_revealing": True,
                "smuggles_answer": False,
                "asks_one_contribution": True,
            },
            "step_13_revision": {"revised": False, "reason": ""},
            "step_14_final_move": {"move_type": "open_probe", "reason": ""},
        },
    })
    mock_client = mock.MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp
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


def test_send_message_banks_best_mastery_from_tutor_state(client):
    session_id = start_session(client)

    mock_resp = mock.MagicMock()
    mock_resp.choices[0].message.content = j.dumps({
        "assistant_message": "Good. What is the key distinction?",
        "updated_state": {
            "topics_covered": ["T1"],
            "mastery": {"T1": 70},
            "evidence_notes": {"T1": "student gave a real distinction"},
            "current_topic_id": "T1",
            "tutor_comment": "bank T1 and verify once more",
        },
        "decision_trace": {
            "step_1_current_topic_option": {
                "topic_id": "T1",
                "why_consider": "already active",
            },
            "step_2_alternative_topic_option": {
                "topic_id": "T2",
                "why_consider": "possible breadth move",
            },
            "step_3_current_topic_value": {
                "topic_id": "T1",
                "grade_value": 4,
                "pedagogical_value": 4,
                "engagement_value": 3,
                "reason": "",
            },
            "step_4_alternative_topic_value": {
                "topic_id": "T2",
                "grade_value": 3,
                "pedagogical_value": 3,
                "engagement_value": 3,
                "reason": "",
            },
            "step_5_weighted_topic_comparison": {
                "grade_weight": 3,
                "pedagogical_weight": 4,
                "engagement_weight": 3,
                "current_topic_total": 37,
                "alternative_topic_total": 27,
                "preferred_topic_id": "T1",
                "reason": "",
            },
            "step_6_chosen_topic": {
                "topic_id": "T1",
                "choice_type": "stay",
                "reason": "",
            },
            "step_7_student_model": {
                "understanding": "partial distinction",
                "uncertainty": "still soft",
                "failure_mode": "too verbal",
            },
            "step_8_evidence_target": {
                "topic_id": "T1",
                "element": "key distinction",
                "target_type": "distinction",
                "why_now": "one stronger check",
            },
            "step_9_move_candidates": [],
            "step_10_choice": {
                "chosen_move": "narrowing_question",
                "reason": "best next check",
            },
            "step_11_reply_draft": {"draft": "Good. What is the key distinction?"},
            "step_12_reply_check": {
                "most_productive": True,
                "minimally_revealing": True,
                "smuggles_answer": False,
                "asks_one_contribution": True,
            },
            "step_13_revision": {"revised": False, "reason": ""},
            "step_14_final_move": {"move_type": "narrowing_question", "reason": "best next check"},
        },
    })
    mock_client = mock.MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp

    with mock.patch("openai.OpenAI", return_value=mock_client):
        response = client.post("/send_message", json={"session_id": session_id, "message": "Hello"})

    assert response.status_code == 200
    db = next(app.dependency_overrides[db_module.get_db]())
    row = db.query(models.SessionStateModel).filter(
        models.SessionStateModel.session_id == session_id
    ).first()
    state = j.loads(row.state_json)
    assert state["mastery"]["T1"] == 70
    assert state["best_mastery"]["T1"] == 70
    assert state["current_grade"] == 38.0
    assert state["private_decision_trace"]["step_6_chosen_topic"]["topic_id"] == "T1"
    assert state["private_decision_trace"]["step_8_evidence_target"]["topic_id"] == "T1"


# ---------------------------------------------------------------------------
# Timeout tests
# ---------------------------------------------------------------------------

def _mock_openai_report(report_text="Generated report."):
    mock_resp = mock.MagicMock()
    mock_resp.choices[0].message.content = j.dumps({"report_text": report_text})
    mock_client = mock.MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp
    return mock.patch("openai.OpenAI", return_value=mock_client)


def _set_mastery_state(session_id, *, best_scores=None, current_scores=None):
    db = next(app.dependency_overrides[db_module.get_db]())
    session = db.query(models.SessionModel).filter(
        models.SessionModel.session_id == session_id
    ).first()
    row = db.query(models.SessionStateModel).filter(
        models.SessionStateModel.session_id == session_id
    ).first()
    state = j.loads(row.state_json)

    best_scores = best_scores or []
    current_scores = current_scores if current_scores is not None else best_scores

    state["best_mastery"] = {
        f"T{i+1}": score
        for i, score in enumerate(best_scores)
    }
    state["mastery"] = {
        f"T{i+1}": score
        for i, score in enumerate(current_scores)
    }
    state["topics_covered"] = [f"T{i+1}" for i, score in enumerate(current_scores) if score > 0]
    state["current_grade"] = float(bot_engine.compute_weighted_grade([
        {"topic_id": f"T{i+1}", "score": score}
        for i, score in enumerate(best_scores)
        if score > 0
    ]))
    row.state_json = j.dumps(state)
    session.current_grade = state["current_grade"]
    db.commit()


def test_session_timeout_returns_final_report_and_closes_session(client):
    session_id = start_session(client)
    db = next(app.dependency_overrides[db_module.get_db]())
    session_row = db.query(models.SessionModel).filter(
        models.SessionModel.session_id == session_id
    ).first()
    # Set started_at to 25 minutes ago to simulate timeout
    session_row.started_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=25)
    db.commit()

    _set_mastery_state(session_id, best_scores=[100, 100])
    with _mock_openai_report():
        response = client.post("/send_message", json={"session_id": session_id, "message": "Late message"})

    assert response.status_code == 200
    data = response.json()
    assert data["session_active"] is False
    assert data["ended_reason"] == "timeout"
    assert data["final_grade"] == 80.0
    assert "session has ended" in data["message"].lower()
    assert data["final_report"]["report_json"]["final_grade"] == 80.0
    assert data["final_report"]["report_json"]["minutes_remaining"] == 0
    assert data["final_report"]["report_json"]["session_duration_minutes"] == 20


def test_session_timeout_ends_session(client):
    session_id = start_session(client)
    db = next(app.dependency_overrides[db_module.get_db]())
    session_row = db.query(models.SessionModel).filter(
        models.SessionModel.session_id == session_id
    ).first()
    session_row.started_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=25)
    db.commit()
    _set_mastery_state(session_id, best_scores=[80])

    with _mock_openai_report():
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

    with _mock_openai_dialogue(reply_text="Let's finish one last idea."):
        response = client.post("/send_message", json={"session_id": session_id, "message": "Hello"})

    assert response.status_code == 200
    data = response.json()
    assert data["session_active"] is True
    assert data["message"] == "Let's finish one last idea."

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


def test_send_message_rejects_non_english_student_message_without_model_call(client):
    session_id = start_session(client)

    with mock.patch("openai.OpenAI", side_effect=AssertionError("model should not be called")):
        response = client.post(
            "/send_message",
            json={"session_id": session_id, "message": "למה לדגום"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "Please write your answer in English." in data["message"]
    assert data["session_active"] is True


def test_send_message_forces_assistant_reply_to_english(client):
    session_id = start_session(client)

    mock_resp = mock.MagicMock()
    mock_resp.choices[0].message.content = j.dumps({
        "assistant_message": "שלום, אפשר להמשיך בעברית.",
        "updated_state": {
            "topics_covered": [],
            "mastery": {},
            "evidence_notes": {},
            "current_topic_id": None,
            "tutor_comment": "",
        },
        "decision_trace": {
            "student_model": {
                "understanding": "",
                "uncertainty": "",
                "failure_mode": "",
            },
            "evidence_target": {
                "topic_id": "T1",
                "element": "",
                "target_type": "criterion",
                "why_now": "",
            },
            "move_candidates": [],
            "chosen_move": {
                "move_type": "open_probe",
                "reason": "",
            },
        },
    })
    mock_client = mock.MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp

    with mock.patch("openai.OpenAI", return_value=mock_client):
        response = client.post("/send_message", json={"session_id": session_id, "message": "Hello"})

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Please continue in English. This tutor only works in English."


def test_send_message_writes_dialogue_turn_audit_row(client):
    session_id = start_session(client)

    with _mock_openai_dialogue("What is one example?"):
        response = client.post(
            "/send_message",
            json={"session_id": session_id, "message": "What counts as data"},
        )

    assert response.status_code == 200
    db = next(app.dependency_overrides[db_module.get_db]())
    audit_row = (
        db.query(models.DialogueTurnAuditModel)
        .filter(models.DialogueTurnAuditModel.session_id == session_id)
        .one()
    )
    assert audit_row.turn_index == 1
    assert audit_row.prompt_template_name == "tutor_prompt.md"
    assert audit_row.dialogue_model
    assert "You are the runtime tutor for a lecture-review dialogue" in audit_row.rendered_system_prompt
    assert audit_row.user_message == "What counts as data"
