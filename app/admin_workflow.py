from __future__ import annotations

import io
import json
import pathlib
import shutil
import subprocess
import zipfile
from dataclasses import dataclass

import fastapi as fa

import app.bot_engine as bot_engine
import app.prompt_loader as prompt_loader
import scripts.convert_ipynb_to_md as convert_ipynb
import scripts.convert_pptx_to_md as convert_pptx
import scripts.convert_qmd_to_md as convert_qmd
import scripts.convert_vtt_to_md as convert_vtt


SOURCE_KEYS = ("slides", "handout", "notebook", "transcript")
GENERATED_KEYS = ("minutes", "rubric")
TARGET_BY_KEY = {
    "slides": "slides.md",
    "handout": "handout.md",
    "notebook": "notebook.md",
    "transcript": "transcript.md",
    "minutes": "minutes.json",
    "rubric": "rubric.md",
}
DISPLAY_LABELS = {
    "slides": "Slides",
    "handout": "Handout",
    "notebook": "Notebook",
    "transcript": "Transcript",
    "minutes": "Instructional Minutes",
    "rubric": "Mastery Rubric",
}


@dataclass(frozen=True)
class LectureFileInfo:
    name: str
    size_bytes: int


def list_lecture_dirs(lectures_dir: pathlib.Path) -> list[pathlib.Path]:
    if not lectures_dir.exists():
        return []
    return sorted(path for path in lectures_dir.iterdir() if path.is_dir())


def validate_lecture_id(lecture_id: str) -> str:
    cleaned = lecture_id.strip()
    if not cleaned:
        raise ValueError("Lecture id is required.")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    if any(ch not in allowed for ch in cleaned):
        raise ValueError("Lecture id may contain only letters, numbers, underscores, and hyphens.")
    return cleaned


def resolve_lecture_dir(lectures_dir: pathlib.Path, lecture_id: str) -> pathlib.Path:
    safe_id = validate_lecture_id(lecture_id)
    lecture_dir = (lectures_dir / safe_id).resolve()
    lectures_root = lectures_dir.resolve()
    if lecture_dir.parent != lectures_root:
        raise ValueError("Lecture id resolved outside lectures directory.")
    return lecture_dir


def default_lecture_config(lecture_id: str) -> dict:
    return {
        "lecture_id": lecture_id,
        "title": lecture_id.replace("_", " ").title(),
        "course": "",
        "active": True,
        "files": {},
        "topics": [],
    }


def load_lecture_config(lecture_dir: pathlib.Path) -> dict:
    config_path = lecture_dir / "lecture_config.json"
    if not config_path.exists():
        return default_lecture_config(lecture_dir.name)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    if "files" not in config or not isinstance(config["files"], dict):
        config["files"] = {}
    if "topics" not in config or not isinstance(config["topics"], list):
        config["topics"] = []
    config.setdefault("lecture_id", lecture_dir.name)
    config.setdefault("title", lecture_dir.name.replace("_", " ").title())
    config.setdefault("course", "")
    config.setdefault("active", True)
    return config


def save_lecture_config(lecture_dir: pathlib.Path, config: dict) -> pathlib.Path:
    config_path = lecture_dir / "lecture_config.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return config_path


def create_lecture_folder(lectures_dir: pathlib.Path, lecture_id: str, title: str, course: str) -> pathlib.Path:
    lecture_dir = resolve_lecture_dir(lectures_dir, lecture_id)
    lecture_dir.mkdir(parents=True, exist_ok=False)
    config = default_lecture_config(lecture_id)
    if title.strip():
        config["title"] = title.strip()
    if course.strip():
        config["course"] = course.strip()
    save_lecture_config(lecture_dir, config)
    return lecture_dir


def list_files(lecture_dir: pathlib.Path) -> list[LectureFileInfo]:
    infos = []
    for path in sorted(path for path in lecture_dir.iterdir() if path.is_file()):
        infos.append(LectureFileInfo(name=path.name, size_bytes=path.stat().st_size))
    return infos


