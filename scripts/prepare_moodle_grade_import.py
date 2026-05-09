from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app import moodle_grade_import


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Lecture Bot Moodle submission ZIPs and build one Moodle grade-import CSV."
    )
    parser.add_argument(
        "--submissions-dir",
        type=pathlib.Path,
        default=moodle_grade_import.DEFAULT_SUBMISSIONS_DIR,
        help="Directory containing <lecture_id>_submissions.zip files.",
    )
    parser.add_argument(
        "--participants",
        type=pathlib.Path,
        default=moodle_grade_import.DEFAULT_PARTICIPANTS_CSV,
        help="Moodle participants CSV export.",
    )
    parser.add_argument(
        "--db",
        type=pathlib.Path,
        default=moodle_grade_import.DEFAULT_DATABASE_PATH,
        help="Lecture Bot SQLite database.",
    )
    parser.add_argument(
        "--lecture",
        action="append",
        default=None,
        help="Lecture id to include. Repeat for multiple lectures. Defaults to all *_submissions.zip files.",
    )
    parser.add_argument(
        "--grade-item",
        action="append",
        default=[],
        metavar="LECTURE_ID=COLUMN",
        help="Moodle grade item column name for a lecture. Repeat as needed.",
    )
    parser.add_argument(
        "--deadline",
        action="append",
        default=[],
        metavar="LECTURE_ID=ISO_DATETIME",
        help="Reject reports generated after this deadline. Repeat as needed.",
    )
    parser.add_argument(
        "--upload-output",
        type=pathlib.Path,
        default=pathlib.Path("data/submissions/moodle_grade_import.csv"),
        help="Output Moodle grade-import CSV.",
    )
    parser.add_argument(
        "--report-output",
        type=pathlib.Path,
        default=pathlib.Path("data/submissions/moodle_grade_import_report.csv"),
        help="Output validation/report CSV.",
    )
    return parser.parse_args()


def parse_key_value(values: list[str], *, option_name: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"{option_name} expects LECTURE_ID=VALUE, got {value!r}.")
        key, item_value = value.split("=", 1)
        key = key.strip()
        item_value = item_value.strip()
        if not key or not item_value:
            raise ValueError(f"{option_name} expects non-empty LECTURE_ID=VALUE, got {value!r}.")
        parsed[key] = item_value
    return parsed


def parse_deadlines(values: list[str]) -> dict[str, dt.datetime]:
    raw_deadlines = parse_key_value(values, option_name="--deadline")
    deadlines: dict[str, dt.datetime] = {}
    for lecture_id, raw_deadline in raw_deadlines.items():
        normalized = raw_deadline
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        try:
            deadlines[lecture_id] = dt.datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(f"Invalid deadline for {lecture_id}: {raw_deadline!r}.") from exc
    return deadlines


def main() -> None:
    args = parse_args()
    try:
        grade_item_names = parse_key_value(args.grade_item, option_name="--grade-item")
        deadlines = parse_deadlines(args.deadline)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    archives = moodle_grade_import.discover_submission_archives(
        args.submissions_dir,
        lecture_ids=args.lecture,
    )
    result = moodle_grade_import.prepare_moodle_grade_import(
        submission_archives=archives,
        participants_csv_path=args.participants,
        db_path=args.db,
        grade_item_names=grade_item_names,
        deadlines=deadlines,
    )
    moodle_grade_import.write_grade_import_outputs(
        result,
        upload_csv_path=args.upload_output,
        report_csv_path=args.report_output,
    )

    print("Done.")
    for key, value in result.summary.items():
        print(f"{key}: {value}")
    print(f"upload_csv: {args.upload_output}")
    print(f"report_csv: {args.report_output}")


if __name__ == "__main__":
    main()
