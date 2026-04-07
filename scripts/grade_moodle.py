"""grade_moodle.py — Validate Moodle submissions and produce a grade CSV.

Usage:
    python scripts/grade_moodle.py <moodle_zip> [options]

    Options:
      --deadline ISO   Reject sessions whose report was generated after this
                       datetime (e.g. "2026-04-14T23:59:00+03:00").
      --lecture ID     Only accept submissions for this lecture_id.
      --output PATH    Output CSV path (default: grades.csv in same dir as zip).
      --db PATH        Path to the SQLite DB file (default: data/lecture_bot.db).

Moodle zip structure expected (file submission):
    <StudentName>_<participant_id>_assignsubmission_file_/<filename>.txt

The report file must start with "=== Lecture Bot Session Report ===" and
contain "Key: Value" lines for Session ID, Student ID, Lecture, Grade,
Session started, and Report generated.

Output CSV columns:
    Identifier, Grade, Feedback comments

"Identifier" matches Moodle's participant folder id (e.g. "participant12345").
"""

import argparse
import csv
import datetime as dt
import pathlib
import re
import sqlite3
import sys
import tempfile
import zipfile

_HEADER = "=== Lecture Bot Session Report ==="
_FIELD_RE = re.compile(r"^([A-Za-z ]+):\s*(.+)$")


def parse_report_file(text: str) -> dict | None:
    """Parse a report text file into a dict of fields. Returns None if invalid."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != _HEADER:
        return None
    fields = {}
    for line in lines[1:]:
        if line.strip() == "--- Report ---":
            break
        m = _FIELD_RE.match(line.strip())
        if m:
            fields[m.group(1).strip().lower()] = m.group(2).strip()
    return fields if "session id" in fields else None


def find_report_files(zip_path: pathlib.Path) -> list[tuple[str, str]]:
    """Extract (participant_id, file_text) pairs from a Moodle submission zip."""
    results = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            # Moodle folder pattern: Anything_participantNNNN_assignsubmission_file_/
            m = re.search(r'_([a-zA-Z0-9]+)_assignsubmission_file_', name)
            if not m:
                continue
            participant_id = m.group(1)
            if name.endswith("/"):
                continue
            with zf.open(name) as f:
                try:
                    text = f.read().decode("utf-8")
                except UnicodeDecodeError:
                    text = f.read().decode("latin-1")
            results.append((participant_id, text))
    return results


def validate_submission(
    fields: dict,
    db_conn: sqlite3.Connection,
    deadline: dt.datetime | None,
    required_lecture: str | None,
) -> tuple[float | None, str]:
    """Validate a parsed report against the database.

    Returns (grade, comment). grade is None if rejected.
    """
    session_id = fields.get("session id", "").strip()
    if not session_id:
        return None, "REJECTED: No session ID in report."

    row = db_conn.execute(
        "SELECT student_id, lecture_id, current_grade, started_at FROM sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()

    if row is None:
        return None, f"REJECTED: Session ID {session_id!r} not found in database."

    db_student, db_lecture, db_grade, db_started_at = row

    # Check student ID
    submitted_student = fields.get("student id", "").strip()
    if submitted_student != db_student:
        return None, (
            f"REJECTED: Student ID mismatch — submitted {submitted_student!r}, "
            f"database has {db_student!r}."
        )

    # Check lecture
    if required_lecture and db_lecture != required_lecture:
        return None, (
            f"REJECTED: Lecture mismatch — session is for {db_lecture!r}, "
            f"expected {required_lecture!r}."
        )

    # Check submitted grade matches DB (allow ±1 for rounding)
    submitted_grade_str = fields.get("grade", "").split("/")[0].strip()
    try:
        submitted_grade = float(submitted_grade_str)
    except ValueError:
        return None, "REJECTED: Could not parse grade from report."

    if db_grade is None:
        return None, "REJECTED: No grade recorded in database for this session."

    if abs(submitted_grade - float(db_grade)) > 1.0:
        return None, (
            f"REJECTED: Grade mismatch — submitted {submitted_grade}, "
            f"database has {db_grade}."
        )

    # Check deadline
    if deadline:
        generated_str = fields.get("report generated", "").strip()
        try:
            generated_at = dt.datetime.fromisoformat(generated_str)
            if generated_at.tzinfo is None:
                generated_at = generated_at.replace(tzinfo=dt.timezone.utc)
            if generated_at > deadline:
                return None, (
                    f"REJECTED: Report generated at {generated_str} is after "
                    f"deadline {deadline.isoformat()}."
                )
        except ValueError:
            return None, f"REJECTED: Could not parse 'Report generated' timestamp: {generated_str!r}."

    return float(db_grade), f"Validated. Session: {session_id}. Lecture: {db_lecture}."


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Moodle submissions and produce grade CSV.")
    parser.add_argument("zip", type=pathlib.Path, help="Path to the Moodle submission zip.")
    parser.add_argument("--deadline", type=str, default=None, help="ISO deadline datetime.")
    parser.add_argument("--lecture", type=str, default=None, help="Required lecture ID.")
    parser.add_argument("--output", type=pathlib.Path, default=None, help="Output CSV path.")
    parser.add_argument("--db", type=pathlib.Path, default=pathlib.Path("data/lecture_bot.db"),
                        help="Path to SQLite DB.")
    args = parser.parse_args()

    zip_path: pathlib.Path = args.zip
    if not zip_path.exists():
        print(f"Error: zip file not found: {zip_path}", file=sys.stderr)
        sys.exit(1)

    db_path: pathlib.Path = args.db
    if not db_path.exists():
        print(f"Error: database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    deadline: dt.datetime | None = None
    if args.deadline:
        try:
            deadline = dt.datetime.fromisoformat(args.deadline)
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=dt.timezone.utc)
        except ValueError:
            print(f"Error: invalid deadline datetime: {args.deadline!r}", file=sys.stderr)
            sys.exit(1)

    output_path: pathlib.Path = args.output or zip_path.with_name(zip_path.stem + "_grades.csv")

    db_conn = sqlite3.connect(db_path)
    try:
        submissions = find_report_files(zip_path)
    except zipfile.BadZipFile:
        print(f"Error: not a valid zip file: {zip_path}", file=sys.stderr)
        sys.exit(1)

    if not submissions:
        print("Warning: no submission files found in zip.", file=sys.stderr)

    rows = []
    accepted = rejected = 0
    for participant_id, text in submissions:
        fields = parse_report_file(text)
        if fields is None:
            grade, comment = None, "REJECTED: File is not a valid Lecture Bot report."
        else:
            grade, comment = validate_submission(fields, db_conn, deadline, args.lecture)

        if grade is not None:
            accepted += 1
        else:
            rejected += 1

        rows.append({
            "Identifier": participant_id,
            "Grade": "" if grade is None else str(int(round(grade))),
            "Feedback comments": comment,
        })

    db_conn.close()

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Identifier", "Grade", "Feedback comments"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done. {accepted} accepted, {rejected} rejected → {output_path}")


if __name__ == "__main__":
    main()
