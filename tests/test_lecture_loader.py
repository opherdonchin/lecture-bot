import json

import pytest

import app.lecture_loader as lecture_loader


def write_lectures_defaults(root) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "config.json").write_text(
        json.dumps(
            {
                "context_files": [
                    {"key": "slides", "path": "slides.md", "label": "Slides", "required": True},
                    {"key": "minutes", "path": "minutes.json", "label": "Instructional Minutes", "required": True},
                    {"key": "notebook", "path": "notebook.md", "label": "Notebook", "required": False},
                ]
            }
        ),
        encoding="utf-8",
    )


def write_lecture_package(root, lecture_id: str, *, include_minutes: bool, context_files=None) -> None:
    lecture_dir = root / lecture_id
    lecture_dir.mkdir(parents=True)

    (lecture_dir / "lecture_config.json").write_text(
        json.dumps(
            {
                "title": "Fixture Lecture",
                "topics": [],
                **({"context_files": context_files} if context_files is not None else {}),
            }
        ),
        encoding="utf-8",
    )
    (lecture_dir / "rubric.md").write_text("Rubric\n", encoding="utf-8")
    (lecture_dir / "slides.md").write_text("Slides\n", encoding="utf-8")
    (lecture_dir / "notebook.md").write_text("Notebook\n", encoding="utf-8")
    if include_minutes:
        (lecture_dir / "minutes.json").write_text('{"ok": true}\n', encoding="utf-8")


def test_load_lecture_package_uses_root_context_defaults(tmp_path):
    lectures_dir = tmp_path / "lectures"
    write_lectures_defaults(lectures_dir)
    write_lecture_package(lectures_dir, "lecture_fixture", include_minutes=True)

    package = lecture_loader.load_lecture_package(lectures_dir, "lecture_fixture")

    assert [section["key"] for section in package["context_sections"]] == ["slides", "minutes", "notebook"]
    assert package["minutes"] == '{"ok": true}\n'


def test_load_lecture_package_requires_default_required_context_file(tmp_path):
    lectures_dir = tmp_path / "lectures"
    write_lectures_defaults(lectures_dir)
    write_lecture_package(lectures_dir, "lecture_fixture", include_minutes=False)

    with pytest.raises(lecture_loader.LectureNotFoundError, match="minutes.json"):
        lecture_loader.load_lecture_package(lectures_dir, "lecture_fixture")


def test_load_lecture_package_allows_lecture_level_context_override(tmp_path):
    lectures_dir = tmp_path / "lectures"
    write_lectures_defaults(lectures_dir)
    write_lecture_package(
        lectures_dir,
        "lecture_fixture",
        include_minutes=False,
        context_files=[
            {"key": "slides", "path": "slides.md", "label": "Slide Deck", "required": True},
            {"key": "notebook", "path": "notebook.md", "label": "Lab Notes", "required": True},
        ],
    )

    package = lecture_loader.load_lecture_package(lectures_dir, "lecture_fixture")

    assert [section["label"] for section in package["context_sections"]] == ["Slide Deck", "Lab Notes"]
    assert "minutes" not in package
