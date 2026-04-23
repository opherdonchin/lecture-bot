import contextlib
import json
import pathlib
import re

from fastapi.testclient import TestClient

import app.admin_main as admin_main
import app.config as config_module
import app.main as student_main


@contextlib.contextmanager
def _temporary_root_path(fastapi_app, root_path: str):
    original_root_path = fastapi_app.root_path
    fastapi_app.root_path = root_path
    try:
        yield
    finally:
        fastapi_app.root_path = original_root_path


def _extract_student_routes(html: str) -> dict[str, str]:
    match = re.search(r"window\.APP_ROUTES = (\{.*?\});", html, flags=re.S)
    assert match, "student route config was not rendered"
    return json.loads(match.group(1))


def _admin_auth():
    return ("admin", "secret")


def _admin_settings(tmp_path):
    lectures_dir = tmp_path / "lectures"
    lectures_dir.mkdir(parents=True)
    return config_module.Settings(
        lectures_dir=lectures_dir,
        admin_username="admin",
        admin_password="secret",
    )


def _write_admin_lecture(lectures_dir):
    lecture_dir = lectures_dir / "lecture_01"
    lecture_dir.mkdir(parents=True)
    (lecture_dir / "slides.md").write_text("Slides\n", encoding="utf-8")
    (lecture_dir / "handout.md").write_text("Handout\n", encoding="utf-8")
    (lecture_dir / "notebook.md").write_text("Notebook\n", encoding="utf-8")
    (lecture_dir / "transcript.md").write_text("Transcript\n", encoding="utf-8")
    (lecture_dir / "minutes.json").write_text('{"lecture_metadata": {"title": "Lecture 1"}}\n', encoding="utf-8")
    (lecture_dir / "rubric.md").write_text("# Rubric\n", encoding="utf-8")
    (lecture_dir / "lecture_config.json").write_text(
        json.dumps(
            {
                "lecture_id": "lecture_01",
                "title": "Lecture 1",
                "course": "Course",
                "active": True,
                "files": {
                    "slides": {"source": "slides.md", "target": "slides.md"},
                    "handout": {"source": "handout.md", "target": "handout.md"},
                    "notebook": {"source": "notebook.md", "target": "notebook.md"},
                    "transcript": {"source": "transcript.md", "target": "transcript.md"},
                    "minutes": {"target": "minutes.json"},
                    "rubric": {"target": "rubric.md"},
                },
                "topics": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return lecture_dir


def test_repo_default_prefix_settings_are_committed(monkeypatch):
    monkeypatch.delenv("LECTURE_BOT_STUDENT_ROOT_PATH", raising=False)
    monkeypatch.delenv("LECTURE_BOT_ADMIN_ROOT_PATH", raising=False)
    settings = config_module.Settings(_env_file=None)
    assert settings.student_root_path == "/bot"
    assert settings.admin_root_path == "/bot-admin"


def test_prefix_settings_can_be_overridden_by_environment(monkeypatch):
    monkeypatch.setenv("LECTURE_BOT_STUDENT_ROOT_PATH", "/stats")
    monkeypatch.setenv("LECTURE_BOT_ADMIN_ROOT_PATH", "/stats-admin")
    settings = config_module.Settings(_env_file=None)
    assert settings.student_root_path == "/stats"
    assert settings.admin_root_path == "/stats-admin"


def test_student_default_prefix_rendered_in_static_and_api_urls():
    with _temporary_root_path(student_main.app, "/bot"):
        client = TestClient(student_main.app)
        response = client.get("/bot/")

    assert response.status_code == 200
    assert 'href="/bot/static/style.css"' in response.text
    assert 'src="/bot/static/chat.js"' in response.text

    routes = _extract_student_routes(response.text)
    assert routes == {
        "list_lectures": "/bot/lectures",
        "start_session": "/bot/start_session",
        "send_message": "/bot/send_message",
        "get_grade": "/bot/get_grade",
        "generate_report": "/bot/generate_report",
        "restart_session": "/bot/restart_session",
    }


def test_student_override_prefix_example_rendered_in_static_and_api_urls():
    with _temporary_root_path(student_main.app, "/stats"):
        client = TestClient(student_main.app)
        response = client.get("/stats/")

    assert response.status_code == 200
    assert 'href="/stats/static/style.css"' in response.text
    assert 'src="/stats/static/chat.js"' in response.text

    routes = _extract_student_routes(response.text)
    assert routes["list_lectures"] == "/stats/lectures"
    assert routes["start_session"] == "/stats/start_session"
    assert routes["send_message"] == "/stats/send_message"
    assert routes["get_grade"] == "/stats/get_grade"
    assert routes["generate_report"] == "/stats/generate_report"
    assert routes["restart_session"] == "/stats/restart_session"


def test_admin_default_prefix_rendered_in_index_static_links_and_forms(tmp_path, monkeypatch):
    settings = _admin_settings(tmp_path)
    _write_admin_lecture(settings.lectures_dir)
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)

    with _temporary_root_path(admin_main.app, "/bot-admin"):
        client = TestClient(admin_main.app)
        response = client.get("/bot-admin/", auth=_admin_auth())

    assert response.status_code == 200
    assert 'href="/bot-admin/static/style.css"' in response.text
    assert 'href="/bot-admin/static/admin.css"' in response.text
    assert 'action="/bot-admin/lectures"' in response.text
    assert 'href="/bot-admin/lectures/lecture_01"' in response.text


def test_admin_override_prefix_rendered_in_detail_links_and_forms(tmp_path, monkeypatch):
    settings = _admin_settings(tmp_path)
    _write_admin_lecture(settings.lectures_dir)
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)

    with _temporary_root_path(admin_main.app, "/stats-admin"):
        client = TestClient(admin_main.app)
        response = client.get("/stats-admin/lectures/lecture_01", auth=_admin_auth())

    assert response.status_code == 200
    html = response.text
    assert 'href="/stats-admin/static/style.css"' in html
    assert 'href="/stats-admin/static/admin.css"' in html
    assert 'href="/stats-admin/lectures"' in html
    assert 'action="/stats-admin/lectures/lecture_01/metadata"' in html
    assert 'action="/stats-admin/lectures/lecture_01/upload"' in html
    assert 'href="/stats-admin/lectures/lecture_01/files/slides.md"' in html
    assert 'action="/stats-admin/lectures/lecture_01/delete"' in html
    assert 'action="/stats-admin/lectures/lecture_01/sources"' in html
    assert 'action="/stats-admin/lectures/lecture_01/build/local"' in html
    assert 'href="/stats-admin/lectures/lecture_01/prompt/minutes.txt"' in html
    assert 'href="/stats-admin/lectures/lecture_01/bundle/minutes.zip"' in html
    assert 'action="/stats-admin/lectures/lecture_01/generated/minutes"' in html
    assert 'href="/stats-admin/lectures/lecture_01/prompt/rubric.txt"' in html
    assert 'href="/stats-admin/lectures/lecture_01/bundle/rubric.zip"' in html
    assert 'action="/stats-admin/lectures/lecture_01/generated/rubric"' in html


def test_prefix_sensitive_frontend_files_do_not_keep_root_relative_urls():
    chat_js = pathlib.Path("app/static/chat.js").read_text(encoding="utf-8")
    assert not re.search(r"fetch\(\s*['\"]/", chat_js)

    for template_path in [
        pathlib.Path("app/templates/chat.html"),
        pathlib.Path("app/templates/admin_index.html"),
        pathlib.Path("app/templates/admin_lecture.html"),
    ]:
        template = template_path.read_text(encoding="utf-8")
        assert not re.search(r"\b(?:href|src|action)=['\"]/", template)
