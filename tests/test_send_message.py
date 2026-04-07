import datetime as dt
import json as j
import unittest.mock as mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db_module
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


def test_turn_count_persists(client):
    session_id = start_session(client)

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


# ---------------------------------------------------------------------------
# Timeout tests
# ---------------------------------------------------------------------------

def test_session_timeout_returns_400(client):
    session_id = start_session(client)
    db = next(app.dependency_overrides[db_module.get_db]())
    session_row = db.query(models.SessionModel).filter(
        models.SessionModel.session_id == session_id
    ).first()
    # Set started_at to 25 minutes ago to simulate timeout
    session_row.started_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=25)
    db.commit()

    response = client.post("/send_message", json={"session_id": session_id, "message": "Late message"})
    assert response.status_code == 400
    assert "timed out" in response.json()["detail"].lower()


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
    """Without an API key the fallback message is returned and turn_count still increments."""
    import app.config as config_module
    session_id = start_session(client)

    response = client.post("/send_message", json={"session_id": session_id, "message": "Hello"})
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["session_active"] is True

    # turn_count must have incremented regardless of whether fallback or real reply was used
    db = next(app.dependency_overrides[db_module.get_db]())
    row = db.query(models.SessionStateModel).filter(
        models.SessionStateModel.session_id == session_id
    ).first()
    state = j.loads(row.state_json)
    assert state["turn_count"] == 1
