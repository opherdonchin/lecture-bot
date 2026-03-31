import json

import app.db as db_module
import app.models as models
from app.main import app


def start_session(client, student_id="student_001", lecture_id="lecture_01"):
    response = client.post(
        "/start_session",
        json={"student_id": student_id, "lecture_id": lecture_id},
    )
    assert response.status_code == 200, response.text
    return response.json()["session_id"]


# ---------------------------------------------------------------------------
# Transaction consistency: start_session persists session + opening message
# ---------------------------------------------------------------------------

def test_start_session_persists_session_row(client):
    session_id = start_session(client)
    db = next(app.dependency_overrides[db_module.get_db]())
    row = db.query(models.SessionModel).filter(
        models.SessionModel.session_id == session_id
    ).first()
    assert row is not None
    assert row.student_id == "student_001"


def test_start_session_persists_opening_message(client):
    session_id = start_session(client)
    db = next(app.dependency_overrides[db_module.get_db]())
    messages = (
        db.query(models.MessageModel)
        .filter(models.MessageModel.session_id == session_id)
        .all()
    )
    assert any(m.role == "assistant" for m in messages)


def test_start_session_persists_state(client):
    session_id = start_session(client)
    db = next(app.dependency_overrides[db_module.get_db]())
    row = db.query(models.SessionStateModel).filter(
        models.SessionStateModel.session_id == session_id
    ).first()
    assert row is not None
    state = json.loads(row.state_json)
    assert state["turn_count"] == 0


# ---------------------------------------------------------------------------
# /restart_session
# ---------------------------------------------------------------------------

def test_restart_session_returns_new_session_id(client):
    old_id = start_session(client)
    response = client.post(
        "/restart_session",
        json={"session_id": old_id, "student_id": "student_001", "lecture_id": "lecture_01"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["session_id"] != old_id


def test_restart_session_ends_old_session(client):
    old_id = start_session(client)
    client.post(
        "/restart_session",
        json={"session_id": old_id, "student_id": "student_001", "lecture_id": "lecture_01"},
    )
    db = next(app.dependency_overrides[db_module.get_db]())
    old_row = db.query(models.SessionModel).filter(
        models.SessionModel.session_id == old_id
    ).first()
    assert old_row.ended_at is not None


def test_restart_session_invalid_old_session(client):
    response = client.post(
        "/restart_session",
        json={"session_id": "does-not-exist", "student_id": "student_001", "lecture_id": "lecture_01"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# /get_grade
# ---------------------------------------------------------------------------

def test_get_grade_returns_grade_structure(client):
    session_id = start_session(client)
    response = client.post("/get_grade", json={"session_id": session_id})
    assert response.status_code == 200, response.text
    data = response.json()
    assert "grade" in data
    assert "explanation" in data
    assert "missing_topics" in data


def test_get_grade_invalid_session(client):
    response = client.post("/get_grade", json={"session_id": "does-not-exist"})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# /generate_report
# ---------------------------------------------------------------------------

def test_generate_report_returns_report_structure(client):
    session_id = start_session(client)
    response = client.post("/generate_report", json={"session_id": session_id})
    assert response.status_code == 200, response.text
    data = response.json()
    assert "report_text" in data
    assert "report_json" in data


def test_generate_report_invalid_session(client):
    response = client.post("/generate_report", json={"session_id": "does-not-exist"})
    assert response.status_code == 404
