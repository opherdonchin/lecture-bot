import argparse
import datetime as dt
import json
import pathlib
import sqlite3
import sys
import zipfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import app.bot_engine as bot_engine
import app.config as config_module

DATABASE_PATH = REPO_ROOT / "data" / "lecture_bot.db"
LECTURES_DIR = REPO_ROOT / "lectures"
PROMPTS_DIR = REPO_ROOT / "prompts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a lecture-bot session with prompts and lecture context files.",
    )
    parser.add_argument(
        "--lecture-id",
        required=True,
        help="Lecture id to export from, for example lecture_03.",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Specific session id to export. Defaults to the latest session for the lecture.",
    )
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=REPO_ROOT / "exports",
        help="Directory where the zip export will be written.",
    )
    return parser.parse_args()


def fetch_one_dict(conn: sqlite3.Connection, query: str, params: tuple) -> dict | None:
    row = conn.execute(query, params).fetchone()
    return dict(row) if row is not None else None


def fetch_all_dicts(conn: sqlite3.Connection, query: str, params: tuple) -> list[dict]:
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_session(conn: sqlite3.Connection, lecture_id: str, session_id: str | None) -> dict:
    if session_id:
        query = """
            select session_id, student_id, lecture_id, started_at, ended_at, current_grade
            from sessions
            where session_id = ?
        """
        params = (session_id,)
    else:
        query = """
            select session_id, student_id, lecture_id, started_at, ended_at, current_grade
            from sessions
            where lecture_id = ?
            order by started_at desc
            limit 1
        """
        params = (lecture_id,)

    session = fetch_one_dict(conn, query, params)
    if session is None:
        if session_id:
            raise ValueError(f"Session not found: {session_id}")
        raise ValueError(f"No sessions found for lecture: {lecture_id}")
    if session["lecture_id"] != lecture_id:
        raise ValueError(
            f"Session {session['session_id']} belongs to lecture {session['lecture_id']}, not {lecture_id}",
        )
    return session


def parse_json_field(raw_text: str | None) -> tuple[object | None, str | None]:
    if raw_text is None:
        return None, None
    try:
        return json.loads(raw_text), None
    except json.JSONDecodeError as exc:
        return None, str(exc)


def load_session_bundle(conn: sqlite3.Connection, session: dict) -> dict:
    session_id = session["session_id"]
    messages = fetch_all_dicts(
        conn,
        """
        select id, session_id, role, content, timestamp
        from messages
        where session_id = ?
        order by timestamp asc, id asc
        """,
        (session_id,),
    )
    grade_events = fetch_all_dicts(
        conn,
        """
        select id, session_id, event_type, grade, timestamp, payload_json
        from grade_events
        where session_id = ?
        order by timestamp asc, id asc
        """,
        (session_id,),
    )
    session_state_row = fetch_one_dict(
        conn,
        """
        select session_id, state_json, updated_at
        from session_state
        where session_id = ?
        """,
        (session_id,),
    )

    state_parsed = None
    state_parse_error = None
    if session_state_row is not None:
        state_parsed, state_parse_error = parse_json_field(session_state_row["state_json"])

    parsed_grade_events = []
    for event in grade_events:
        payload_parsed, payload_parse_error = parse_json_field(event.get("payload_json"))
        parsed_event = dict(event)
        parsed_event["payload"] = payload_parsed
        if payload_parse_error:
            parsed_event["payload_parse_error"] = payload_parse_error
        parsed_grade_events.append(parsed_event)

    return {
        "session": session,
        "messages": messages,
        "session_state": session_state_row,
        "session_state_parsed": state_parsed,
        "session_state_parse_error": state_parse_error,
        "grade_events": parsed_grade_events,
    }


def build_rendered_prompt(lecture_id: str, state: dict | None) -> str:
    lecture_package = load_lecture_package(lecture_id)
    settings = config_module.get_settings()
    return bot_engine.build_dialogue_system_prompt(
        lecture_package=lecture_package,
        state=state or {},
        topic_defs=bot_engine.resolve_topic_defs(lecture_package),
        lecture_context=bot_engine.build_dialogue_context(
            lecture_package,
            settings.max_dialogue_context_chars,
        ),
        timing_context={},
    )


def write_json_bytes(payload: object) -> bytes:
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def collect_lecture_files(lecture_dir: pathlib.Path) -> list[tuple[pathlib.Path, str]]:
    wanted = [
        ("lecture_config.json", "lecture/lecture_config.json"),
        ("slides.md", "lecture/slides.md"),
        ("handout.md", "lecture/handout.md"),
        ("rubric.md", "lecture/rubric.md"),
        ("minutes.json", "lecture/minutes.json"),
    ]
    files: list[tuple[pathlib.Path, str]] = []
    for source_name, archive_name in wanted:
        source_path = lecture_dir / source_name
        if not source_path.exists():
            raise FileNotFoundError(f"Required lecture export file not found: {source_path}")
        files.append((source_path, archive_name))
    return files


