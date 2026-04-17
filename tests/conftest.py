import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.config as config_module
import app.db as db_module
from app.main import app

Base = db_module.Base


def _write_fixture_lecture(lectures_dir, lecture_id: str, topic_count: int = 10):
    lecture_dir = lectures_dir / lecture_id
    lecture_dir.mkdir(parents=True)
    topics = [
        {"topic_id": f"T{i}", "label": f"Topic {i}", "importance": "core"}
        for i in range(1, topic_count + 1)
    ]
    (lecture_dir / "lecture_config.json").write_text(
        json.dumps(
            {
                "lecture_id": lecture_id,
                "title": "Fixture Lecture",
                "course": "Test Course",
                "active": True,
                "topics": topics,
            }
        ),
        encoding="utf-8",
    )
    (lecture_dir / "rubric.md").write_text(
        "\n\n".join(
            [
                f"### T{i}. Topic {i}\n\n- **Description:** Topic {i}.\n\n- **Importance:** core"
                for i in range(1, topic_count + 1)
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (lecture_dir / "slides.md").write_text("Slides\n", encoding="utf-8")
    (lecture_dir / "handout.md").write_text("Handout\n", encoding="utf-8")
    (lecture_dir / "minutes.json").write_text('{"lecture_metadata": {"title": "Fixture Lecture"}}\n', encoding="utf-8")
    (lecture_dir / "notebook.md").write_text("Notebook\n", encoding="utf-8")


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    lectures_dir = tmp_path / "lectures"
    lectures_dir.mkdir(parents=True)
    (lectures_dir / "config.json").write_text(
        json.dumps(
            {
                "context_files": [
                    {"key": "slides", "path": "slides.md", "label": "Slides", "required": True},
                    {"key": "handout", "path": "handout.md", "label": "Handout", "required": True},
                    {"key": "minutes", "path": "minutes.json", "label": "Instructional Minutes", "required": True},
                    {"key": "notebook", "path": "notebook.md", "label": "Notebook", "required": True},
                ]
            }
        ),
        encoding="utf-8",
    )
    _write_fixture_lecture(lectures_dir, "lecture_01")

    test_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    test_settings = config_module.Settings(
        database_url=f"sqlite:///{db_path}",
        lectures_dir=lectures_dir,
    )

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(config_module, "get_settings", lambda: test_settings)
    app.dependency_overrides[db_module.get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
