from __future__ import annotations

import csv
import dataclasses
import datetime as dt
import pathlib
import re
import sqlite3
import zipfile
from collections.abc import Mapping, Sequence


DEFAULT_SUBMISSIONS_DIR = pathlib.Path("data/submissions")
DEFAULT_PARTICIPANTS_CSV = DEFAULT_SUBMISSIONS_DIR / "courseid_64733_participants.csv"
DEFAULT_DATABASE_PATH = pathlib.Path("data/lecture_bot.db")

REPORT_HEADER = "=== Lecture Bot Session Report ==="
REPORT_FIELD_RE = re.compile(r"^([A-Za-z ]+):\s*(.+)$")
SUBMISSION_FILENAME_RE = re.compile(r"_([^_/]+)_assignsubmission_file_/?([^/]*)")
STUDENT_ID_IN_REPORT_FILENAME_RE = re.compile(r"^([0-9]+)_")
PREFIXED_STUDENT_ID_RE = re.compile(r"^student_([0-9]+)$")


@dataclasses.dataclass(frozen=True)
class Participant:
    idnumber: str
    emailaddress: str
    firstname: str
    lastname: str
    groups: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.firstname} {self.lastname}".strip()


@dataclasses.dataclass(frozen=True)
class SubmissionRecord:
    source_zip: str
    source_file: str
    expected_lecture_id: str
    moodle_submission_id: str
    filename_student_id: str
    report_fields: dict[str, str]

    @property
    def session_id(self) -> str:
        return self.report_fields.get("session id", "")

    @property
    def student_id(self) -> str:
        return self.report_fields.get("student id", "")

    @property
    def moodle_student_id(self) -> str:
        return _moodle_student_id(self.student_id)

    @property
    def lecture_id(self) -> str:
        return self.report_fields.get("lecture", "")

    @property
    def submitted_grade(self) -> float | None:
        raw_grade = self.report_fields.get("grade", "").split("/")[0].strip()
        try:
            return float(raw_grade)
        except ValueError:
            return None


@dataclasses.dataclass(frozen=True)
class GradeImportResult:
    upload_rows: list[dict[str, str]]
    report_rows: list[dict[str, str]]
    upload_columns: list[str]
    summary: dict[str, int]


def default_submission_zip_name(lecture_id: str) -> str:
    return f"{lecture_id}_submissions.zip"


def default_submission_zip_path(submissions_dir: pathlib.Path, lecture_id: str) -> pathlib.Path:
    return submissions_dir / default_submission_zip_name(lecture_id)


def discover_submission_archives(
    submissions_dir: pathlib.Path = DEFAULT_SUBMISSIONS_DIR,
    lecture_ids: Sequence[str] | None = None,
) -> dict[str, pathlib.Path]:
    if lecture_ids is not None:
        return {
            lecture_id: default_submission_zip_path(submissions_dir, lecture_id)
            for lecture_id in lecture_ids
        }

    archives: dict[str, pathlib.Path] = {}
    for path in sorted(submissions_dir.glob("*_submissions.zip")):
        lecture_id = path.name.removesuffix("_submissions.zip")
        if lecture_id:
            archives[lecture_id] = path
    return archives


def load_participants_csv(path: pathlib.Path = DEFAULT_PARTICIPANTS_CSV) -> dict[str, Participant]:
    participants: dict[str, Participant] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            participant = Participant(
                idnumber=(row.get("ID number") or "").strip(),
                emailaddress=(row.get("Email address") or "").strip(),
                firstname=(row.get("First name") or "").strip(),
                lastname=(row.get("Last name") or "").strip(),
                groups=(row.get("Groups") or "").strip(),
            )
            if participant.idnumber:
                participants[participant.idnumber] = participant
    return participants


def load_deadlines_csv(path: pathlib.Path) -> dict[str, dt.datetime]:
    if not path.exists():
        return {}

    deadlines: dict[str, dt.datetime] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return {}
        normalized_fieldnames = {field.strip().lower() for field in reader.fieldnames}
        required_fields = {"lecture_id", "deadline"}
        missing_fields = required_fields - normalized_fieldnames
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(f"Deadline CSV is missing required column(s): {missing}.")

        for row_number, row in enumerate(reader, start=2):
            normalized_row = {
                key.strip().lower(): value
                for key, value in row.items()
                if key is not None
            }
            lecture_id = (normalized_row.get("lecture_id") or "").strip()
            raw_deadline = (normalized_row.get("deadline") or "").strip()
            if not lecture_id and not raw_deadline:
                continue
            if not lecture_id or not raw_deadline:
                raise ValueError(f"Deadline CSV row {row_number} must include both lecture_id and deadline.")
            deadline = _parse_datetime(raw_deadline)
            if deadline is None:
                raise ValueError(f"Deadline CSV row {row_number} has invalid ISO datetime {raw_deadline!r}.")
            deadlines[lecture_id] = deadline
    return deadlines


