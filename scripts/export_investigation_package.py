import argparse
import datetime as dt
import json
import pathlib
import shutil
import sqlite3
import zipfile


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DATABASE_PATH = REPO_ROOT / "data" / "lecture_bot.db"
LECTURES_DIR = REPO_ROOT / "lectures"
PROMPTS_DIR = REPO_ROOT / "prompts"
EXPORTS_DIR = REPO_ROOT / "exports"

DEFAULT_LECTURE_ID = "lecture_03"
DEFAULT_SESSION_IDS = [
    "f07ee636-6af0-452c-b39c-a40d47396fce",
    "935f1487-39ee-4af1-905f-2bae807b3c83",
]
DEFAULT_ARTIFACTS = [
    pathlib.Path("/tmp/prompt_eval_results.json"),
    pathlib.Path("/tmp/prompt_eval_draw_loop_round2.json"),
    pathlib.Path("/tmp/draw_loop_decision_traces_round2.json"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a multi-session investigation handoff package.",
    )
    parser.add_argument(
        "--lecture-id",
        default=DEFAULT_LECTURE_ID,
        help="Lecture id to export, for example lecture_03.",
    )
    parser.add_argument(
        "--session-id",
        dest="session_ids",
        action="append",
        default=[],
        help="Session id to include. May be passed multiple times.",
    )
    parser.add_argument(
        "--artifact",
        dest="artifacts",
        action="append",
        default=[],
        help="Extra JSON artifact to include. May be passed multiple times.",
    )
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=EXPORTS_DIR,
        help="Directory where the package directory and zip will be written.",
    )
    return parser.parse_args()


def fetch_one_dict(conn: sqlite3.Connection, query: str, params: tuple) -> dict | None:
    row = conn.execute(query, params).fetchone()
    return dict(row) if row is not None else None


def fetch_all_dicts(conn: sqlite3.Connection, query: str, params: tuple) -> list[dict]:
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def parse_json_field(raw_text: str | None) -> tuple[object | None, str | None]:
    if raw_text is None:
        return None, None
    try:
        return json.loads(raw_text), None
    except json.JSONDecodeError as exc:
        return None, str(exc)


