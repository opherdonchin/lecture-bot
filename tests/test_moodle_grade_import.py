import csv
import datetime as dt
import sqlite3
import zipfile

from app import moodle_grade_import


def _write_participants(path):
    path.write_text(
        "ID number,Email address,First name,Last name,Groups\n"
        "206391179,student@example.com,Student,One,\n",
        encoding="utf-8",
    )


def _write_database(path, *, generated_at: str):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            create table sessions (
                session_id text primary key,
                student_id text,
                lecture_id text,
                current_grade real,
                started_at text
            )
            """
        )
        conn.execute(
            """
            create table grade_events (
                id integer primary key autoincrement,
                session_id text,
                event_type text,
                grade real,
                timestamp text
            )
            """
        )
        conn.execute(
            """
            insert into sessions (session_id, student_id, lecture_id, current_grade, started_at)
            values (?, ?, ?, ?, ?)
            """,
            ("session-1", "206391179", "lecture_01", 85.0, "2026-04-14T20:00:00+00:00"),
        )
        conn.execute(
            """
            insert into grade_events (session_id, event_type, grade, timestamp)
            values (?, ?, ?, ?)
            """,
            ("session-1", "report", 85.0, generated_at),
        )


def _write_submission_zip(path, *, generated_at: str, student_id: str = "206391179"):
    report = "\n".join(
        [
            "=== Lecture Bot Session Report ===",
            "Session ID: session-1",
            f"Student ID: {student_id}",
            "Lecture: lecture_01",
            "Grade: 85 / 100",
            "Session started: 2026-04-14T20:00:00+00:00",
            f"Report generated: {generated_at}",
            "--- Report ---",
            "Report body.",
        ]
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"Student One_participant123_assignsubmission_file_/{student_id}_lecture_01_report.txt", report)


def _report_text(
    *,
    session_id: str,
    student_id: str,
    lecture_id: str,
    grade: float,
    started_at: str,
    generated_at: str,
) -> str:
    return "\n".join(
        [
            "=== Lecture Bot Session Report ===",
            f"Session ID: {session_id}",
            f"Student ID: {student_id}",
            f"Lecture: {lecture_id}",
            f"Grade: {grade:g} / 100",
            f"Session started: {started_at}",
            f"Report generated: {generated_at}",
            "--- Report ---",
            "Report body.",
        ]
    )


def _write_multi_session_database(path, rows):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            create table sessions (
                session_id text primary key,
                student_id text,
                lecture_id text,
                current_grade real,
                started_at text
            )
            """
        )
        conn.execute(
            """
            create table grade_events (
                id integer primary key autoincrement,
                session_id text,
                event_type text,
                grade real,
                timestamp text
            )
            """
        )
        for row in rows:
            conn.execute(
                """
                insert into sessions (session_id, student_id, lecture_id, current_grade, started_at)
                values (?, ?, ?, ?, ?)
                """,
                (row["session_id"], row["student_id"], row["lecture_id"], row["grade"], row["started_at"]),
            )
            conn.execute(
                """
                insert into grade_events (session_id, event_type, grade, timestamp)
                values (?, ?, ?, ?)
                """,
                (row["session_id"], "report", row["grade"], row["generated_at"]),
            )


