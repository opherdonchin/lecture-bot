from __future__ import annotations

import argparse as ap_module
import json as j
import shutil as shutil_module
import sys as sys_module
from dataclasses import dataclass
import pathlib as pathlib_


SCRIPT_DIR = pathlib_.Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys_module.path:
    sys_module.path.insert(0, str(REPO_ROOT))

import scripts.convert_ipynb_to_md as convert_ipynb
import scripts.convert_pptx_to_md as convert_pptx
import scripts.convert_qmd_to_md as convert_qmd
import app.bot_engine as bot_engine


SUPPORTED_FILE_KEYS = ("slides", "handout", "notebook", "rubric")


@dataclass(frozen=True)
class BuildJob:
    logical_key: str
    source: pathlib_.Path
    target: pathlib_.Path


def resolve_lecture_dir(lecture_ref: str | pathlib_.Path, lectures_root: pathlib_.Path | None = None) -> pathlib_.Path:
    lectures_root = lectures_root or REPO_ROOT / "lectures"
    candidate = pathlib_.Path(lecture_ref)

    if candidate.is_dir():
        return candidate.resolve()

    lecture_dir = lectures_root / str(lecture_ref)
    if lecture_dir.is_dir():
        return lecture_dir.resolve()

    raise FileNotFoundError(f"Lecture directory not found for: {lecture_ref}")


def load_lecture_config(lecture_dir: pathlib_.Path) -> dict:
    config_path = lecture_dir / "lecture_config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Lecture config not found: {config_path}")

    config = j.loads(config_path.read_text(encoding="utf-8"))
    files = config.get("files")
    if not isinstance(files, dict):
        raise ValueError(f"Lecture config is missing a valid 'files' section: {config_path}")

    missing_keys = [key for key in SUPPORTED_FILE_KEYS if key not in files]
    if missing_keys:
        missing_text = ", ".join(missing_keys)
        raise ValueError(f"Lecture config is missing file definitions for: {missing_text}")

    unsupported_keys = [key for key in files if key not in SUPPORTED_FILE_KEYS]
    if unsupported_keys:
        unsupported_text = ", ".join(unsupported_keys)
        raise ValueError(f"Unsupported lecture file keys in config: {unsupported_text}")

    return config


def plan_build_jobs(lecture_dir: pathlib_.Path, config: dict) -> list[BuildJob]:
    jobs: list[BuildJob] = []

    for logical_key, file_config in config["files"].items():
        if not isinstance(file_config, dict):
            raise ValueError(f"Invalid file definition for '{logical_key}'")

        source_name = file_config.get("source")
        target_name = file_config.get("target")
        if not source_name or not target_name:
            raise ValueError(f"File definition for '{logical_key}' must include source and target")

        jobs.append(
            BuildJob(
                logical_key=logical_key,
                source=lecture_dir / source_name,
                target=lecture_dir / target_name,
            )
        )

    return jobs


def validate_jobs(jobs: list[BuildJob], force: bool) -> None:
    missing_sources = [str(job.source.name) for job in jobs if not job.source.exists()]
    if missing_sources:
        raise FileNotFoundError(
            f"Missing source files: {', '.join(sorted(missing_sources))}"
        )

    if force:
        return

    existing_targets = [
        str(job.target.name)
        for job in jobs
        if not (job.logical_key == "rubric" and job.source == job.target) and job.target.exists()
    ]
    if existing_targets:
        raise FileExistsError(
            "Refusing to overwrite existing target files without --force: "
            + ", ".join(sorted(existing_targets))
        )


def run_job(job: BuildJob) -> None:
    print(f"[{job.logical_key}] {job.source.name} -> {job.target.name}")

    if job.logical_key == "slides":
        convert_pptx.convert_pptx_to_md(job.source, job.target)
        return

    if job.logical_key == "handout":
        convert_qmd.convert_qmd_to_md(job.source, job.target)
        return

    if job.logical_key == "notebook":
        convert_ipynb.convert_ipynb_to_md(job.source, job.target)
        return

    if job.logical_key == "rubric":
        if job.source == job.target:
            return

        job.target.parent.mkdir(parents=True, exist_ok=True)
        shutil_module.copyfile(job.source, job.target)
        return

    raise ValueError(f"Unsupported lecture file key: {job.logical_key}")


def parse_topics_file(topics_path: pathlib_.Path) -> list[dict]:
    """Parse a topics.txt file into topic_defs.

    Each non-blank, non-comment line is one topic:
        <name>            (importance defaults to "core")
        <name> | <importance>

    Importance must be one of: core, important, brief.
    Topics are assigned IDs T1, T2, ... in file order.
    """
    valid_importance = {"core", "important", "brief"}
    topics = []
    for raw in topics_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            name, _, imp = line.partition("|")
            name = name.strip()
            imp = imp.strip().lower()
        else:
            name = line
            imp = "core"
        if imp not in valid_importance:
            imp = "core"
        if name:
            tid = f"T{len(topics) + 1}"
            topics.append({"topic_id": tid, "label": name, "importance": imp})
    return topics


def build_lecture_package(
    lecture_ref: str | pathlib_.Path,
    force: bool = False,
    lectures_root: pathlib_.Path | None = None,
) -> list[BuildJob]:
    lecture_dir = resolve_lecture_dir(lecture_ref, lectures_root=lectures_root)
    config = load_lecture_config(lecture_dir)
    jobs = plan_build_jobs(lecture_dir, config)
    validate_jobs(jobs, force=force)

    lecture_label = config.get("lecture_id", lecture_dir.name)
    print(f"Building lecture package for {lecture_label}")

    for job in jobs:
        run_job(job)

    # Resolve topics: topics.txt takes priority, then fall back to rubric parsing
    topics_txt = lecture_dir / "topics.txt"
    config_path = lecture_dir / "lecture_config.json"

    if topics_txt.exists():
        topic_defs = parse_topics_file(topics_txt)
        if topic_defs:
            config["topics"] = topic_defs
            config_path.write_text(j.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Wrote {len(topic_defs)} topics from topics.txt to lecture_config.json")
        else:
            print("Warning: topics.txt exists but contains no valid topics.")
    else:
        # Fall back: parse the built rubric for ### T1. headings
        rubric_job = next((jb for jb in jobs if jb.logical_key == "rubric"), None)
        rubric_path = rubric_job.target if rubric_job else lecture_dir / "rubric.md"
        if rubric_path.exists():
            topic_defs = bot_engine.parse_rubric_topics(rubric_path.read_text(encoding="utf-8"))
            if topic_defs:
                config["topics"] = topic_defs
                config_path.write_text(j.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"Wrote {len(topic_defs)} topics from rubric to lecture_config.json")
            else:
                print("Warning: no topics found. Add a topics.txt file to the lecture directory.")
                print("  Format: one topic per line, optionally 'name | importance'")

    print("Build complete")
    return jobs


def main(argv: list[str] | None = None) -> int:
    parser = ap_module.ArgumentParser(
        description="Build processed markdown files for a lecture package."
    )
    parser.add_argument(
        "lecture",
        help="Lecture id (for example lecture_01) or a lecture directory path",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing target files",
    )
    args = parser.parse_args(argv)

    try:
        build_lecture_package(args.lecture, force=args.force)
    except Exception as exc:
        print(f"Error: {exc}", file=sys_module.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
