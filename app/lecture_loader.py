import json as j
import pathlib as pathlib_


class LectureNotFoundError(FileNotFoundError):
    pass


def load_lecture_package(lectures_dir: pathlib_.Path, lecture_id: str) -> dict:
    lecture_path = lectures_dir / lecture_id
    if not lecture_path.exists() or not lecture_path.is_dir():
        raise LectureNotFoundError(f"Lecture package not found: {lecture_id}")

    config_path = lecture_path / "lecture_config.json"
    rubric_path = lecture_path / "rubric.md"
    slides_path = lecture_path / "slides.md"
    handout_path = lecture_path / "handout.md"
    notebook_path = lecture_path / "notebook.md"
    bot_notes_path = lecture_path / "bot_notes.md"

    required_paths = [config_path, rubric_path, slides_path, handout_path, notebook_path]
    missing = [str(path.name) for path in required_paths if not path.exists()]
    if missing:
        raise LectureNotFoundError(
            f"Lecture package {lecture_id} is missing required files: {', '.join(missing)}"
        )

    with config_path.open("r", encoding="utf-8") as f:
        lecture_config = j.load(f)

    def read_text(path: pathlib_.Path) -> str:
        return path.read_text(encoding="utf-8")

    return {
        "lecture_id": lecture_id,
        "config": lecture_config,
        "topics": lecture_config.get("topics", []),
        "rubric": read_text(rubric_path),
        "slides": read_text(slides_path),
        "handout": read_text(handout_path),
        "notebook": read_text(notebook_path),
        "bot_notes": read_text(bot_notes_path) if bot_notes_path.exists() else "",
    }