def _write_prefixed_student_database(path, *, generated_at: str):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            create table sessions (
                session_id text primary key,
                student_id text,
                lecture_id text,
                current_grade real,
                started_at text
            )
            """
        )
        conn.execute(
            """
            create table grade_events (
                id integer primary key autoincrement,
                session_id text,
                event_type text,
                grade real,
                timestamp text
            )
            """
        )
        conn.execute(
            """
            insert into sessions (session_id, student_id, lecture_id, current_grade, started_at)
            values (?, ?, ?, ?, ?)
            """,
            ("session-1", "student_206391179", "lecture_01", 85.0, "2026-04-14T20:00:00+00:00"),
        )
        conn.execute(
            """
            insert into grade_events (session_id, event_type, grade, timestamp)
            values (?, ?, ?, ?)
            """,
            ("session-1", "report", 85.0, generated_at),
        )


def test_deadline_classifies_late_report_without_rejecting(tmp_path):
    participants = tmp_path / "participants.csv"
    db_path = tmp_path / "lecture_bot.db"
    archive_path = tmp_path / "lecture_01_submissions.zip"
    generated_at = "2026-04-14T21:05:00+00:00"
    _write_participants(participants)
    _write_database(db_path, generated_at=generated_at)
    _write_submission_zip(archive_path, generated_at=generated_at)

    result = moodle_grade_import.prepare_moodle_grade_import(
        submission_archives={"lecture_01": archive_path},
        participants_csv_path=participants,
        db_path=db_path,
        deadlines={"lecture_01": dt.datetime.fromisoformat("2026-04-14T21:00:00+00:00")},
    )

    assert result.summary["accepted"] == 1
    assert result.summary["rejected"] == 0
    assert result.upload_columns == ["lecture_01", "lecture_01_on_time"]
    assert result.upload_rows == [{"ID number": "206391179", "lecture_01": "85", "lecture_01_on_time": "0"}]
    assert result.report_rows[0]["status"] == "accepted"
    assert result.report_rows[0]["on_time"] == "0"
    assert result.report_rows[0]["timing_status"] == "late"


def test_prefixed_student_id_matches_moodle_id_number(tmp_path):
    participants = tmp_path / "participants.csv"
    db_path = tmp_path / "lecture_bot.db"
    archive_path = tmp_path / "lecture_01_submissions.zip"
    generated_at = "2026-04-14T20:55:00+00:00"
    _write_participants(participants)
    _write_prefixed_student_database(db_path, generated_at=generated_at)
    _write_submission_zip(archive_path, generated_at=generated_at, student_id="student_206391179")

    result = moodle_grade_import.prepare_moodle_grade_import(
        submission_archives={"lecture_01": archive_path},
        participants_csv_path=participants,
        db_path=db_path,
    )

    assert result.summary["accepted"] == 1
    assert result.summary["rejected"] == 0
    assert result.upload_rows == [{"ID number": "206391179", "lecture_01": "85"}]
    assert result.report_rows[0]["student_id"] == "206391179"


def test_missing_deadline_omits_on_time_import_column(tmp_path):
    participants = tmp_path / "participants.csv"
    db_path = tmp_path / "lecture_bot.db"
    archive_path = tmp_path / "lecture_01_submissions.zip"
    generated_at = "2026-04-14T20:55:00+00:00"
    _write_participants(participants)
    _write_database(db_path, generated_at=generated_at)
    _write_submission_zip(archive_path, generated_at=generated_at)

    result = moodle_grade_import.prepare_moodle_grade_import(
        submission_archives={"lecture_01": archive_path},
        participants_csv_path=participants,
        db_path=db_path,
    )

    assert result.upload_columns == ["lecture_01"]
    assert result.upload_rows == [{"ID number": "206391179", "lecture_01": "85"}]
    assert result.report_rows[0]["on_time"] == ""
    assert result.report_rows[0]["timing_status"] == "deadline_missing"


def test_report_event_timestamp_allows_small_processing_delay(tmp_path):
    participants = tmp_path / "participants.csv"
    db_path = tmp_path / "lecture_bot.db"
    archive_path = tmp_path / "lecture_01_submissions.zip"
    _write_participants(participants)
    _write_database(db_path, generated_at="2026-04-14T20:55:24+00:00")
    _write_submission_zip(archive_path, generated_at="2026-04-14T20:55:00+00:00")

    result = moodle_grade_import.prepare_moodle_grade_import(
        submission_archives={"lecture_01": archive_path},
        participants_csv_path=participants,
        db_path=db_path,
    )

    assert result.summary["accepted"] == 1
    assert result.summary["rejected"] == 0
    assert result.report_rows[0]["status"] == "accepted"


def test_multi_lecture_zip_infers_lecture_columns_and_keeps_best_duplicate_grade(tmp_path):
    participants = tmp_path / "participants.csv"
    db_path = tmp_path / "lecture_bot.db"
    archive_path = tmp_path / "multi.zip"
    student_id = "206391179"
    started_at = "2026-04-14T20:00:00+00:00"
    rows = [
        {
            "session_id": "session-lecture-1",
            "student_id": student_id,
            "lecture_id": "lecture_01",
            "grade": 85.0,
            "started_at": started_at,
            "generated_at": "2026-04-14T20:55:00+00:00",
        },
        {
            "session_id": "session-lecture-2-low",
            "student_id": student_id,
            "lecture_id": "lecture_02",
            "grade": 70.0,
            "started_at": started_at,
            "generated_at": "2026-04-14T21:05:00+00:00",
        },
        {
            "session_id": "session-lecture-2-high",
            "student_id": student_id,
            "lecture_id": "lecture_02",
            "grade": 90.0,
            "started_at": started_at,
            "generated_at": "2026-04-14T20:45:00+00:00",
        },
    ]
    _write_participants(participants)
    _write_multi_session_database(db_path, rows)
    with zipfile.ZipFile(archive_path, "w") as archive:
        for row in rows:
            archive.writestr(
                f"Student One_participant123_assignsubmission_file_{student_id}_{row['lecture_id']}_{row['session_id']}_report.txt",
                _report_text(**row),
            )

    result = moodle_grade_import.prepare_moodle_grade_import(
        submission_archives={},
        multi_lecture_archives=[archive_path],
        participants_csv_path=participants,
        db_path=db_path,
    )

    assert result.summary["archives"] == 1
    assert result.summary["records"] == 3
    assert result.summary["accepted"] == 2
    assert result.summary["accepted_superseded"] == 1
    assert result.upload_columns == ["lecture_01", "lecture_02"]
    assert result.upload_rows == [{"ID number": student_id, "lecture_01": "85", "lecture_02": "90"}]
    superseded = [row for row in result.report_rows if row["status"] == "accepted_superseded"]
    assert superseded[0]["session_id"] == "session-lecture-2-low"


def test_write_grade_import_outputs_includes_deadline_audit_columns(tmp_path):
    result = moodle_grade_import.GradeImportResult(
        upload_rows=[{"ID number": "206391179", "lecture_01": "85", "lecture_01_on_time": "1"}],
        report_rows=[
            {
                "status": "accepted",
                "issue": "",
                "detail": "Validated.",
                "expected_lecture_id": "lecture_01",
                "lecture_id": "lecture_01",
                "student_id": "206391179",
                "participant_name": "Student One",
                "participant_email": "student@example.com",
                "session_id": "session-1",
                "submitted_grade": "85",
                "db_grade": "85",
                "deadline": "2026-04-14T21:00:00+00:00",
                "report_generated_at": "2026-04-14T20:55:00+00:00",
                "on_time": "1",
                "timing_status": "on_time",
                "source_zip": "lecture_01_submissions.zip",
                "source_file": "206391179_report.txt",
            }
        ],
        upload_columns=["lecture_01", "lecture_01_on_time"],
        summary={},
    )
    upload_path = tmp_path / "upload.csv"
    report_path = tmp_path / "report.csv"

    moodle_grade_import.write_grade_import_outputs(result, upload_csv_path=upload_path, report_csv_path=report_path)

    upload_rows = list(csv.DictReader(upload_path.open(encoding="utf-8")))
    report_rows = list(csv.DictReader(report_path.open(encoding="utf-8")))
    assert upload_rows[0]["lecture_01_on_time"] == "1"
    assert report_rows[0]["deadline"] == "2026-04-14T21:00:00+00:00"
    assert report_rows[0]["timing_status"] == "on_time"
