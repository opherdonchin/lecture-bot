"""The lecture package handshake as commands on the server, run through scripts/lecture-package.

    scripts/lecture-package contract pml
    scripts/lecture-package check pml lecture_03 < lecture_03.zip
    scripts/lecture-package install pml lecture_03 [--replace] < lecture_03.zip

Each prints one JSON result and exits 0 if it is ok, 1 if not. See
docs/lecture_package_handshake.md.
"""

from __future__ import annotations

import argparse as ap_module
import json as j
import os as os_module
import pathlib as pathlib_
import re as re_module
import sys as sys_module


SCRIPT_DIR = pathlib_.Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys_module.path:
    sys_module.path.insert(0, str(REPO_ROOT))

import app.lecture_packages as lecture_packages


DEFAULT_INSTANCES_ROOT = "/srv/lecture-bot/instances"
COURSE_RE = re_module.compile(r"\A[a-z0-9_-]+\Z")


def instance_settings(course: str) -> tuple[pathlib_.Path, str]:
    """Return an instance's lectures folder and tutor prompt, reading only those two settings."""
    if not COURSE_RE.match(course):
        raise ValueError(f"{course!r} is not a valid course name.")
    root = pathlib_.Path(os_module.environ.get("LECTURE_BOT_INSTANCES_ROOT", DEFAULT_INSTANCES_ROOT))
    settings_file = root / course / "instance.env"
    wanted: dict[str, str] = {}
    try:
        lines = settings_file.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ValueError(f"Cannot read the settings of course {course!r}: {error.strerror}.") from error
    for line in lines:
        key, separator, value = line.strip().partition("=")
        if separator and key in {"LECTURES_DIR", "TUTOR_PROMPT_TEMPLATE"}:
            wanted[key] = value.strip().strip('"').strip("'")
    missing = {"LECTURES_DIR", "TUTOR_PROMPT_TEMPLATE"} - set(wanted)
    if missing:
        raise ValueError(f"The settings of course {course!r} do not set {', '.join(sorted(missing))}.")
    return pathlib_.Path(wanted["LECTURES_DIR"]), wanted["TUTOR_PROMPT_TEMPLATE"]


def run(args: ap_module.Namespace, stdin: bytes | None = None) -> dict:
    """Carry out one operation and return its result."""
    try:
        lectures_dir, prompt = instance_settings(args.course)
    except ValueError as error:
        return {"handshake": lecture_packages.HANDSHAKE_VERSION, "ok": False, "errors": [str(error)]}
    if args.operation == "contract":
        return lecture_packages.describe_expectations(prompt)
    data = sys_module.stdin.buffer.read() if stdin is None else stdin
    if args.operation == "check":
        return lecture_packages.check_archive(lectures_dir, args.lecture_id, data, prompt).to_dict()
    return lecture_packages.install_archive(lectures_dir, args.lecture_id, data, prompt, replace=args.replace).to_dict()


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    parser = ap_module.ArgumentParser(description=__doc__, formatter_class=ap_module.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="operation", required=True)
    contract_parser = sub.add_parser("contract", help="Show what the instance expects of a package.")
    contract_parser.add_argument("course")
    check_parser = sub.add_parser("check", help="Check a package .zip from stdin; installs nothing.")
    check_parser.add_argument("course")
    check_parser.add_argument("lecture_id")
    install_parser = sub.add_parser("install", help="Check a package .zip from stdin and install it, switched off.")
    install_parser.add_argument("course")
    install_parser.add_argument("lecture_id")
    install_parser.add_argument("--replace", action="store_true", help="Replace a lecture that is switched off.")

    result = run(parser.parse_args(argv))
    print(j.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
