import datetime as dt
import json
import zipfile
from io import BytesIO

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.admin_main as admin_main
import app.config as config_module
import app.db as db_module
import app.models as models


SESSION_ONE = "11111111-1111-4111-8111-111111111111"
SESSION_TWO = "22222222-2222-4222-8222-222222222222"
SESSION_THREE = "33333333-3333-4333-8333-333333333333"


def _auth():
    return ("admin", "secret")


def _write_lecture_package(lectures_dir, lecture_id: str) -> None:
    lecture_dir = lectures_dir / lecture_id
    lecture_dir.mkdir(parents=True, exist_ok=True)
    (lecture_dir / "lecture_config.json").write_text(
        json.dumps(
            {
                "lecture_id": lecture_id,
                "title": lecture_id,
                "course": "Course",
                "active": True,
                "topics": [{"topic_id": "T1", "label": "Topic One", "importance": "core"}],
            }
        ),
        encoding="utf-8",
    )
    (lecture_dir / "slides.md").write_text("Slides\n", encoding="utf-8")
    (lecture_dir / "handout.md").write_text("Handout\n", encoding="utf-8")
    (lecture_dir / "minutes.json").write_text('{"lecture_metadata": {"title": "Fixture"}}\n', encoding="utf-8")
    (lecture_dir / "rubric.md").write_text("### T1. Topic One\n\n- **Importance:** core\n", encoding="utf-8")


def _settings(tmp_path):
    lectures_dir = tmp_path / "lectures"
    lectures_dir.mkdir(parents=True)
    (lectures_dir / "config.json").write_text(
        json.dumps(
            {
                "context_files": [
                    {"key": "slides", "path": "slides.md", "label": "Slides", "required": True},
                    {"key": "handout", "path": "handout.md", "label": "Handout", "required": True},
                    {"key": "minutes", "path": "minutes.json", "label": "Minutes", "required": True},
                ]
            }
        ),
        encoding="utf-8",
    )
    _write_lecture_package(lectures_dir, "lecture_01")
    _write_lecture_package(lectures_dir, "lecture_02")
    db_path = tmp_path / "test.db"
    return config_module.Settings(
        database_url=f"sqlite:///{db_path}",
        lectures_dir=lectures_dir,
        admin_username="admin",
        admin_password="secret",
    )


def _add_session(db, *, session_id, student_id, lecture_id, started_at, grade, user_turns, assistant_turns, notes=0, grade_events=0):
    db.add(
        models.SessionModel(
            session_id=session_id,
            student_id=student_id,
            lecture_id=lecture_id,
            started_at=started_at,
            current_grade=grade,
        )
    )
    db.add(
        models.SessionStateModel(
            session_id=session_id,
            state_json=json.dumps({"turn_count": user_turns}),
            updated_at=started_at,
        )
    )
    for index in range(user_turns):
        db.add(
            models.MessageModel(
                session_id=session_id,
                role="user",
                content=f"user message {index}",
                timestamp=started_at + dt.timedelta(minutes=index * 2),
            )
        )
    for index in range(assistant_turns):
        db.add(
            models.MessageModel(
                session_id=session_id,
                role="assistant",
                content=f"assistant message {index}",
                timestamp=started_at + dt.timedelta(minutes=index * 2 + 1),
            )
        )
    for index in range(notes):
        db.add(
            models.SessionNoteModel(
                session_id=session_id,
                note_text=f"important student comment {index}",
                turn_index=index,
                state_json=json.dumps({"note": index}),
                created_at=started_at + dt.timedelta(minutes=30 + index),
            )
        )
    for index in range(grade_events):
        db.add(
            models.GradeEventModel(
                session_id=session_id,
                event_type="current_grade",
                grade=grade,
                timestamp=started_at + dt.timedelta(minutes=40 + index),
                payload_json=json.dumps({"grade": grade}),
            )
        )


def _client_with_sessions(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)
    test_engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    db_module.Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    with TestSession() as db:
        _add_session(
            db,
            session_id=SESSION_ONE,
            student_id="alpha",
            lecture_id="lecture_01",
            started_at=dt.datetime(2026, 4, 20, 9, 0, 0),
            grade=88,
            user_turns=4,
            assistant_turns=5,
            notes=1,
            grade_events=2,
        )
        _add_session(
            db,
            session_id=SESSION_TWO,
            student_id="alpha-extra",
            lecture_id="lecture_02",
            started_at=dt.datetime(2026, 4, 21, 9, 0, 0),
            grade=55,
            user_turns=1,
            assistant_turns=2,
        )
        _add_session(
            db,
            session_id=SESSION_THREE,
            student_id="beta",
            lecture_id="lecture_01",
            started_at=dt.datetime(2026, 4, 22, 9, 0, 0),
            grade=15,
            user_turns=8,
            assistant_turns=9,
        )
        db.commit()

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    admin_main.app.dependency_overrides[db_module.get_db] = override_get_db
    client = TestClient(admin_main.app)
    try:
        yield client, settings
    finally:
        admin_main.app.dependency_overrides.clear()


def _zip_names(response):
    with zipfile.ZipFile(BytesIO(response.content)) as zf:
        return zf.namelist(), zf


def test_admin_sessions_requires_auth(tmp_path, monkeypatch):
    client_iter = _client_with_sessions(tmp_path, monkeypatch)
    client, _settings_obj = next(client_iter)
    try:
        response = client.get("/sessions")
        assert response.status_code == 401
    finally:
        next(client_iter, None)