def update_metadata(config: dict, *, title: str, course: str, active: bool) -> dict:
    updated = dict(config)
    updated["title"] = title.strip()
    updated["course"] = course.strip()
    updated["active"] = bool(active)
    return updated


def update_selected_sources(config: dict, selected: dict[str, str]) -> dict:
    updated = dict(config)
    files = dict(updated.get("files", {}))

    for key in SOURCE_KEYS:
        source_name = selected.get(key, "").strip()
        if source_name:
            files[key] = {
                "source": source_name,
                "target": TARGET_BY_KEY[key],
            }
        else:
            files.pop(key, None)

    if all(key in files for key in ("slides", "handout", "notebook", "transcript")):
        files["minutes"] = {"target": TARGET_BY_KEY["minutes"]}
        files["rubric"] = {"target": TARGET_BY_KEY["rubric"]}
    else:
        files.pop("minutes", None)
        files.pop("rubric", None)

    updated["files"] = files
    return updated


def save_uploaded_file(destination: pathlib.Path, uploaded_file: fa.UploadFile) -> pathlib.Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as buffer:
        shutil.copyfileobj(uploaded_file.file, buffer)
    return destination


def delete_file(lecture_dir: pathlib.Path, filename: str) -> None:
    target = (lecture_dir / filename).resolve()
    if target.parent != lecture_dir.resolve():
        raise ValueError("Refusing to delete files outside the lecture directory.")
    if target.name == "lecture_config.json":
        raise ValueError("lecture_config.json cannot be deleted from the admin app.")
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(filename)
    target.unlink()


def _copy_text_like_source(source: pathlib.Path, target: pathlib.Path) -> None:
    content = source.read_text(encoding="utf-8")
    if content and not content.endswith("\n"):
        content += "\n"
    target.write_text(content, encoding="utf-8")


def _convert_handout_source(source: pathlib.Path, target: pathlib.Path) -> None:
    suffix = source.suffix.lower()
    if suffix in {".qmd", ".md", ".txt"}:
        convert_qmd.convert_qmd_to_md(source, target)
        return
    if suffix == ".pdf":
        result = subprocess.run(
            ["pdftotext", "-layout", str(source), "-"],
            check=True,
            capture_output=True,
            text=True,
        )
        text = result.stdout
        if text and not text.endswith("\n"):
            text += "\n"
        target.write_text(text, encoding="utf-8")
        return
    raise ValueError("Handout source must be .qmd, .md, .txt, or .pdf")


def build_local_sources(lecture_dir: pathlib.Path, config: dict) -> list[str]:
    files = config.get("files", {})
    missing = [key for key in SOURCE_KEYS if key not in files]
    if missing:
        raise ValueError(f"Select source files for: {', '.join(missing)}")

    log_lines: list[str] = []
    for key in SOURCE_KEYS:
        source = lecture_dir / files[key]["source"]
        target = lecture_dir / files[key]["target"]
        if not source.exists():
            raise FileNotFoundError(files[key]["source"])
        target.parent.mkdir(parents=True, exist_ok=True)
        if key == "slides":
            convert_pptx.convert_pptx_to_md(source, target)
        elif key == "handout":
            _convert_handout_source(source, target)
        elif key == "notebook":
            convert_ipynb.convert_ipynb_to_md(source, target)
        elif key == "transcript":
            convert_vtt.convert_vtt_to_md(source, target)
        log_lines.append(f"{DISPLAY_LABELS[key]}: {source.name} -> {target.name}")
    return log_lines


def parse_topics_from_rubric(lecture_dir: pathlib.Path, config: dict) -> dict:
    files = dict(config.get("files", {}))
    rubric_info = files.get("rubric")
    if not rubric_info:
        return config
    rubric_path = lecture_dir / rubric_info["target"]
    if not rubric_path.exists():
        return config

    updated = dict(config)
    updated["topics"] = bot_engine.parse_rubric_topics(rubric_path.read_text(encoding="utf-8"))
    return updated


