import json
import unittest.mock as mock

import pytest

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


def test_start_session_topics_sampled_populated(client):
    session_id = start_session(client)
    db = next(app.dependency_overrides[db_module.get_db]())
    row = db.query(models.SessionStateModel).filter(
        models.SessionStateModel.session_id == session_id
    ).first()
    state = json.loads(row.state_json)
    assert isinstance(state["topics_sampled"], list)
    assert len(state["topics_sampled"]) > 0


def test_start_session_topics_sampled_stable(client):
    """Two calls with same lecture produce different sessions but each has non-empty topics_sampled."""
    session_id1 = start_session(client, student_id="s1")
    session_id2 = start_session(client, student_id="s2")
    db = next(app.dependency_overrides[db_module.get_db]())
    row1 = db.query(models.SessionStateModel).filter(
        models.SessionStateModel.session_id == session_id1
    ).first()
    row2 = db.query(models.SessionStateModel).filter(
        models.SessionStateModel.session_id == session_id2
    ).first()
    state1 = json.loads(row1.state_json)
    state2 = json.loads(row2.state_json)
    # Each session has topics sampled
    assert len(state1["topics_sampled"]) > 0
    assert len(state2["topics_sampled"]) > 0
    # Different sessions have different topic lists (virtually always for UUID-seeded random)
    # We just verify the structure is consistent
    assert set(state1["topics_sampled"]).issubset({"T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10"})
    assert set(state2["topics_sampled"]).issubset({"T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10"})


def test_start_session_topics_sampled_immutable_after_creation(client):
    """topics_sampled in state equals what was set at creation (send_message must not change it)."""
    session_id = start_session(client)
    db = next(app.dependency_overrides[db_module.get_db]())
    row = db.query(models.SessionStateModel).filter(
        models.SessionStateModel.session_id == session_id
    ).first()
    initial_state = json.loads(row.state_json)
    original_sampled = list(initial_state["topics_sampled"])

    # Send a message with OpenAI mocked — this test only cares about topics_sampled immutability
    mock_client = mock.MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("no api in tests")
    with mock.patch("openai.OpenAI", return_value=mock_client):
        client.post("/send_message", json={"session_id": session_id, "message": "Hello"})

    db2 = next(app.dependency_overrides[db_module.get_db]())
    row2 = db2.query(models.SessionStateModel).filter(
        models.SessionStateModel.session_id == session_id
    ).first()
    updated_state = json.loads(row2.state_json)
    assert updated_state["topics_sampled"] == original_sampled


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
    with _mock_topic_scores([80]):
        response = client.post("/get_grade", json={"session_id": session_id})
    assert response.status_code == 200, response.text
    data = response.json()
    assert "grade" in data
    assert "explanation" in data
    assert "missing_topics" in data


def test_get_grade_invalid_session(client):
    response = client.post("/get_grade", json={"session_id": "does-not-exist"})
    assert response.status_code == 404


def _mock_topic_scores(scores):
    """Return a mock for bot_engine.generate_topic_scores."""
    result = {
        "topic_scores": [{"topic_id": f"T{i+1}", "score": s, "rationale": "ok"} for i, s in enumerate(scores)],
        "explanation": "Mock grading.",
        "missing_topics": [],
    }
    return mock.patch("app.bot_engine.generate_topic_scores", return_value=result)


def test_get_grade_python_owns_weighting(client):
    """Weighted grade is computed in Python, not returned by the model."""
    session_id = start_session(client)
    # 2 topics scored at 100 each → 55+25 = 80
    with _mock_topic_scores([100, 100]):
        response = client.post("/get_grade", json={"session_id": session_id})
    assert response.status_code == 200
    assert response.json()["grade"] == 80.0


def test_get_grade_zero_padding_fewer_than_5(client):
    """Fewer than 5 topics scored: remaining slots padded with zero."""
    session_id = start_session(client)
    with _mock_topic_scores([100]):
        response = client.post("/get_grade", json={"session_id": session_id})
    assert response.status_code == 200
    assert response.json()["grade"] == 55.0