def build_deadline_template_rows(
    lecture_ids: Sequence[str],
    existing_deadlines: Mapping[str, dt.datetime] | None = None,
) -> list[dict[str, str]]:
    existing_deadlines = existing_deadlines or {}
    return [
        {
            "lecture_id": lecture_id,
            "deadline": _format_datetime(existing_deadlines[lecture_id]) if lecture_id in existing_deadlines else "",
        }
        for lecture_id in sorted(lecture_ids)
    ]


def parse_report_text(text: str) -> dict[str, str] | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != REPORT_HEADER:
        return None

    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "--- Report ---":
            break
        match = REPORT_FIELD_RE.match(line.strip())
        if match:
            fields[match.group(1).strip().lower()] = match.group(2).strip()
    return fields if fields.get("session id") else None


def read_submission_records(
    submission_archives: Mapping[str, pathlib.Path],
) -> tuple[list[SubmissionRecord], list[dict[str, str]]]:
    records: list[SubmissionRecord] = []
    difficulties: list[dict[str, str]] = []
    for expected_lecture_id, archive_path in sorted(submission_archives.items()):
        if not archive_path.exists():
            difficulties.append(
                _difficulty_row(
                    source_zip=str(archive_path),
                    source_file="",
                    expected_lecture_id=expected_lecture_id,
                    issue="archive_missing",
                    detail=f"Archive not found: {archive_path}",
                )
            )
            continue

        try:
            zip_handle = zipfile.ZipFile(archive_path)
        except zipfile.BadZipFile:
            difficulties.append(
                _difficulty_row(
                    source_zip=str(archive_path),
                    source_file="",
                    expected_lecture_id=expected_lecture_id,
                    issue="archive_not_zip",
                    detail=f"Not a valid zip file: {archive_path}",
                )
            )
            continue

        with zip_handle:
            for member_name in zip_handle.namelist():
                if member_name.endswith("/"):
                    continue
                match = SUBMISSION_FILENAME_RE.search(member_name)
                if not match:
                    difficulties.append(
                        _difficulty_row(
                            source_zip=str(archive_path),
                            source_file=member_name,
                            expected_lecture_id=expected_lecture_id,
                            issue="filename_unrecognized",
                            detail="Could not locate Moodle assignsubmission_file marker.",
                        )
                    )
                    continue

                moodle_submission_id, submitted_filename = match.groups()
                filename_student_id = _student_id_from_uploaded_filename(submitted_filename)
                try:
                    text = zip_handle.read(member_name).decode("utf-8-sig")
                except UnicodeDecodeError:
                    text = zip_handle.read(member_name).decode("latin-1", errors="replace")

                fields = parse_report_text(text)
                if fields is None:
                    difficulties.append(
                        _difficulty_row(
                            source_zip=str(archive_path),
                            source_file=member_name,
                            expected_lecture_id=expected_lecture_id,
                            issue="report_header_invalid",
                            detail="File is not a valid Lecture Bot session report.",
                        )
                    )
                    continue

                records.append(
                    SubmissionRecord(
                        source_zip=str(archive_path),
                        source_file=member_name,
                        expected_lecture_id=expected_lecture_id,
                        moodle_submission_id=moodle_submission_id,
                        filename_student_id=filename_student_id,
                        report_fields=fields,
                    )
                )
    return records, difficulties


