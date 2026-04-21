import datetime as dt
import json
import unittest.mock as mock

import app.bot_engine as bot_engine
import app.config as config_module
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


def test_start_session_uses_sampled_topics_for_opening_message(client):
    with mock.patch("app.bot_engine.build_opening_message", return_value="Opening.") as mock_opening:
        response = client.post(
            "/start_session",
            json={"student_id": "student_001", "lecture_id": "lecture_01"},
        )
    assert response.status_code == 200, response.text
    session_id = response.json()["session_id"]
    db = next(app.dependency_overrides[db_module.get_db]())
    row = db.query(models.SessionStateModel).filter(
        models.SessionStateModel.session_id == session_id
    ).first()
    state = json.loads(row.state_json)
    assert mock_opening.call_args.kwargs["sampled_topic_ids"] == state["topics_sampled"]


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
    _set_mastery_state(session_id, best_scores=[80])
    response = client.post("/get_grade", json={"session_id": session_id})
    assert response.status_code == 200, response.text
    data = response.json()
    assert "grade" in data
    assert "explanation" in data
    assert "scored_topics" in data
    assert "missing_topics" in data
    assert "minutes_elapsed" in data
    assert "minutes_remaining" in data
    assert "session_duration_minutes" in data


def test_get_grade_invalid_session(client):
    response = client.post("/get_grade", json={"session_id": "does-not-exist"})
    assert response.status_code == 404


def _set_mastery_state(session_id, *, best_scores=None, current_scores=None):
    db = next(app.dependency_overrides[db_module.get_db]())
    session = db.query(models.SessionModel).filter(
        models.SessionModel.session_id == session_id
    ).first()
    row = db.query(models.SessionStateModel).filter(
        models.SessionStateModel.session_id == session_id
    ).first()
    state = json.loads(row.state_json)

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
    row.state_json = json.dumps(state)
    session.current_grade = state["current_grade"]
    db.commit()


def test_get_grade_python_owns_weighting(client):
    """Weighted grade is computed in Python, not returned by the model."""
    session_id = start_session(client)
    _set_mastery_state(session_id, best_scores=[100, 100])
    response = client.post("/get_grade", json={"session_id": session_id})
    assert response.status_code == 200
    assert response.json()["grade"] == 80.0


def test_get_grade_zero_padding_fewer_than_5(client):
    """Fewer than 5 topics scored: remaining slots padded with zero."""
    session_id = start_session(client)
    _set_mastery_state(session_id, best_scores=[100])
    response = client.post("/get_grade", json={"session_id": session_id})
    assert response.status_code == 200
    assert response.json()["grade"] == 55.0


def test_get_grade_returns_labelled_scored_topics(client):
    session_id = start_session(client)
    _set_mastery_state(session_id, best_scores=[100, 100])
    response = client.post("/get_grade", json={"session_id": session_id})
    assert response.status_code == 200
    assert response.json()["scored_topics"] == [
        "Topic 1",
        "Topic 2",
    ]


def test_get_grade_deduplicates_repeated_topic_defs(client):
    lectures_dir = config_module.get_settings().lectures_dir
    config_path = lectures_dir / "lecture_01" / "lecture_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["topics"] = config["topics"] + config["topics"]
    config_path.write_text(json.dumps(config), encoding="utf-8")

    session_id = start_session(client)
    _set_mastery_state(session_id, best_scores=[100, 100])
    response = client.post("/get_grade", json={"session_id": session_id})

    assert response.status_code == 200
    assert response.json()["scored_topics"] == ["Topic 1", "Topic 2"]
    assert response.json()["missing_topics"] == [f"Topic {i}" for i in range(3, 11)]


def test_get_grade_uses_best_mastery_when_current_mastery_is_lower(client):
    session_id = start_session(client)
    _set_mastery_state(session_id, best_scores=[100, 100], current_scores=[20])
    response = client.post("/get_grade", json={"session_id": session_id})
    assert response.status_code == 200
    assert response.json()["grade"] == 80.0


def test_get_grade_banks_higher_current_mastery(client):
    session_id = start_session(client)
    _set_mastery_state(session_id, best_scores=[50], current_scores=[100])
    response = client.post("/get_grade", json={"session_id": session_id})
    assert response.status_code == 200
    assert response.json()["grade"] == 55.0


def test_get_grade_inserts_grade_event(client):
    """A grade event row is inserted on each grading call."""
    session_id = start_session(client)
    _set_mastery_state(session_id, best_scores=[80])
    client.post("/get_grade", json={"session_id": session_id})

    db = next(app.dependency_overrides[db_module.get_db]())
    events = db.query(models.GradeEventModel).filter(
        models.GradeEventModel.session_id == session_id,
        models.GradeEventModel.event_type == "grade",
    ).all()
    assert len(events) >= 1