def test_get_grade_monotone_nondecreasing(client):
    """current_grade only increases, never decreases."""
    session_id = start_session(client)
    # First call: score 80
    with _mock_topic_scores([100, 100]):
        r1 = client.post("/get_grade", json={"session_id": session_id})
    assert r1.json()["grade"] == 80.0

    # Second call with lower scores
    with _mock_topic_scores([50]):
        r2 = client.post("/get_grade", json={"session_id": session_id})
    # Authoritative grade stays at 80
    assert r2.json()["grade"] == 80.0


def test_get_grade_updates_on_improvement(client):
    """current_grade updates when candidate is higher."""
    session_id = start_session(client)
    with _mock_topic_scores([50]):
        r1 = client.post("/get_grade", json={"session_id": session_id})
    assert r1.json()["grade"] == pytest.approx(27.0)  # 55*50/100=27.5 → floor=27

    with _mock_topic_scores([100]):
        r2 = client.post("/get_grade", json={"session_id": session_id})
    assert r2.json()["grade"] == 55.0


def test_get_grade_inserts_grade_event(client):
    """A grade event row is inserted on each grading call."""
    session_id = start_session(client)
    with _mock_topic_scores([80]):
        client.post("/get_grade", json={"session_id": session_id})

    db = next(app.dependency_overrides[db_module.get_db]())
    events = db.query(models.GradeEventModel).filter(
        models.GradeEventModel.session_id == session_id,
        models.GradeEventModel.event_type == "grade",
    ).all()
    assert len(events) >= 1


def test_get_grade_accepted_payload_authoritative_after_lower_candidate(client):
    """After a lower grade attempt, the explanation from the first (higher) accepted payload is returned."""
    session_id = start_session(client)

    high_scores = {
        "topic_scores": [{"topic_id": "T1", "score": 100, "rationale": "strong"}],
        "explanation": "High performance on T1.",
        "missing_topics": [],
    }
    low_scores = {
        "topic_scores": [],
        "explanation": "Nothing demonstrated.",
        "missing_topics": ["T1"],
    }

    with mock.patch("app.bot_engine.generate_topic_scores", return_value=high_scores):
        client.post("/get_grade", json={"session_id": session_id})

    with mock.patch("app.bot_engine.generate_topic_scores", return_value=low_scores):
        r2 = client.post("/get_grade", json={"session_id": session_id})

    data = r2.json()
    assert data["grade"] == 55.0
    assert "High performance" in data["explanation"]


# ---------------------------------------------------------------------------
# /generate_report
# ---------------------------------------------------------------------------

def _mock_openai_report(report_text="Generated report."):
    """Patch openai.OpenAI so generate_report returns a canned response without a real API call."""
    mock_resp = mock.MagicMock()
    mock_resp.choices[0].message.content = json.dumps({"report_text": report_text})
    mock_client = mock.MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp
    return mock.patch("openai.OpenAI", return_value=mock_client)


def test_generate_report_returns_report_structure(client):
    session_id = start_session(client)
    with _mock_openai_report():
        response = client.post("/generate_report", json={"session_id": session_id})
    assert response.status_code == 200, response.text
    data = response.json()
    assert "report_text" in data
    assert "report_json" in data


def test_generate_report_invalid_session(client):
    response = client.post("/generate_report", json={"session_id": "does-not-exist"})
    assert response.status_code == 404


def _mock_scores_for_report(topic_scores_list, explanation="Good work.", missing=None):
    result = {
        "topic_scores": [{"topic_id": f"T{i+1}", "score": s, "rationale": "ok"} for i, s in enumerate(topic_scores_list)],
        "explanation": explanation,
        "missing_topics": missing or [],
    }
    return mock.patch("app.bot_engine.generate_topic_scores", return_value=result)


