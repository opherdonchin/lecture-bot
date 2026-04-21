import json as j
import pathlib as pathlib_


class LectureNotFoundError(FileNotFoundError):
    pass


def load_lectures_defaults(lectures_dir: pathlib_.Path) -> dict:
    defaults_path = lectures_dir / "config.json"
    if not defaults_path.exists():
        return {}
    return j.loads(defaults_path.read_text(encoding="utf-8"))


def resolve_context_files(lectures_defaults: dict, lecture_config: dict) -> list[dict]:
    context_files = lecture_config.get("context_files", lectures_defaults.get("context_files"))
    if not isinstance(context_files, list) or not context_files:
        raise ValueError("Lecture config must define a non-empty context_files list directly or via lectures/config.json")

    resolved: list[dict] = []
    for item in context_files:
        if not isinstance(item, dict):
            raise ValueError("Each context_files entry must be an object")
        key = item.get("key")
        path = item.get("path")
        label = item.get("label") or str(key)
        required = item.get("required", True)
        if not isinstance(key, str) or not key:
            raise ValueError("Each context_files entry must include a non-empty string key")
        if not isinstance(path, str) or not path:
            raise ValueError("Each context_files entry must include a non-empty string path")
        resolved.append(
            {
                "key": key,
                "path": path,
                "label": str(label),
                "required": bool(required),
            }
        )
    return resolved


def load_lecture_package(lectures_dir: pathlib_.Path, lecture_id: str) -> dict:
    lecture_path = lectures_dir / lecture_id
    if not lecture_path.exists() or not lecture_path.is_dir():
        raise LectureNotFoundError(f"Lecture package not found: {lecture_id}")

    lectures_defaults = load_lectures_defaults(lectures_dir)
    config_path = lecture_path / "lecture_config.json"
    rubric_path = lecture_path / "rubric.md"

    required_paths = [config_path, rubric_path]
    missing = [str(path.name) for path in required_paths if not path.exists()]
    if missing:
        raise LectureNotFoundError(
            f"Lecture package {lecture_id} is missing required files: {', '.join(missing)}"
        )

    with config_path.open("r", encoding="utf-8") as f:
        lecture_config = j.load(f)
    context_files = resolve_context_files(lectures_defaults, lecture_config)

    def read_text(path: pathlib_.Path) -> str:
        return path.read_text(encoding="utf-8")

    context_sections: list[dict] = []
    context_values: dict[str, str] = {}
    missing_context_paths: list[str] = []
    for item in context_files:
        file_path = lecture_path / item["path"]
        if not file_path.exists():
            if item["required"]:
                missing_context_paths.append(item["path"])
            continue
        content = read_text(file_path)
        context_sections.append(
            {
                "key": item["key"],
                "label": item["label"],
                "content": content,
            }
        )
        context_values[item["key"]] = content

    if missing_context_paths:
        raise LectureNotFoundError(
            f"Lecture package {lecture_id} is missing required files: {', '.join(missing_context_paths)}"
        )

    return {
        "lecture_id": lecture_id,
        "config": lecture_config,
        "topics": lecture_config.get("topics", []),
        "rubric": read_text(rubric_path),
        "context_sections": context_sections,
        **context_values,
    }
