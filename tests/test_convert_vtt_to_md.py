from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts import convert_vtt_to_md


def test_convert_vtt_to_md_strips_webvtt_noise(tmp_path: Path) -> None:
    source = tmp_path / "lecture.vtt"
    target = tmp_path / "transcript.md"
    source.write_text(
        "WEBVTT\n\n"
        "NOTE automated captions\n\n"
        "1\n"
        "00:00:01.000 --> 00:00:03.000\n"
        "<v Prof>Hello class</v>\n\n"
        "2\n"
        "00:00:03.000 --> 00:00:05.000\n"
        "Hello class\n\n"
        "3\n"
        "00:00:05.000 --> 00:00:07.000\n"
        "Today we compare prior and likelihood.\n",
        encoding="utf-8",
    )

    convert_vtt_to_md.convert_vtt_to_md(source, target)

    rendered = target.read_text(encoding="utf-8")
    assert rendered.startswith("# Transcript")
    assert "WEBVTT" not in rendered
    assert "NOTE automated captions" not in rendered
    assert rendered.count("Hello class") == 1
    assert "[00:00:05.000 - 00:00:07.000] Today we compare prior and likelihood." in rendered