def test_admin_sessions_displays_counts_and_root_path_safe_links(tmp_path, monkeypatch):
    client_iter = _client_with_sessions(tmp_path, monkeypatch)
    client, _settings_obj = next(client_iter)
    original_root_path = admin_main.app.root_path
    admin_main.app.root_path = "/stats-admin"
    try:
        response = client.get("/stats-admin/sessions", auth=_auth())
    finally:
        admin_main.app.root_path = original_root_path
        next(client_iter, None)

    assert response.status_code == 200
    html = response.text
    assert "alpha" in html
    assert SESSION_ONE in html
    assert "important student comment" not in html
    assert ">4</td>" in html
    assert ">5</td>" in html
    assert ">1</td>" in html
    assert ">2</td>" in html
    assert 'action="/stats-admin/sessions"' in html
    assert 'action="/stats-admin/sessions/export"' in html


def test_admin_sessions_filters(tmp_path, monkeypatch):
    client_iter = _client_with_sessions(tmp_path, monkeypatch)
    client, _settings_obj = next(client_iter)
    try:
        response = client.get("/sessions?student_id=alpha&student_match=exact", auth=_auth())
        assert SESSION_ONE in response.text
        assert SESSION_TWO not in response.text

        response = client.get("/sessions?student_id=alpha&student_match=contains", auth=_auth())
        assert SESSION_ONE in response.text
        assert SESSION_TWO in response.text

        response = client.get("/sessions?lecture_id=lecture_02", auth=_auth())
        assert SESSION_TWO in response.text
        assert SESSION_ONE not in response.text

        response = client.get("/sessions?start_date=2026-04-21&end_date=2026-04-21", auth=_auth())
        assert SESSION_TWO in response.text
        assert SESSION_ONE not in response.text
        assert SESSION_THREE not in response.text

        response = client.get("/sessions?min_user_turns=5", auth=_auth())
        assert SESSION_THREE in response.text
        assert SESSION_ONE not in response.text

        response = client.get("/sessions?min_grade=50&max_grade=60", auth=_auth())
        assert SESSION_TWO in response.text
        assert SESSION_ONE not in response.text
    finally:
        next(client_iter, None)


def test_admin_sessions_export_validation(tmp_path, monkeypatch):
    client_iter = _client_with_sessions(tmp_path, monkeypatch)
    client, _settings_obj = next(client_iter)
    try:
        response = client.post("/sessions/export", auth=_auth(), data={})
        assert response.status_code == 400
        assert "Select at least one" in response.text

        response = client.post("/sessions/export", auth=_auth(), data={"session_id": "not-a-uuid"})
        assert response.status_code == 400
        assert "Invalid session id" in response.text

        response = client.post(
            "/sessions/export",
            auth=_auth(),
            data={"session_id": "44444444-4444-4444-8444-444444444444"},
        )
        assert response.status_code == 400
        assert "Unknown session id" in response.text

        too_many = [f"aaaaaaaa-aaaa-4aaa-8aaa-{index:012d}" for index in range(51)]
        response = client.post("/sessions/export", auth=_auth(), data={"session_id": too_many})
        assert response.status_code == 400
        assert "Select no more than" in response.text
    finally:
        next(client_iter, None)


def test_admin_sessions_export_zip_shape_and_notes(tmp_path, monkeypatch):
    client_iter = _client_with_sessions(tmp_path, monkeypatch)
    client, _settings_obj = next(client_iter)
    try:
        response = client.post(
            "/sessions/export",
            auth=_auth(),
            data={"session_id": [SESSION_ONE, SESSION_TWO]},
        )
    finally:
        next(client_iter, None)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "lecture_bot_sessions_" in response.headers["content-disposition"]

    with zipfile.ZipFile(BytesIO(response.content)) as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        top_manifest = json.loads(zf.read("manifest.json"))
        assert top_manifest["format"] == "lecture_bot_sessions_multi_export"
        assert top_manifest["session_ids"] == [SESSION_ONE, SESSION_TWO]

        for session_id in [SESSION_ONE, SESSION_TWO]:
            assert f"{session_id}/manifest.json" in names
            assert f"{session_id}/conversation/session_bundle.json" in names
            assert f"{session_id}/conversation/dialogue_turn_audits.json" in names
            assert f"{session_id}/conversation/private_artifact_logs.json" in names
            assert f"{session_id}/conversation/session_notes.json" in names

        notes = json.loads(zf.read(f"{SESSION_ONE}/conversation/session_notes.json"))
        assert notes[0]["note_text"] == "important student comment 0"
        assert not any(name.endswith(".zip") for name in names)
        allowed_prefixes = ("manifest.json", f"{SESSION_ONE}/", f"{SESSION_TWO}/")
        assert all(name == "manifest.json" or name.startswith(allowed_prefixes[1:]) for name in names)


def test_admin_single_session_export_uses_session_directory(tmp_path, monkeypatch):
    client_iter = _client_with_sessions(tmp_path, monkeypatch)
    client, _settings_obj = next(client_iter)
    try:
        response = client.post("/sessions/export", auth=_auth(), data={"session_id": SESSION_ONE})
    finally:
        next(client_iter, None)

    assert response.status_code == 200
    with zipfile.ZipFile(BytesIO(response.content)) as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        assert f"{SESSION_ONE}/manifest.json" in names
        assert "manifest.json" in names
        assert not any(name.startswith(f"{SESSION_TWO}/") for name in names)