def prepare_moodle_grade_import(
    *,
    submission_archives: Mapping[str, pathlib.Path],
    participants_csv_path: pathlib.Path = DEFAULT_PARTICIPANTS_CSV,
    db_path: pathlib.Path = DEFAULT_DATABASE_PATH,
    grade_item_names: Mapping[str, str] | None = None,
    deadlines: Mapping[str, dt.datetime] | None = None,
    grade_tolerance: float = 1.0,
    report_event_tolerance_seconds: float = 30.0,
) -> GradeImportResult:
    participants = load_participants_csv(participants_csv_path)
    records, difficulties = read_submission_records(submission_archives)
    grade_item_names = grade_item_names or {}
    deadlines = deadlines or {}

    report_rows: list[dict[str, str]] = list(difficulties)
    accepted_records: list[SubmissionRecord] = []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        for record in records:
            validation = _validate_record(
                record,
                conn=conn,
                participants=participants,
                deadline=deadlines.get(record.expected_lecture_id),
                grade_tolerance=grade_tolerance,
                report_event_tolerance_seconds=report_event_tolerance_seconds,
            )
            report_rows.append(validation)
            if validation["status"] == "accepted":
                accepted_records.append(record)

    chosen_records, superseded_keys = _choose_records_for_upload(accepted_records)
    for row in report_rows:
        key = (row.get("student_id", ""), row.get("lecture_id", ""), row.get("session_id", ""))
        if key in superseded_keys:
            row["status"] = "accepted_superseded"
            row["issue"] = "duplicate_submission"
            row["detail"] = "Another accepted submission for the same student and lecture was newer."

    lecture_ids = sorted(submission_archives)
    upload_columns = _build_upload_columns(
        lecture_ids=lecture_ids,
        grade_item_names=grade_item_names,
        deadline_lecture_ids=set(deadlines),
    )
    upload_rows = _build_upload_rows(
        chosen_records=chosen_records,
        participants=participants,
        lecture_ids=lecture_ids,
        grade_item_names=grade_item_names,
        deadlines=deadlines,
    )
    summary = {
        "participants": len(participants),
        "archives": len(submission_archives),
        "records": len(records),
        "accepted": sum(1 for row in report_rows if row["status"] == "accepted"),
        "accepted_superseded": sum(1 for row in report_rows if row["status"] == "accepted_superseded"),
        "rejected": sum(1 for row in report_rows if row["status"] == "rejected"),
        "difficulties": len(difficulties),
        "upload_rows": len(upload_rows),
    }
    return GradeImportResult(
        upload_rows=upload_rows,
        report_rows=report_rows,
        upload_columns=upload_columns,
        summary=summary,
    )


def write_grade_import_outputs(
    result: GradeImportResult,
    *,
    upload_csv_path: pathlib.Path,
    report_csv_path: pathlib.Path,
) -> None:
    upload_csv_path.parent.mkdir(parents=True, exist_ok=True)
    report_csv_path.parent.mkdir(parents=True, exist_ok=True)

    upload_fields = ["ID number", *result.upload_columns]
    with upload_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=upload_fields)
        writer.writeheader()
        writer.writerows(result.upload_rows)

    report_fields = [
        "status",
        "issue",
        "detail",
        "expected_lecture_id",
        "lecture_id",
        "student_id",
        "participant_name",
        "participant_email",
        "session_id",
        "submitted_grade",
        "db_grade",
        "deadline",
        "report_generated_at",
        "on_time",
        "timing_status",
        "source_zip",
        "source_file",
    ]
    with report_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=report_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(result.report_rows)


def _difficulty_row(
    *,
    source_zip: str,
    source_file: str,
    expected_lecture_id: str,
    issue: str,
    detail: str,
) -> dict[str, str]:
    return {
        "status": "rejected",
        "issue": issue,
        "detail": detail,
        "expected_lecture_id": expected_lecture_id,
        "lecture_id": "",
        "student_id": "",
        "participant_name": "",
        "participant_email": "",
        "session_id": "",
        "submitted_grade": "",
        "db_grade": "",
        "deadline": "",
        "report_generated_at": "",
        "on_time": "",
        "timing_status": "",
        "source_zip": source_zip,
        "source_file": source_file,
    }


def _student_id_from_uploaded_filename(filename: str) -> str:
    match = STUDENT_ID_IN_REPORT_FILENAME_RE.match(filename)
    return match.group(1) if match else ""


def _moodle_student_id(student_id: str) -> str:
    normalized = student_id.strip()
    match = PREFIXED_STUDENT_ID_RE.match(normalized)
    return match.group(1) if match else normalized


