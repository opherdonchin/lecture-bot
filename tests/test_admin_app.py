import json

from fastapi.testclient import TestClient

import app.admin_main as admin_main
import app.config as config_module


def _auth():
    return ("admin", "secret")


def _settings(tmp_path):
    lectures_dir = tmp_path / "lectures"
    lectures_dir.mkdir(parents=True)
    return config_module.Settings(
        lectures_dir=lectures_dir,
        admin_username="admin",
        admin_password="secret",
    )


def test_admin_requires_basic_auth(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "get_settings", lambda: _settings(tmp_path))
    client = TestClient(admin_main.app)
    response = client.get("/")
    assert response.status_code == 401


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
