#!/usr/bin/env python3
"""Generate a compact public-safe repository map for the ed-tech presentation."""

from __future__ import annotations

import pathlib as pathlib_


SCRIPT_PATH = pathlib_.Path(__file__).resolve()
PRESENTATION_DIR = SCRIPT_PATH.parents[1]
REPO_ROOT = SCRIPT_PATH.parents[3]
OUTPUT_PATH = PRESENTATION_DIR / "generated" / "repo_tree.txt"

DIRECTORY_SUMMARIES = [
    ("app/", "student/admin FastAPI apps, state, grading, templates, static UI"),
    ("docs/", "implementation, grading, tutor specification, runtime contracts"),
    ("prompts/", "runtime tutor prompt, generator, analysis and artifact prompts"),
    ("scripts/", "lecture-package build, conversion, export, Moodle helpers"),
    ("lectures/", "lecture package root; package contents excluded"),
    ("tests/", "pytest coverage for app, build pipeline, grading, routing"),
    ("presentations/", "Quarto presentation sources"),
    ("deploy/", "systemd deployment examples"),
]

ROOT_FILE_SUMMARIES = [
    ("README.md", "operational overview"),
    ("pixi.toml", "environment and task commands"),
]


def format_entry(name: str, summary: str, *, is_last: bool) -> str:
    connector = "`-- " if is_last else "|-- "
    return f"{connector}{name:<16} # {summary}"


def lecture_children() -> list[tuple[str, str]]:
    lectures_dir = REPO_ROOT / "lectures"
    if not lectures_dir.is_dir():
        return []
    entries: list[tuple[str, str]] = []
    config_path = lectures_dir / "config.json"
    if config_path.is_file():
        entries.append(("config.json", "runtime context defaults"))
    lecture_dirs = sorted(
        path
        for path in lectures_dir.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )
    entries.extend(
        (f"{path.name}/", "contents excluded")
        for path in lecture_dirs
    )
    return entries


def add_lecture_children(lines: list[str], prefix: str) -> None:
    children = lecture_children()
    for index, (name, summary) in enumerate(children):
        is_last = index == len(children) - 1
        connector = "`-- " if is_last else "|-- "
        lines.append(f"{prefix}{connector}{name:<16} # {summary}")


def main() -> int:
    lines = [
        "lecture-bot/",
        "# Compact public-safe orientation map.",
        "# Runtime databases, exports, logs, .env, Quarto render output, caches, and private lecture packages are excluded.",
    ]
    existing_entries = [
        (name, summary)
        for name, summary in DIRECTORY_SUMMARIES
        if (REPO_ROOT / name.rstrip("/")).is_dir()
    ]
    existing_entries.extend(
        (name, summary)
        for name, summary in ROOT_FILE_SUMMARIES
        if (REPO_ROOT / name).is_file()
    )
    for index, (name, summary) in enumerate(existing_entries):
        is_last = index == len(existing_entries) - 1
        lines.append(format_entry(name, summary, is_last=is_last))
        if name == "lectures/":
            add_lecture_children(lines, "    " if is_last else "|   ")
    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
