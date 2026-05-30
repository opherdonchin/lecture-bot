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


def _write_submission_zip(path, *, generated_at: str):
    report = "\n".join(
        [
            "=== Lecture Bot Session Report ===",
            "Session ID: session-1",
            "Student ID: 206391179",
            "Lecture: lecture_01",
            "Grade: 85 / 100",
            "Session started: 2026-04-14T20:00:00+00:00",
            f"Report generated: {generated_at}",
            "--- Report ---",
            "Report body.",
        ]
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Student One_participant123_assignsubmission_file_/206391179_report.txt", report)


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