def current_step(config: dict, lecture_dir: pathlib.Path) -> str:
    files = config.get("files", {})
    if any(key not in files for key in SOURCE_KEYS):
        return "select_sources"
    if any(not (lecture_dir / files[key]["target"]).exists() for key in SOURCE_KEYS):
        return "build_local"
    if not (lecture_dir / TARGET_BY_KEY["minutes"]).exists():
        return "minutes"
    if not (lecture_dir / TARGET_BY_KEY["rubric"]).exists():
        return "rubric"
    return "complete"


def build_manual_prompt(stage: str) -> str:
    if stage == "minutes":
        base_prompt = prompt_loader.load_prompt_template("minutes_generation_prompt.md").strip()
        file_name = TARGET_BY_KEY["minutes"]
        return (
            "Please use the uploaded lecture files to complete the task below.\n\n"
            f"When you are done, produce the final result as a downloadable file named `{file_name}`.\n"
            "The file should contain only the requested final JSON content.\n\n"
            f"{base_prompt}\n"
        )
    if stage == "rubric":
        base_prompt = prompt_loader.load_prompt_template("master_rubric_generation_prompt.md").strip()
        file_name = TARGET_BY_KEY["rubric"]
        return (
            "Please use the uploaded lecture files to complete the task below.\n\n"
            f"When you are done, produce the final result as a downloadable file named `{file_name}`.\n"
            "The file should contain only the final markdown rubric.\n\n"
            f"{base_prompt}\n"
        )
    raise ValueError(f"Unsupported manual prompt stage: {stage}")


def required_bundle_files(stage: str) -> list[str]:
    if stage == "minutes":
        return [
            TARGET_BY_KEY["slides"],
            TARGET_BY_KEY["handout"],
            TARGET_BY_KEY["notebook"],
            TARGET_BY_KEY["transcript"],
        ]
    if stage == "rubric":
        return [
            TARGET_BY_KEY["slides"],
            TARGET_BY_KEY["handout"],
            TARGET_BY_KEY["notebook"],
            TARGET_BY_KEY["minutes"],
        ]
    raise ValueError(f"Unsupported bundle stage: {stage}")


def build_bundle_bytes(lecture_dir: pathlib.Path, stage: str) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename in required_bundle_files(stage):
            path = lecture_dir / filename
            if not path.exists():
                raise FileNotFoundError(filename)
            zf.write(path, arcname=filename)
    return output.getvalue()


def save_generated_artifact(lecture_dir: pathlib.Path, config: dict, kind: str, uploaded_file: fa.UploadFile) -> dict:
    if kind not in GENERATED_KEYS:
        raise ValueError(f"Unsupported generated artifact kind: {kind}")

    files = dict(config.get("files", {}))
    files.setdefault(kind, {"target": TARGET_BY_KEY[kind]})
    destination = lecture_dir / files[kind]["target"]
    save_uploaded_file(destination, uploaded_file)

    updated = dict(config)
    updated["files"] = files
    if kind == "rubric":
        updated = parse_topics_from_rubric(lecture_dir, updated)
    return updated


def lecture_summary(config: dict, lecture_dir: pathlib.Path) -> dict:
    files = config.get("files", {})
    selected_sources = {
        key: files.get(key, {}).get("source", "")
        for key in SOURCE_KEYS
    }
    generated_targets = {
        key: files.get(key, {}).get("target", TARGET_BY_KEY[key])
        for key in GENERATED_KEYS
    }
    processed_targets = {
        key: files.get(key, {}).get("target", TARGET_BY_KEY[key])
        for key in SOURCE_KEYS
    }
    processed_ready = {
        key: (lecture_dir / processed_targets[key]).exists()
        for key in SOURCE_KEYS
    }
    generated_ready = {
        key: (lecture_dir / generated_targets[key]).exists()
        for key in GENERATED_KEYS
    }
    return {
        "selected_sources": selected_sources,
        "processed_targets": processed_targets,
        "generated_targets": generated_targets,
        "processed_ready": processed_ready,
        "generated_ready": generated_ready,
        "current_step": current_step(config, lecture_dir),
    }
