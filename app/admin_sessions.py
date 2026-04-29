from __future__ import annotations

import datetime as dt
import io
import json
import pathlib
import sqlite3
import uuid
import zipfile
from dataclasses import dataclass
from typing import Iterable

import sqlalchemy as sa
import sqlalchemy.orm as sqlalchemy_orm

import app.models as models
from scripts import export_session_package


DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 200
MAX_EXPORT_SESSIONS = 50


@dataclass(frozen=True)
class SessionFilters:
    student_id: str = ""
    student_match: str = "contains"
    lecture_id: str = ""
    start_date: str = ""
    end_date: str = ""
    min_user_turns: str = ""
    max_user_turns: str = ""
    min_grade: str = ""
    max_grade: str = ""
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE


def parse_int(raw_value: str, field_name: str) -> int | None:
    value = raw_value.strip()
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an integer.") from exc
    if parsed < 0:
        raise ValueError(f"{field_name} must be zero or greater.")
    return parsed


def parse_float(raw_value: str, field_name: str) -> float | None:
    value = raw_value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a number.") from exc


def parse_date_start(raw_value: str, field_name: str) -> dt.datetime | None:
    value = raw_value.strip()
    if not value:
        return None
    try:
        parsed_date = dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD.") from exc
    return dt.datetime.combine(parsed_date, dt.time.min)


def parse_date_exclusive_end(raw_value: str, field_name: str) -> dt.datetime | None:
    start = parse_date_start(raw_value, field_name)
    if start is None:
        return None
    return start + dt.timedelta(days=1)


def normalized_page(value: int) -> int:
    return max(1, value)


def normalized_page_size(value: int) -> int:
    return min(MAX_PAGE_SIZE, max(1, value))