def test_get_grade_does_not_call_generate_topic_scores(client):
    session_id = start_session(client)
    _set_mastery_state(session_id, best_scores=[100])
    with mock.patch("app.bot_engine.generate_topic_scores", side_effect=AssertionError("should not be called")):
        response = client.post("/get_grade", json={"session_id": session_id})
    assert response.status_code == 200
    assert response.json()["grade"] == 55.0


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
    _set_mastery_state(session_id, best_scores=[80])
    with _mock_openai_report():
        response = client.post("/generate_report", json={"session_id": session_id})
    assert response.status_code == 200, response.text
    data = response.json()
    assert "report_text" in data
    assert "report_json" in data
    assert "minutes_elapsed" in data["report_json"]
    assert "minutes_remaining" in data["report_json"]
    assert "session_duration_minutes" in data["report_json"]


def test_get_grade_returns_session_timing_fields(client):
    session_id = start_session(client)
    _set_mastery_state(session_id, best_scores=[80])
    db = next(app.dependency_overrides[db_module.get_db]())
    session_row = db.query(models.SessionModel).filter(
        models.SessionModel.session_id == session_id
    ).first()
    session_row.started_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=7)
    db.commit()

    response = client.post("/get_grade", json={"session_id": session_id})
    data = response.json()
    assert data["minutes_elapsed"] >= 7
    assert data["minutes_remaining"] <= 13
    assert data["session_duration_minutes"] == 20


def test_generate_report_includes_session_timing_fields(client):
    session_id = start_session(client)
    _set_mastery_state(session_id, best_scores=[80])
    db = next(app.dependency_overrides[db_module.get_db]())
    session_row = db.query(models.SessionModel).filter(
        models.SessionModel.session_id == session_id
    ).first()
    session_row.started_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=9)
    db.commit()

    with _mock_openai_report():
        response = client.post("/generate_report", json={"session_id": session_id})

    data = response.json()
    assert data["report_json"]["minutes_elapsed"] >= 9
    assert data["report_json"]["minutes_remaining"] <= 11
    assert data["report_json"]["session_duration_minutes"] == 20


def test_generate_report_invalid_session(client):
    response = client.post("/generate_report", json={"session_id": "does-not-exist"})
    assert response.status_code == 404


def test_generate_report_uses_authoritative_grade(client):
    """report_json.final_grade equals session.current_grade."""
    session_id = start_session(client)
    _set_mastery_state(session_id, best_scores=[100, 100])
    with _mock_openai_report():
        response = client.post("/generate_report", json={"session_id": session_id})
    assert response.status_code == 200
    data = response.json()
    assert data["report_json"]["final_grade"] == 80.0


def test_generate_report_uses_best_mastery_when_current_mastery_is_lower(client):
    session_id = start_session(client)
    _set_mastery_state(session_id, best_scores=[100, 100], current_scores=[0])
    with _mock_openai_report():
        response = client.post("/generate_report", json={"session_id": session_id})

    data = response.json()
    assert data["report_json"]["final_grade"] == 80.0


def test_generate_report_passes_state_based_explanation(client):
    session_id = start_session(client)
    _set_mastery_state(session_id, best_scores=[100])
    with mock.patch("app.bot_engine.generate_report") as mock_gen_report:
        mock_gen_report.return_value = {
            "report_text": "Report based on T1 understanding.",
            "report_json": {},
        }
        response = client.post("/generate_report", json={"session_id": session_id})

    call_kwargs = mock_gen_report.call_args.kwargs
    assert "Best demonstrated understanding so far is in Topic 1." == call_kwargs["grading_result"]["explanation"]
    assert response.status_code == 200


def test_generate_report_inserts_report_event(client):
    """A grade event with event_type='report' is inserted."""
    session_id = start_session(client)
    mock_client = mock.MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("no api in tests")
    _set_mastery_state(session_id, best_scores=[80])
    with mock.patch("openai.OpenAI", return_value=mock_client):
        client.post("/generate_report", json={"session_id": session_id})

    db = next(app.dependency_overrides[db_module.get_db]())
    events = db.query(models.GradeEventModel).filter(
        models.GradeEventModel.session_id == session_id,
        models.GradeEventModel.event_type == "report",
    ).all()
    assert len(events) >= 1


def test_generate_report_does_not_call_generate_topic_scores(client):
    session_id = start_session(client)
    _set_mastery_state(session_id, best_scores=[100])
    with mock.patch("app.bot_engine.generate_topic_scores", side_effect=AssertionError("should not be called")), \
         _mock_openai_report():
        response = client.post("/generate_report", json={"session_id": session_id})
    assert response.status_code == 200
    assert response.json()["report_json"]["final_grade"] == 55.0