def _validate_record(
    record: SubmissionRecord,
    *,
    conn: sqlite3.Connection,
    participants: Mapping[str, Participant],
    deadline: dt.datetime | None,
    grade_tolerance: float,
    report_event_tolerance_seconds: float,
) -> dict[str, str]:
    moodle_student_id = record.moodle_student_id
    participant = participants.get(moodle_student_id)
    base = {
        "status": "accepted",
        "issue": "",
        "detail": "Validated.",
        "expected_lecture_id": record.expected_lecture_id,
        "lecture_id": record.lecture_id,
        "student_id": moodle_student_id,
        "participant_name": participant.full_name if participant else "",
        "participant_email": participant.emailaddress if participant else "",
        "session_id": record.session_id,
        "submitted_grade": "" if record.submitted_grade is None else _format_grade(record.submitted_grade),
        "db_grade": "",
        "deadline": _format_datetime(deadline) if deadline is not None else "",
        "report_generated_at": record.report_fields.get("report generated", ""),
        "on_time": "",
        "timing_status": "deadline_missing" if deadline is None else "",
        "source_zip": record.source_zip,
        "source_file": record.source_file,
    }

    if record.submitted_grade is None:
        return _reject(base, "grade_unparseable", "Could not parse Grade field.")
    if not moodle_student_id:
        return _reject(base, "student_id_missing", "Report did not contain a Student ID.")
    if participant is None:
        return _reject(base, "participant_missing", "Student ID is not present in participant CSV.")
    if record.filename_student_id and record.filename_student_id != moodle_student_id:
        return _reject(
            base,
            "filename_student_mismatch",
            f"Filename student ID {record.filename_student_id!r} does not match report ID {record.student_id!r}.",
        )
    if record.lecture_id != record.expected_lecture_id:
        return _reject(
            base,
            "lecture_archive_mismatch",
            f"Report lecture {record.lecture_id!r} was submitted in archive {record.expected_lecture_id!r}.",
        )

    session_row = conn.execute(
        """
        select student_id, lecture_id, current_grade, started_at
        from sessions
        where session_id = ?
        """,
        (record.session_id,),
    ).fetchone()
    if session_row is None:
        return _reject(base, "session_missing", "Session ID was not found in the database.")

    base["db_grade"] = "" if session_row["current_grade"] is None else _format_grade(float(session_row["current_grade"]))
    if _moodle_student_id(session_row["student_id"]) != moodle_student_id:
        return _reject(
            base,
            "db_student_mismatch",
            f"Database student ID {session_row['student_id']!r} does not match report ID {record.student_id!r}.",
        )
    if session_row["lecture_id"] != record.lecture_id:
        return _reject(
            base,
            "db_lecture_mismatch",
            f"Database lecture {session_row['lecture_id']!r} does not match report lecture {record.lecture_id!r}.",
        )
    if session_row["current_grade"] is None:
        return _reject(base, "db_grade_missing", "Session has no current grade in the database.")
    if abs(record.submitted_grade - float(session_row["current_grade"])) > grade_tolerance:
        return _reject(
            base,
            "grade_mismatch",
            f"Report grade {record.submitted_grade} does not match database grade {session_row['current_grade']}.",
        )

    start_check = _check_started_at(record, session_row["started_at"])
    if start_check:
        return _reject(base, "started_at_mismatch", start_check)

    timing_fields, generated_check = _check_report_generated_at(
        record,
        conn=conn,
        deadline=deadline,
        tolerance_seconds=report_event_tolerance_seconds,
    )
    base.update(timing_fields)
    if generated_check:
        return _reject(base, generated_check[0], generated_check[1])

    return base


def _reject(row: dict[str, str], issue: str, detail: str) -> dict[str, str]:
    return {**row, "status": "rejected", "issue": issue, "detail": detail}


def _check_started_at(record: SubmissionRecord, db_started_at: str) -> str:
    report_started_raw = record.report_fields.get("session started", "")
    report_started = _parse_datetime(report_started_raw)
    db_started = _parse_datetime(db_started_at)
    if report_started is None:
        return f"Could not parse Session started timestamp {report_started_raw!r}."
    if db_started is None:
        return f"Could not parse database started_at timestamp {db_started_at!r}."
    if abs((_to_utc_naive(report_started) - _to_utc_naive(db_started)).total_seconds()) > 1.0:
        return f"Report start {report_started_raw!r} does not match database start {db_started_at!r}."
    return ""