def validate_session_id(raw_session_id: str) -> str:
    try:
        parsed = uuid.UUID(raw_session_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid session id: {raw_session_id}") from exc
    normalized = str(parsed)
    if raw_session_id.lower() != normalized:
        raise ValueError(f"Invalid session id: {raw_session_id}")
    return normalized


def validate_selected_session_ids(raw_session_ids: Iterable[str]) -> list[str]:
    session_ids = [sid.strip() for sid in raw_session_ids if sid.strip()]
    if not session_ids:
        raise ValueError("Select at least one session to export.")
    if len(session_ids) > MAX_EXPORT_SESSIONS:
        raise ValueError(f"Select no more than {MAX_EXPORT_SESSIONS} sessions at a time.")
    normalized = [validate_session_id(session_id) for session_id in session_ids]
    if len(set(normalized)) != len(normalized):
        raise ValueError("Selected session ids must be unique.")
    return normalized


def session_count_subqueries():
    message_counts = (
        sa.select(
            models.MessageModel.session_id.label("session_id"),
            sa.func.count(models.MessageModel.id).label("message_count"),
            sa.func.sum(sa.case((models.MessageModel.role == "user", 1), else_=0)).label("user_messages"),
            sa.func.sum(sa.case((models.MessageModel.role == "assistant", 1), else_=0)).label("assistant_messages"),
            sa.func.max(models.MessageModel.timestamp).label("latest_message_at"),
        )
        .group_by(models.MessageModel.session_id)
        .subquery()
    )
    note_counts = (
        sa.select(
            models.SessionNoteModel.session_id.label("session_id"),
            sa.func.count(models.SessionNoteModel.id).label("notes"),
        )
        .group_by(models.SessionNoteModel.session_id)
        .subquery()
    )
    grade_counts = (
        sa.select(
            models.GradeEventModel.session_id.label("session_id"),
            sa.func.count(models.GradeEventModel.id).label("grade_events"),
        )
        .group_by(models.GradeEventModel.session_id)
        .subquery()
    )
    return message_counts, note_counts, grade_counts


def sessions_select(filters: SessionFilters):
    message_counts, note_counts, grade_counts = session_count_subqueries()
    user_messages = sa.func.coalesce(message_counts.c.user_messages, 0)
    assistant_messages = sa.func.coalesce(message_counts.c.assistant_messages, 0)
    notes = sa.func.coalesce(note_counts.c.notes, 0)
    grade_events = sa.func.coalesce(grade_counts.c.grade_events, 0)

    stmt = (
        sa.select(
            models.SessionModel.session_id,
            models.SessionModel.student_id,
            models.SessionModel.lecture_id,
            models.SessionModel.started_at,
            models.SessionModel.ended_at,
            models.SessionModel.current_grade,
            sa.func.coalesce(message_counts.c.message_count, 0).label("message_count"),
            user_messages.label("user_messages"),
            assistant_messages.label("assistant_messages"),
            notes.label("notes"),
            grade_events.label("grade_events"),
            message_counts.c.latest_message_at,
        )
        .outerjoin(message_counts, message_counts.c.session_id == models.SessionModel.session_id)
        .outerjoin(note_counts, note_counts.c.session_id == models.SessionModel.session_id)
        .outerjoin(grade_counts, grade_counts.c.session_id == models.SessionModel.session_id)
    )

    if filters.student_id.strip():
        student_id = filters.student_id.strip()
        if filters.student_match == "exact":
            stmt = stmt.where(models.SessionModel.student_id == student_id)
        else:
            stmt = stmt.where(models.SessionModel.student_id.contains(student_id))
    if filters.lecture_id.strip():
        stmt = stmt.where(models.SessionModel.lecture_id == filters.lecture_id.strip())

    start_at = parse_date_start(filters.start_date, "Start date")
    end_before = parse_date_exclusive_end(filters.end_date, "End date")
    if start_at is not None:
        stmt = stmt.where(models.SessionModel.started_at >= start_at)
    if end_before is not None:
        stmt = stmt.where(models.SessionModel.started_at < end_before)

    min_user_turns = parse_int(filters.min_user_turns, "Minimum user turns")
    max_user_turns = parse_int(filters.max_user_turns, "Maximum user turns")
    if min_user_turns is not None:
        stmt = stmt.where(user_messages >= min_user_turns)
    if max_user_turns is not None:
        stmt = stmt.where(user_messages <= max_user_turns)

    min_grade = parse_float(filters.min_grade, "Minimum grade")
    max_grade = parse_float(filters.max_grade, "Maximum grade")
    if min_grade is not None:
        stmt = stmt.where(models.SessionModel.current_grade >= min_grade)
    if max_grade is not None:
        stmt = stmt.where(models.SessionModel.current_grade <= max_grade)

    return stmt


def list_sessions(db: sqlalchemy_orm.Session, filters: SessionFilters) -> dict:
    page = normalized_page(filters.page)
    page_size = normalized_page_size(filters.page_size)
    stmt = sessions_select(filters)

    total = db.execute(sa.select(sa.func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(models.SessionModel.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).mappings().all()

    return {
        "rows": [dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_previous": page > 1,
        "has_next": page * page_size < total,
    }


def sqlite_path_from_database_url(database_url: str) -> pathlib.Path:
    url = sa.engine.make_url(database_url)
    if not url.drivername.startswith("sqlite"):
        raise ValueError("Session exports currently require a SQLite DATABASE_URL.")
    if not url.database or url.database == ":memory:":
        raise ValueError("Session exports require a file-backed SQLite database.")
    return pathlib.Path(url.database)


def ensure_sessions_exist(db: sqlalchemy_orm.Session, session_ids: list[str]) -> None:
    existing = set(
        db.execute(
            sa.select(models.SessionModel.session_id).where(models.SessionModel.session_id.in_(session_ids))
        ).scalars()
    )
    missing = [session_id for session_id in session_ids if session_id not in existing]
    if missing:
        raise ValueError(f"Unknown session id: {missing[0]}")


def build_multi_export_manifest(session_ids: list[str]) -> dict:
    return {
        "format": "lecture_bot_sessions_multi_export",
        "exported_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "session_count": len(session_ids),
        "session_ids": session_ids,
        "notes": {
            "prompt_files_source": "current_files_at_export_time",
            "rendered_prompts_source": "dialogue_turn_audits",
            "student_comments_source": "conversation/session_notes.json",
        },
    }


def build_sessions_export_zip(
    *,
    db: sqlalchemy_orm.Session,
    session_ids: list[str],
    database_url: str,
    lectures_dir: pathlib.Path,
) -> bytes:
    normalized_session_ids = validate_selected_session_ids(session_ids)
    ensure_sessions_exist(db, normalized_session_ids)
    database_path = sqlite_path_from_database_url(database_url).resolve()

    buffer = io.BytesIO()
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    try:
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(build_multi_export_manifest(normalized_session_ids), indent=2).encode("utf-8"))
            for session_id in normalized_session_ids:
                export_session_package.write_session_package_to_zip(
                    zf,
                    conn=conn,
                    session_id=session_id,
                    lectures_dir=lectures_dir,
                    archive_prefix=f"{session_id}/",
                    zip_path=pathlib.Path("admin_session_export.zip"),
                    database_path=database_path,
                )
    finally:
        conn.close()
    return buffer.getvalue()
