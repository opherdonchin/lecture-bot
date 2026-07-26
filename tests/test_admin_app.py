import json
import re
import subprocess

from fastapi.testclient import TestClient

import app.admin_main as admin_main
import app.config as config_module


def _auth():
    return ("admin", "secret")


def _settings(tmp_path):
    lectures_dir = tmp_path / "lectures"
    lectures_dir.mkdir(parents=True)
    submissions_dir = tmp_path / "submissions"
    return config_module.Settings(
        lectures_dir=lectures_dir,
        moodle_submissions_dir=submissions_dir,
        moodle_participants_csv=submissions_dir / "participants.csv",
        moodle_deadlines_csv=submissions_dir / "deadlines.csv",
        moodle_grade_import_csv=submissions_dir / "moodle_grade_import.csv",
        moodle_grade_import_report_csv=submissions_dir / "moodle_grade_import_report.csv",
        admin_username="admin",
        admin_password="secret",
    )


def test_admin_requires_basic_auth(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "get_settings", lambda: _settings(tmp_path))
    client = TestClient(admin_main.app)
    response = client.get("/")
    assert response.status_code == 401


def test_admin_home_links_to_primary_sections(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "get_settings", lambda: _settings(tmp_path))
    client = TestClient(admin_main.app)

    response = client.get("/", auth=_auth())

    assert response.status_code == 200
    assert re.search(r'href="[^"]*/lectures"', response.text)
    assert re.search(r'href="[^"]*/sessions"', response.text)
    assert re.search(r'href="[^"]*/grades"', response.text)
    assert re.search(r'href="[^"]*/analysis"', response.text)


def test_admin_can_create_lecture_and_select_sources(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)
    client = TestClient(admin_main.app)

    response = client.post(
        "/lectures",
        auth=_auth(),
        data={"lecture_id": "lecture_new", "title": "New Lecture", "course": "Course"},
    )
    assert response.status_code == 200
    assert "lecture_new" in response.text

    lecture_dir = settings.lectures_dir / "lecture_new"
    (lecture_dir / "slides.pptx").write_text("x", encoding="utf-8")
    (lecture_dir / "handout.txt").write_text("handout", encoding="utf-8")
    (lecture_dir / "notebook.ipynb").write_text("{}", encoding="utf-8")
    (lecture_dir / "transcript.vtt").write_text("WEBVTT\n", encoding="utf-8")

    response = client.post(
        "/lectures/lecture_new/sources",
        auth=_auth(),
        data={
            "slides_source": "slides.pptx",
            "handout_source": "handout.txt",
            "notebook_source": "notebook.ipynb",
            "transcript_source": "transcript.vtt",
        },
    )
    assert response.status_code == 200

    config = json.loads((lecture_dir / "lecture_config.json").read_text(encoding="utf-8"))
    assert config["files"]["slides"]["source"] == "slides.pptx"
    assert config["files"]["minutes"]["target"] == "minutes.json"
    assert config["files"]["rubric"]["target"] == "rubric.md"