def _check_report_generated_at(
    record: SubmissionRecord,
    *,
    conn: sqlite3.Connection,
    deadline: dt.datetime | None,
    tolerance_seconds: float,
) -> tuple[dict[str, str], tuple[str, str] | None]:
    generated_raw = record.report_fields.get("report generated", "")
    timing_fields = {
        "deadline": _format_datetime(deadline) if deadline is not None else "",
        "report_generated_at": generated_raw,
        "on_time": "",
        "timing_status": "deadline_missing" if deadline is None else "",
    }
    generated_at = _parse_datetime(generated_raw)
    if generated_at is None:
        return timing_fields, (
            "report_generated_unparseable",
            f"Could not parse Report generated timestamp {generated_raw!r}.",
        )

    if deadline is not None:
        on_time = _to_utc_naive(generated_at) <= _to_utc_naive(deadline)
        timing_fields["on_time"] = "1" if on_time else "0"
        timing_fields["timing_status"] = "on_time" if on_time else "late"

    event_rows = conn.execute(
        """
        select timestamp
        from grade_events
        where session_id = ? and event_type = 'report'
        """,
        (record.session_id,),
    ).fetchall()
    event_times = [
        _parse_datetime(event_row["timestamp"])
        for event_row in event_rows
    ]
    event_times = [event_time for event_time in event_times if event_time is not None]
    if not event_times:
        return timing_fields, ("report_event_missing", "No report grade event was found for this session.")

    best_delta = min(
        abs((_to_utc_naive(event_time) - _to_utc_naive(generated_at)).total_seconds())
        for event_time in event_times
    )
    if best_delta > tolerance_seconds:
        return timing_fields, (
            "report_event_time_mismatch",
            f"Nearest database report event is {best_delta:.1f} seconds from Report generated.",
        )
    return timing_fields, None


def _build_upload_columns(
    *,
    lecture_ids: Sequence[str],
    grade_item_names: Mapping[str, str],
    deadline_lecture_ids: set[str],
) -> list[str]:
    columns: list[str] = []
    for lecture_id in lecture_ids:
        grade_column = grade_item_names.get(lecture_id, lecture_id)
        columns.append(grade_column)
        if lecture_id in deadline_lecture_ids:
            columns.append(_on_time_column_name(grade_column))
    return columns


def _choose_records_for_upload(
    records: Sequence[SubmissionRecord],
) -> tuple[dict[tuple[str, str], SubmissionRecord], set[tuple[str, str, str]]]:
    by_student_lecture: dict[tuple[str, str], SubmissionRecord] = {}
    superseded: set[tuple[str, str, str]] = set()
    for record in records:
        key = (record.moodle_student_id, record.lecture_id)
        existing = by_student_lecture.get(key)
        if existing is None:
            by_student_lecture[key] = record
            continue

        existing_time = _parse_datetime(existing.report_fields.get("report generated", ""))
        record_time = _parse_datetime(record.report_fields.get("report generated", ""))
        if existing_time is not None and record_time is not None and _to_utc_naive(record_time) > _to_utc_naive(existing_time):
            superseded.add((existing.moodle_student_id, existing.lecture_id, existing.session_id))
            by_student_lecture[key] = record
        else:
            superseded.add((record.moodle_student_id, record.lecture_id, record.session_id))
    return by_student_lecture, superseded


def _build_upload_rows(
    *,
    chosen_records: Mapping[tuple[str, str], SubmissionRecord],
    participants: Mapping[str, Participant],
    lecture_ids: Sequence[str],
    grade_item_names: Mapping[str, str],
    deadlines: Mapping[str, dt.datetime],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    student_ids = sorted({student_id for student_id, _lecture_id in chosen_records})
    for student_id in student_ids:
        if student_id not in participants:
            continue
        row = {"ID number": student_id}
        for lecture_id in lecture_ids:
            column = grade_item_names.get(lecture_id, lecture_id)
            record = chosen_records.get((student_id, lecture_id))
            row[column] = "" if record is None or record.submitted_grade is None else _format_grade(record.submitted_grade)
            if lecture_id in deadlines:
                row[_on_time_column_name(column)] = "" if record is None else _on_time_value(record, deadlines[lecture_id])
        rows.append(row)
    return rows


def _on_time_column_name(grade_column: str) -> str:
    return f"{grade_column}_on_time"


def _on_time_value(record: SubmissionRecord, deadline: dt.datetime) -> str:
    generated_at = _parse_datetime(record.report_fields.get("report generated", ""))
    if generated_at is None:
        return ""
    return "1" if _to_utc_naive(generated_at) <= _to_utc_naive(deadline) else "0"


def _parse_datetime(value: str) -> dt.datetime | None:
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        return dt.datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _to_utc_naive(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(dt.timezone.utc).replace(tzinfo=None)


def _format_grade(grade: float) -> str:
    if grade.is_integer():
        return str(int(grade))
    return f"{grade:.2f}".rstrip("0").rstrip(".")


def _format_datetime(value: dt.datetime) -> str:
    return value.isoformat()
