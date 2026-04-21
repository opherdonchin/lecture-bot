from __future__ import annotations

import argparse as ap_module
import html as html_module
import pathlib as pathlib_
import re as re_module
from dataclasses import dataclass


_TIMESTAMP_RE = re_module.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2}(?:\.\d{3})?)\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2}(?:\.\d{3})?)"
)
_TAG_RE = re_module.compile(r"<[^>]+>")


@dataclass(frozen=True)
class Cue:
    start: str
    end: str
    text: str


def _clean_text(text: str) -> str:
    unescaped = html_module.unescape(text)
    without_tags = _TAG_RE.sub("", unescaped)
    collapsed = " ".join(without_tags.split())
    return collapsed.strip()


def parse_vtt(text: str) -> list[Cue]:
    blocks = re_module.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n"))
    cues: list[Cue] = []
    previous_text = ""

    for raw_block in blocks:
        lines = [line.strip("\ufeff") for line in raw_block.split("\n") if line.strip()]
        if not lines:
            continue
        if lines[0] == "WEBVTT":
            continue
        if lines[0].startswith(("NOTE", "STYLE", "REGION")):
            continue

        timestamp_index = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timestamp_index is None:
            continue

        match = _TIMESTAMP_RE.search(lines[timestamp_index])
        if not match:
            continue

        text_lines = [_clean_text(line) for line in lines[timestamp_index + 1 :]]
        cue_text = " ".join(line for line in text_lines if line).strip()
        if not cue_text or cue_text == previous_text:
            continue

        previous_text = cue_text
        cues.append(
            Cue(
                start=match.group("start"),
                end=match.group("end"),
                text=cue_text,
            )
        )

    return cues


def render_transcript_markdown(cues: list[Cue]) -> str:
    lines = ["# Transcript", ""]

    if not cues:
        lines.append("_No transcript cues were parsed from the WebVTT file._")
        lines.append("")
        return "\n".join(lines)

    for cue in cues:
        lines.append(f"- [{cue.start} - {cue.end}] {cue.text}")

    lines.append("")
    return "\n".join(lines)


def convert_vtt_to_md(source: str | pathlib_.Path, target: str | pathlib_.Path) -> pathlib_.Path:
    source_path = pathlib_.Path(source)
    target_path = pathlib_.Path(target)

    if not source_path.exists():
        raise FileNotFoundError(f"VTT source file not found: {source_path}")

    cues = parse_vtt(source_path.read_text(encoding="utf-8"))
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(render_transcript_markdown(cues), encoding="utf-8")
    return target_path


def main(argv: list[str] | None = None) -> int:
    parser = ap_module.ArgumentParser(description="Convert a WebVTT transcript to markdown.")
    parser.add_argument("source", help="Path to the source .vtt file")
    parser.add_argument("target", help="Path to the output .md file")
    args = parser.parse_args(argv)

    try:
        convert_vtt_to_md(args.source, args.target)
    except Exception as exc:
        parser.exit(1, f"Error: {exc}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
