from __future__ import annotations

import argparse
import sys
from pathlib import Path


def strip_front_matter(text: str) -> str:
    if text.startswith("\ufeff"):
        text = text[1:]

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() in {"---", "..."}:
            return "".join(lines[index + 1 :]).lstrip("\n")

    return text


def convert_qmd_to_md(source: str | Path, target: str | Path) -> Path:
    source_path = Path(source)
    target_path = Path(target)

    if not source_path.exists():
        raise FileNotFoundError(f"Quarto source file not found: {source_path}")

    content = source_path.read_text(encoding="utf-8")
    markdown = strip_front_matter(content)
    if markdown and not markdown.endswith("\n"):
        markdown += "\n"

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(markdown, encoding="utf-8")
    return target_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert a Quarto markdown file to markdown.")
    parser.add_argument("source", help="Path to the source .qmd file")
    parser.add_argument("target", help="Path to the target .md file")
    args = parser.parse_args(argv)

    try:
        convert_qmd_to_md(args.source, args.target)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
