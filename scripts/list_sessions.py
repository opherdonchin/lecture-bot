import argparse
import datetime as dt
import pathlib
import sqlite3


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = REPO_ROOT / "data" / "lecture_bot.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List recent lecture-bot sessions with activity counts.")
    parser.add_argument(
        "--database",
        type=pathlib.Path,
        default=DEFAULT_DATABASE_PATH,
        help="SQLite database path. Defaults to data/lecture_bot.db.",
    )
    parser.add_argument("--lecture-id", default=None, help="Only show sessions for this lecture id.")
    parser.add_argument("--student-id", default=None, help="Only show sessions for this student id.")
    parser.add_argument("--session-id", default=None, help="Only show one session id.")
    parser.add_argument("--since", default=None, help="Only show sessions started at or after this timestamp/date.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of sessions to show.")
    return parser.parse_args()


def parse_since(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    value = raw_value.strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        parsed_date = dt.date.fromisoformat(value)
        parsed = dt.datetime.combine(parsed_date, dt.time.min)
    return parsed.isoformat(sep=" ")


def format_value(value: object, width: int) -> str:
    text = "" if value is None else str(value)
    if len(text) <= width:
        return text.ljust(width)
    return f"{text[: width - 1]}..."


def main() -> None:
    args = parse_args()
    database_path = args.database.resolve()
    since = parse_since(args.since)

    filters = []
    params: list[object] = []
    if args.session_id:
        filters.append("s.session_id = ?")
        params.append(args.session_id)
    if args.lecture_id:
        filters.append("s.lecture_id = ?")
        params.append(args.lecture_id)
    if args.student_id:
        filters.append("s.student_id = ?")
        params.append(args.student_id)
    if since:
        filters.append("s.started_at >= ?")
        params.append(since)

    where_clause = f"where {' and '.join(filters)}" if filters else ""
    params.append(args.limit)

    query = f"""
        select
            s.session_id,
            s.student_id,
            s.lecture_id,
            s.started_at,
            s.ended_at,
            s.current_grade,
            count(m.id) as message_count,
            sum(case when m.role = 'user' then 1 else 0 end) as user_messages,
            sum(case when m.role = 'assistant' then 1 else 0 end) as assistant_messages,
            count(distinct n.id) as notes,
            count(distinct ge.id) as grade_events,
            max(m.timestamp) as latest_message_at
        from sessions s
        left join messages m on m.session_id = s.session_id
        left join session_notes n on n.session_id = s.session_id
        left join grade_events ge on ge.session_id = s.session_id
        {where_clause}
        group by s.session_id
        order by s.started_at desc
        limit ?
    """

    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = [dict(row) for row in conn.execute(query, params).fetchall()]
    finally:
        conn.close()

    if not rows:
        print("No sessions found.")
        return

    columns = [
        ("started_at", 24),
        ("lecture_id", 12),
        ("student_id", 16),
        ("user_messages", 13),
        ("assistant_messages", 18),
        ("notes", 5),
        ("grade_events", 12),
        ("current_grade", 13),
        ("session_id", 36),
    ]
    print(" ".join(format_value(name, width) for name, width in columns))
    print(" ".join("-" * width for _, width in columns))
    for row in rows:
        print(" ".join(format_value(row.get(name), width) for name, width in columns))


if __name__ == "__main__":
    main()