def collect_prompt_files() -> list[tuple[pathlib.Path, str]]:
    wanted = [
        ("dialogue_system_prompt.md", "prompts/dialogue_system_prompt.md"),
        ("tutor_generation_prompt.md", "prompts/tutor_generation_prompt.md"),
        ("master_rubric_generation_prompt.md", "prompts/master_rubric_generation_prompt.md"),
        ("minutes_generation_prompt.md", "prompts/minutes_generation_prompt.md"),
    ]
    return [(PROMPTS_DIR / name, archive_name) for name, archive_name in wanted]


def build_manifest(
    *,
    lecture_id: str,
    session_bundle: dict,
    database_path: pathlib.Path,
    lecture_dir: pathlib.Path,
    zip_path: pathlib.Path,
) -> dict:
    session = session_bundle["session"]
    return {
        "export_generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "lecture_id": lecture_id,
        "session_id": session["session_id"],
        "student_id": session["student_id"],
        "started_at": session["started_at"],
        "ended_at": session["ended_at"],
        "current_grade": session["current_grade"],
        "source_database": str(database_path),
        "source_lecture_dir": str(lecture_dir),
        "zip_path": str(zip_path),
        "included_files": [
            "conversation/session_bundle.json",
            "conversation/messages_for_chat_agent.json",
            "prompts/dialogue_system_prompt.md",
            "prompts/dialogue_system_prompt_rendered_latest.md",
            "prompts/tutor_generation_prompt.md",
            "prompts/master_rubric_generation_prompt.md",
            "prompts/minutes_generation_prompt.md",
            "lecture/lecture_config.json",
            "lecture/slides.md",
            "lecture/handout.md",
            "lecture/rubric.md",
            "lecture/minutes.json",
        ],
    }


def export_session_package(lecture_id: str, session_id: str | None, output_dir: pathlib.Path) -> pathlib.Path:
    database_path = DATABASE_PATH.resolve()
    lecture_dir = (LECTURES_DIR / lecture_id).resolve()
    if not lecture_dir.exists():
        raise FileNotFoundError(f"Lecture directory not found: {lecture_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    try:
        session = get_session(conn, lecture_id=lecture_id, session_id=session_id)
        session_bundle = load_session_bundle(conn, session)
    finally:
        conn.close()

    rendered_prompt = build_rendered_prompt(
        lecture_id=lecture_id,
        state=session_bundle.get("session_state_parsed"),
    )
    chat_agent_messages = [
        {"role": "system", "content": rendered_prompt},
        *[
            {"role": message["role"], "content": message["content"]}
            for message in session_bundle["messages"]
        ],
    ]

    timestamp = session["started_at"].replace(":", "").replace("-", "").replace(" ", "T").split(".")[0]
    zip_name = f"{lecture_id}_{session['session_id']}_{timestamp}.zip"
    zip_path = (output_dir / zip_name).resolve()

    manifest = build_manifest(
        lecture_id=lecture_id,
        session_bundle=session_bundle,
        database_path=database_path,
        lecture_dir=lecture_dir,
        zip_path=zip_path,
    )

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", write_json_bytes(manifest))
        zf.writestr("conversation/session_bundle.json", write_json_bytes(session_bundle))
        zf.writestr("conversation/messages_for_chat_agent.json", write_json_bytes(chat_agent_messages))
        zf.writestr("prompts/dialogue_system_prompt_rendered_latest.md", rendered_prompt.encode("utf-8"))

        for source_path, archive_name in collect_prompt_files():
            zf.write(source_path, archive_name)

        for source_path, archive_name in collect_lecture_files(lecture_dir):
            zf.write(source_path, archive_name)

    return zip_path


def load_lecture_package(lecture_id: str) -> dict:
    lecture_dir = LECTURES_DIR / lecture_id
    if not lecture_dir.exists():
        raise FileNotFoundError(f"Lecture directory not found: {lecture_dir}")

    defaults_path = LECTURES_DIR / "config.json"
    lecture_config_path = lecture_dir / "lecture_config.json"
    rubric_path = lecture_dir / "rubric.md"
    if not lecture_config_path.exists():
        raise FileNotFoundError(f"Lecture config not found: {lecture_config_path}")
    if not rubric_path.exists():
        raise FileNotFoundError(f"Rubric file not found: {rubric_path}")

    lectures_defaults = json.loads(defaults_path.read_text(encoding="utf-8")) if defaults_path.exists() else {}
    lecture_config = json.loads(lecture_config_path.read_text(encoding="utf-8"))
    context_file_defs = lecture_config.get("context_files", lectures_defaults.get("context_files", []))

    context_sections: list[dict] = []
    for item in context_file_defs:
        file_path = lecture_dir / item["path"]
        required = bool(item.get("required", True))
        if not file_path.exists():
            if required:
                raise FileNotFoundError(f"Required lecture context file not found: {file_path}")
            continue
        context_sections.append(
            {
                "key": item["key"],
                "label": item.get("label") or item["key"],
                "content": file_path.read_text(encoding="utf-8"),
            }
        )

    return {
        "lecture_id": lecture_id,
        "config": lecture_config,
        "topics": lecture_config.get("topics", []),
        "rubric": rubric_path.read_text(encoding="utf-8"),
        "context_sections": context_sections,
    }


def main() -> None:
    args = parse_args()
    zip_path = export_session_package(
        lecture_id=args.lecture_id,
        session_id=args.session_id,
        output_dir=args.output_dir,
    )
    print(zip_path)


if __name__ == "__main__":
    main()