def test_admin_build_local_and_upload_generated_artifacts(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)
    lecture_dir = settings.lectures_dir / "lecture_01"
    lecture_dir.mkdir(parents=True)
    (lecture_dir / "slides_source.pptx").write_text("placeholder", encoding="utf-8")
    (lecture_dir / "handout_source.txt").write_text("Handout text\n", encoding="utf-8")
    (lecture_dir / "notebook_source.ipynb").write_text("{}", encoding="utf-8")
    (lecture_dir / "transcript_source.vtt").write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nhello\n", encoding="utf-8")
    (lecture_dir / "lecture_config.json").write_text(
        json.dumps(
            {
                "lecture_id": "lecture_01",
                "title": "Lecture 1",
                "course": "Course",
                "active": True,
                "files": {
                    "slides": {"source": "slides_source.pptx", "target": "slides.md"},
                    "handout": {"source": "handout_source.txt", "target": "handout.md"},
                    "notebook": {"source": "notebook_source.ipynb", "target": "notebook.md"},
                    "transcript": {"source": "transcript_source.vtt", "target": "transcript.md"},
                    "minutes": {"target": "minutes.json"},
                    "rubric": {"target": "rubric.md"},
                },
                "topics": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    client = TestClient(admin_main.app)

    def fake_slides(source, target):
        target.write_text("# Slides\n", encoding="utf-8")

    def fake_notebook(source, target):
        target.write_text("# Notebook\n", encoding="utf-8")

    monkeypatch.setattr("scripts.convert_pptx_to_md.convert_pptx_to_md", fake_slides)
    monkeypatch.setattr("scripts.convert_ipynb_to_md.convert_ipynb_to_md", fake_notebook)

    response = client.post("/lectures/lecture_01/build/local", auth=_auth())
    assert response.status_code == 200
    assert (lecture_dir / "slides.md").exists()
    assert (lecture_dir / "handout.md").exists()
    assert (lecture_dir / "notebook.md").exists()
    assert (lecture_dir / "transcript.md").exists()

    response = client.post(
        "/lectures/lecture_01/generated/minutes",
        auth=_auth(),
        files={"uploaded_file": ("minutes.json", b'{"lecture_metadata": {"title": "Lecture 1"}}\n', "application/json")},
    )
    assert response.status_code == 200
    assert (lecture_dir / "minutes.json").exists()

    response = client.post(
        "/lectures/lecture_01/generated/rubric",
        auth=_auth(),
        files={"uploaded_file": ("rubric.md", b"# Mastery Rubric\n\n### T1. Topic One\n**Importance:** core\n", "text/markdown")},
    )
    assert response.status_code == 200

    config = json.loads((lecture_dir / "lecture_config.json").read_text(encoding="utf-8"))
    assert config["topics"] == [{"topic_id": "T1", "label": "Topic One", "importance": "core"}]


def test_admin_grades_uploads_submission_zip_and_regenerates_outputs(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)
    lecture_dir = settings.lectures_dir / "lecture_01"
    lecture_dir.mkdir(parents=True)
    (lecture_dir / "lecture_config.json").write_text(
        json.dumps({"lecture_id": "lecture_01", "title": "Lecture 1", "active": True, "files": {}, "topics": []}) + "\n",
        encoding="utf-8",
    )
    called = {}

    def fake_run_grade_import():
        called["ran"] = True
        settings.moodle_grade_import_csv.parent.mkdir(parents=True, exist_ok=True)
        settings.moodle_grade_import_csv.write_text("ID number,lecture_01\n206391179,85\n", encoding="utf-8")
        settings.moodle_grade_import_report_csv.write_text("status\naccepted\n", encoding="utf-8")
        return {
            "participants": 1,
            "archives": 1,
            "records": 1,
            "accepted": 1,
            "accepted_superseded": 0,
            "rejected": 0,
            "difficulties": 0,
            "upload_rows": 1,
        }

    monkeypatch.setattr(admin_main, "_run_grade_import", fake_run_grade_import)
    client = TestClient(admin_main.app)

    response = client.post(
        "/grades/submissions",
        auth=_auth(),
        files={"submission_lecture_01": ("lecture_01.zip", b"zip bytes", "application/zip")},
    )

    assert response.status_code == 200
    assert called["ran"] is True
    assert (settings.moodle_submissions_dir / "lecture_01_submissions.zip").read_bytes() == b"zip bytes"
    assert "regenerated Moodle import files" in response.text

    download = client.get("/grades/files/import", auth=_auth())
    assert download.status_code == 200
    assert "206391179" in download.text


def test_admin_grades_uploads_multi_lecture_zip_and_regenerates_outputs(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)
    lecture_dir = settings.lectures_dir / "lecture_01"
    lecture_dir.mkdir(parents=True)
    (lecture_dir / "lecture_config.json").write_text(
        json.dumps({"lecture_id": "lecture_01", "title": "Lecture 1", "active": True, "files": {}, "topics": []}) + "\n",
        encoding="utf-8",
    )
    called = {}

    def fake_run_grade_import():
        called["ran"] = True
        settings.moodle_grade_import_csv.parent.mkdir(parents=True, exist_ok=True)
        settings.moodle_grade_import_csv.write_text("ID number,lecture_01\n206391179,85\n", encoding="utf-8")
        settings.moodle_grade_import_report_csv.write_text("status\naccepted\n", encoding="utf-8")
        return {
            "participants": 1,
            "archives": 1,
            "records": 1,
            "accepted": 1,
            "accepted_superseded": 0,
            "rejected": 0,
            "difficulties": 0,
            "upload_rows": 1,
        }

    monkeypatch.setattr(admin_main, "_run_grade_import", fake_run_grade_import)
    client = TestClient(admin_main.app)

    response = client.post(
        "/grades/submissions/multi",
        auth=_auth(),
        files={"uploaded_file": ("additional.zip", b"zip bytes", "application/zip")},
    )

    assert response.status_code == 200
    assert called["ran"] is True
    assert (settings.moodle_submissions_dir / "multi_lecture_submissions.zip").read_bytes() == b"zip bytes"
    assert "regenerated Moodle import files" in response.text


def test_admin_grades_clears_only_submission_zips(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)
    settings.moodle_submissions_dir.mkdir(parents=True, exist_ok=True)
    lecture_zip = settings.moodle_submissions_dir / "lecture_01_submissions.zip"
    multi_zip = settings.moodle_submissions_dir / "multi_lecture_submissions.zip"
    generated_csv = settings.moodle_grade_import_csv
    participants_csv = settings.moodle_participants_csv
    deadlines_csv = settings.moodle_deadlines_csv
    for path in [lecture_zip, multi_zip, generated_csv, participants_csv, deadlines_csv]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"content")

    client = TestClient(admin_main.app)
    response = client.post("/grades/submissions/clear", auth=_auth())

    assert response.status_code == 200
    assert "Cleared 2 submission ZIP" in response.text
    assert not lecture_zip.exists()
    assert not multi_zip.exists()
    assert generated_csv.exists()
    assert participants_csv.exists()
    assert deadlines_csv.exists()


def test_admin_grades_deadline_template_and_upload(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)
    lecture_dir = settings.lectures_dir / "lecture_01"
    lecture_dir.mkdir(parents=True)
    (lecture_dir / "lecture_config.json").write_text(
        json.dumps({"lecture_id": "lecture_01", "title": "Lecture 1", "active": True, "files": {}, "topics": []}) + "\n",
        encoding="utf-8",
    )
    client = TestClient(admin_main.app)

    template = client.get("/grades/deadlines/template", auth=_auth())
    assert template.status_code == 200
    assert "lecture_id,deadline" in template.text
    assert "lecture_01," in template.text

    response = client.post(
        "/grades/deadlines",
        auth=_auth(),
        files={"uploaded_file": ("deadlines.csv", b"lecture_id,deadline\nlecture_01,2026-04-14T23:59:00+03:00\n", "text/csv")},
    )

    assert response.status_code == 200
    assert settings.moodle_deadlines_csv.read_text(encoding="utf-8") == (
        "lecture_id,deadline\nlecture_01,2026-04-14T23:59:00+03:00\n"
    )
    assert "Deadlines CSV updated" in response.text

    response = client.post(
        "/grades/deadlines/edit",
        auth=_auth(),
        data={"timezone_offset": "+03:00", "deadline_lecture_01": "2026-04-21T23:59"},
    )

    assert response.status_code == 200
    assert settings.moodle_deadlines_csv.read_text(encoding="utf-8") == (
        "lecture_id,deadline\nlecture_01,2026-04-21T23:59:00+03:00\n"
    )
    assert "Deadlines saved" in response.text


def test_restart_student_app_uses_configured_system_service_command(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(admin_main.subprocess, "run", fake_run)

    ok, message = admin_main._restart_student_app()

    assert ok is True
    assert message == "Student app restarted successfully."
    assert calls[0][0] == ["sudo", "-n", "systemctl", "restart", "lecture-bot.service"]
    assert calls[0][1]["timeout"] == 15


def test_restart_student_app_explains_permission_failure(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="Interactive authentication required.")

    monkeypatch.setattr(admin_main.subprocess, "run", fake_run)

    ok, message = admin_main._restart_student_app()

    assert ok is False
    assert "needs service-manager permission" in message
    assert "sudo -n systemctl restart lecture-bot.service" in message