def load_session_data(conn: sqlite3.Connection, session_id: str, lecture_id: str) -> dict:
    session = fetch_one_dict(
        conn,
        """
        select session_id, student_id, lecture_id, started_at, ended_at, current_grade
        from sessions
        where session_id = ?
        """,
        (session_id,),
    )
    if session is None:
        raise ValueError(f"Session not found: {session_id}")
    if session["lecture_id"] != lecture_id:
        raise ValueError(
            f"Session {session_id} belongs to lecture {session['lecture_id']}, not {lecture_id}",
        )

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
    dialogue_turn_audits = fetch_all_dicts(
        conn,
        """
        select *
        from dialogue_turn_audits
        where session_id = ?
        order by turn_index asc, id asc
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
    session_notes = fetch_all_dicts(
        conn,
        """
        select id, session_id, note_text, turn_index, latest_message_id,
               latest_assistant_message_id, state_json, created_at
        from session_notes
        where session_id = ?
        order by created_at asc, id asc
        """,
        (session_id,),
    )
    state_row = fetch_one_dict(
        conn,
        """
        select session_id, state_json, updated_at
        from session_state
        where session_id = ?
        """,
        (session_id,),
    )
    state_parsed, state_parse_error = (None, None)
    if state_row is not None:
        state_parsed, state_parse_error = parse_json_field(state_row["state_json"])

    audits_enriched = []
    for audit in dialogue_turn_audits:
        enriched = dict(audit)
        for key in [
            "state_before_json",
            "recent_messages_json",
            "action_hint_json",
        ]:
            parsed, parse_error = parse_json_field(enriched.get(key))
            enriched[key.removesuffix("_json")] = parsed
            if parse_error:
                enriched[f"{key}_parse_error"] = parse_error
        audits_enriched.append(enriched)

    grade_events_enriched = []
    for event in grade_events:
        enriched = dict(event)
        payload, parse_error = parse_json_field(event.get("payload_json"))
        enriched["payload"] = payload
        if parse_error:
            enriched["payload_parse_error"] = parse_error
        grade_events_enriched.append(enriched)

    session_notes_enriched = []
    for note in session_notes:
        enriched = dict(note)
        state, parse_error = parse_json_field(note.get("state_json"))
        enriched["state"] = state
        if parse_error:
            enriched["state_json_parse_error"] = parse_error
        session_notes_enriched.append(enriched)

    chat_transcript = [
        {"role": message["role"], "content": message["content"]}
        for message in messages
    ]

    return {
        "session": session,
        "messages": messages,
        "chat_transcript": chat_transcript,
        "dialogue_turn_audits": audits_enriched,
        "session_state": state_row,
        "session_state_parsed": state_parsed,
        "session_state_parse_error": state_parse_error,
        "grade_events": grade_events_enriched,
        "session_notes": session_notes_enriched,
    }


def ensure_clean_dir(path: pathlib.Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: pathlib.Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def copy_file(source: pathlib.Path, destination: pathlib.Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def build_readme(
    *,
    lecture_id: str,
    session_ids: list[str],
    artifact_paths: list[pathlib.Path],
    package_dir: pathlib.Path,
) -> str:
    generated_at = dt.datetime.now(dt.timezone.utc).isoformat()
    artifact_lines = "\n".join(
        f"- `artifacts/{path.name}`" for path in artifact_paths
    ) or "- none"
    session_lines = "\n".join(f"- `{sid}`" for sid in session_ids)
    return f"""# Investigation Export Package

Generated at: `{generated_at}`

This package was assembled for a handoff to another agent investigating tutoring-loop behavior in `lecture-bot`.

## Included Sessions

{session_lines}

## Included Materials

- `sessions/<session_id>/session_bundle.json`: raw session metadata, messages, audits, state, and grade events
- `sessions/<session_id>/chat_transcript.json`: compact role/content transcript
- `sessions/<session_id>/dialogue_turn_audits.json`: parsed audit rows with parsed JSON fields expanded
- `sessions/<session_id>/messages.txt`: plain-text transcript for quick reading
- `prompts/`: active prompt files
- `prompt_generators/`: code that builds and sanitizes dialogue prompts/replies
- `lecture/`: lecture_03 config and context files used by the dialogue prompt
- `artifacts/`: evaluation JSON outputs produced during this investigation
- `manifest.json`: package manifest

## Prompt Generator Files

- `prompt_generators/app/bot_engine.py`
- `prompt_generators/app/prompt_loader.py`
- `prompt_generators/app/config.py`
- `prompt_generators/app/lecture_loader.py`
- `prompt_generators/scripts/export_session_package.py`

## Evaluation Artifacts

{artifact_lines}

## Source Location

- Repo root: `{REPO_ROOT}`
- Package dir: `{package_dir}`
- Lecture id: `{lecture_id}`
"""


def build_manifest(
    *,
    lecture_id: str,
    session_ids: list[str],
    artifact_paths: list[pathlib.Path],
    package_dir: pathlib.Path,
    zip_path: pathlib.Path,
) -> dict:
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "lecture_id": lecture_id,
        "session_ids": session_ids,
        "repo_root": str(REPO_ROOT),
        "database_path": str(DATABASE_PATH),
        "package_dir": str(package_dir),
        "zip_path": str(zip_path),
        "artifacts": [str(path) for path in artifact_paths],
        "included_roots": [
            "sessions/",
            "prompts/",
            "prompt_generators/",
            "lecture/",
            "artifacts/",
            "README.md",
        ],
    }


def transcript_text(messages: list[dict]) -> str:
    lines = []
    for message in messages:
        lines.append(f"{message['role'].upper()}: {message['content']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def zip_directory(source_dir: pathlib.Path, zip_path: pathlib.Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir():
                continue
            zf.write(path, path.relative_to(source_dir))


def export_package(
    *,
    lecture_id: str,
    session_ids: list[str],
    artifact_paths: list[pathlib.Path],
    output_dir: pathlib.Path,
) -> tuple[pathlib.Path, pathlib.Path]:
    timestamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    package_name = f"investigation_export_{lecture_id}_{timestamp}"
    package_dir = output_dir / package_name
    zip_path = output_dir / f"{package_name}.zip"

    ensure_clean_dir(package_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        for session_id in session_ids:
            session_data = load_session_data(conn, session_id, lecture_id)
            session_dir = package_dir / "sessions" / session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            write_json(session_dir / "session_bundle.json", session_data)
            write_json(session_dir / "chat_transcript.json", session_data["chat_transcript"])
            write_json(session_dir / "dialogue_turn_audits.json", session_data["dialogue_turn_audits"])
            write_json(session_dir / "session_notes.json", session_data["session_notes"])
            (session_dir / "messages.txt").write_text(
                transcript_text(session_data["messages"]),
                encoding="utf-8",
            )
    finally:
        conn.close()

    prompt_files = [
        "tutor_prompt.md",
        "tutor_generator_prompt.md",
        "master_rubric_generation_prompt.md",
        "minutes_generation_prompt.md",
    ]
    for name in prompt_files:
        copy_file(PROMPTS_DIR / name, package_dir / "prompts" / name)

    generator_files = [
        REPO_ROOT / "app" / "bot_engine.py",
        REPO_ROOT / "app" / "prompt_loader.py",
        REPO_ROOT / "app" / "config.py",
        REPO_ROOT / "app" / "lecture_loader.py",
        REPO_ROOT / "scripts" / "export_session_package.py",
    ]
    for source_path in generator_files:
        copy_file(source_path, package_dir / "prompt_generators" / source_path.relative_to(REPO_ROOT))

    lecture_dir = LECTURES_DIR / lecture_id
    lecture_files = [
        lecture_dir / "lecture_config.json",
        lecture_dir / "slides.md",
        lecture_dir / "handout.md",
        lecture_dir / "rubric.md",
        lecture_dir / "minutes.json",
        lecture_dir / "transcript.md",
        LECTURES_DIR / "config.json",
    ]
    for source_path in lecture_files:
        copy_file(source_path, package_dir / "lecture" / source_path.name)

    copied_artifacts = []
    for artifact_path in artifact_paths:
        if not artifact_path.exists():
            continue
        copy_file(artifact_path, package_dir / "artifacts" / artifact_path.name)
        copied_artifacts.append(artifact_path)

    readme = build_readme(
        lecture_id=lecture_id,
        session_ids=session_ids,
        artifact_paths=copied_artifacts,
        package_dir=package_dir,
    )
    (package_dir / "README.md").write_text(readme, encoding="utf-8")

    manifest = build_manifest(
        lecture_id=lecture_id,
        session_ids=session_ids,
        artifact_paths=copied_artifacts,
        package_dir=package_dir,
        zip_path=zip_path,
    )
    write_json(package_dir / "manifest.json", manifest)

    if zip_path.exists():
        zip_path.unlink()
    zip_directory(package_dir, zip_path)
    return package_dir, zip_path


def main() -> None:
    args = parse_args()
    session_ids = args.session_ids or list(DEFAULT_SESSION_IDS)
    artifact_paths = list(DEFAULT_ARTIFACTS)
    artifact_paths.extend(pathlib.Path(path) for path in args.artifacts)
    package_dir, zip_path = export_package(
        lecture_id=args.lecture_id,
        session_ids=session_ids,
        artifact_paths=artifact_paths,
        output_dir=args.output_dir,
    )
    print(package_dir)
    print(zip_path)


if __name__ == "__main__":
    main()