def test_generate_report_uses_authoritative_grade(client):
    """report_json.final_grade equals session.current_grade."""
    session_id = start_session(client)
    with _mock_scores_for_report([100, 100]), _mock_openai_report():
        response = client.post("/generate_report", json={"session_id": session_id})
    assert response.status_code == 200
    data = response.json()
    assert data["report_json"]["final_grade"] == 80.0


def test_generate_report_grade_monotone_nondecreasing(client):
    """After a lower candidate, report still reflects accepted best grade."""
    session_id = start_session(client)
    with _mock_topic_scores([100, 100]):
        client.post("/get_grade", json={"session_id": session_id})

    with _mock_scores_for_report([0]), _mock_openai_report():
        response = client.post("/generate_report", json={"session_id": session_id})

    data = response.json()
    assert data["report_json"]["final_grade"] == 80.0


def test_generate_report_uses_prior_explanation_when_lower_candidate(client):
    """When candidate is lower, report explanation comes from prior accepted payload."""
    session_id = start_session(client)

    first_grading = {
        "topic_scores": [{"topic_id": "T1", "score": 100, "rationale": "strong"}],
        "explanation": "Excellent understanding of T1.",
        "missing_topics": [],
    }
    with mock.patch("app.bot_engine.generate_topic_scores", return_value=first_grading):
        client.post("/get_grade", json={"session_id": session_id})

    low_grading = {
        "topic_scores": [],
        "explanation": "Nothing demonstrated.",
        "missing_topics": ["T1"],
    }
    with mock.patch("app.bot_engine.generate_topic_scores", return_value=low_grading):
        # Also need to prevent report generator from calling real OpenAI
        with mock.patch("app.bot_engine.generate_report") as mock_gen_report:
            mock_gen_report.return_value = {
                "report_text": "Report based on T1 understanding.",
                "report_json": {},
            }
            response = client.post("/generate_report", json={"session_id": session_id})

    # The call to generate_report should have received the authoritative explanation
    call_kwargs = mock_gen_report.call_args.kwargs
    assert "Excellent understanding" in call_kwargs["grading_result"]["explanation"]


def test_generate_report_inserts_report_event(client):
    """A grade event with event_type='report' is inserted."""
    session_id = start_session(client)
    mock_client = mock.MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("no api in tests")
    with _mock_scores_for_report([80]), mock.patch("openai.OpenAI", return_value=mock_client):
        client.post("/generate_report", json={"session_id": session_id})

    db = next(app.dependency_overrides[db_module.get_db]())
    events = db.query(models.GradeEventModel).filter(
        models.GradeEventModel.session_id == session_id,
        models.GradeEventModel.event_type == "report",
    ).all()
    assert len(events) >= 1


def test_get_grade_uses_report_event_payload_when_authoritative(client):
    """If the highest accepted payload came from a report event, get_grade still uses it.

    This validates the shared _get_authoritative_grading_payload helper searches
    both 'grade' and 'report' event types.
    """
    session_id = start_session(client)

    # First accepted payload comes from a /generate_report call (no prior /get_grade)
    high_grading = {
        "topic_scores": [{"topic_id": "T1", "score": 100, "rationale": "strong"}],
        "explanation": "Authoritative payload from report event.",
        "missing_topics": [],
    }
    with mock.patch("app.bot_engine.generate_topic_scores", return_value=high_grading), \
         _mock_openai_report():
        client.post("/generate_report", json={"session_id": session_id})

    # Now get_grade with a lower candidate score
    low_grading = {
        "topic_scores": [],
        "explanation": "Nothing demonstrated.",
        "missing_topics": ["T1"],
    }
    with mock.patch("app.bot_engine.generate_topic_scores", return_value=low_grading):
        r = client.post("/get_grade", json={"session_id": session_id})

    data = r.json()
    assert data["grade"] == 55.0
    assert "Authoritative payload from report event" in data["explanation"]
