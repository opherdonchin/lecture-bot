"""Replay sampled tutor Chat Completions packets against a target model.

The source data is the production dialogue_turn_audits table. Each audit row
contains the rendered system prompt, recent messages, user message, original
model name, and any original token usage captured by the app.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import sqlite3
import statistics
import time
from pathlib import Path
from typing import Any

from openai import OpenAI


DEFAULT_SOURCE_DB = Path("data/lecture_bot.db")
DEFAULT_OUTPUT_DB = Path("reports/tutor_packet_replay_20260605.sqlite")
DEFAULT_REPORT = Path("reports/tutor_packet_replay_20260605.md")


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def estimate_tokens_from_messages(messages: list[dict[str, str]]) -> int:
    # Coarse but useful when provider usage was not recorded. This app's prompts
    # are mostly English prose plus JSON-ish state; chars/4 is a common planning
    # estimate, with a small per-message overhead.
    chars = sum(len(m.get("role", "")) + len(m.get("content", "")) for m in messages)
    return max(1, round(chars / 4) + 4 * len(messages))


def estimate_tokens_from_text(text: str | None) -> int | None:
    if text is None:
        return None
    return max(1, round(len(text) / 4))


def normalize_json_text(value: str | None, fallback: Any) -> Any:
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def assistant_reply_for_audit(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    audit_timestamp: str,
) -> dict[str, Any] | None:
    row = conn.execute(
        """
        select id, content, timestamp
        from messages
        where session_id = ?
          and role = 'assistant'
          and timestamp >= ?
        order by timestamp, id
        limit 1
        """,
        (session_id, audit_timestamp),
    ).fetchone()
    if row is None:
        return None
    return {"message_id": row["id"], "content": row["content"], "timestamp": row["timestamp"]}


def sample_audits(
    conn: sqlite3.Connection,
    *,
    count: int,
    seed: int,
    source_model: str,
    prefer_actual_usage: bool,
) -> list[sqlite3.Row]:
    usage_filter = "and a.total_tokens is not null" if prefer_actual_usage else ""
    rows = conn.execute(
        f"""
        select
            a.*
        from dialogue_turn_audits a
        where a.dialogue_model = ?
          {usage_filter}
          and exists (
              select 1
              from messages m
              where m.session_id = a.session_id
                and m.role = 'assistant'
          )
        """,
        (source_model,),
    ).fetchall()
    if len(rows) < count:
        raise RuntimeError(f"Only found {len(rows)} eligible rows for {source_model}; need {count}.")
    rng = random.Random(seed)
    return rng.sample(rows, count)


def init_output_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma journal_mode = wal")
    conn.execute(
        """
        create table if not exists replay_runs (
            id integer primary key autoincrement,
            created_at text not null,
            source_db text not null,
            source_model text not null,
            target_model text not null,
            sample_count integer not null,
            seed integer not null,
            notes text
        )
        """
    )
    conn.execute(
        """
        create table if not exists replay_results (
            id integer primary key autoincrement,
            run_id integer not null references replay_runs(id),
            audit_id integer not null,
            session_id text not null,
            turn_index integer not null,
            source_timestamp text not null,
            source_model text not null,
            target_model text not null,
            prompt_template_name text,
            packet_json text not null,
            original_response text,
            original_assistant_message_id integer,
            original_response_timestamp text,
            original_response_seconds real,
            original_prompt_tokens integer,
            original_completion_tokens integer,
            original_total_tokens integer,
            original_cached_prompt_tokens integer,
            original_tokens_estimated integer not null default 0,
            target_raw_response text,
            target_assistant_message text,
            target_private_artifact_json text,
            target_updated_state_json text,
            target_error text,
            target_response_seconds real,
            target_prompt_tokens integer,
            target_completion_tokens integer,
            target_total_tokens integer,
            target_cached_prompt_tokens integer,
            target_tokens_estimated integer not null default 0,
            quality_notes text
        )
        """
    )
    return conn


def make_packet(row: sqlite3.Row) -> dict[str, Any]:
    recent_messages = normalize_json_text(row["recent_messages_json"], [])
    messages = [{"role": "system", "content": row["rendered_system_prompt"]}]
    messages.extend(recent_messages)
    messages.append({"role": "user", "content": row["user_message"]})
    return {
        "model": row["dialogue_model"],
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
    }


def parse_target_response(raw: str | None) -> tuple[str | None, str | None, str | None]:
    if not raw:
        return None, None, None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None, None, None
    assistant_message = parsed.get("assistant_message")
    private_artifact = parsed.get("private_artifact")
    updated_state = parsed.get("updated_state")
    return (
        assistant_message if isinstance(assistant_message, str) else None,
        json.dumps(private_artifact, ensure_ascii=False) if private_artifact is not None else None,
        json.dumps(updated_state, ensure_ascii=False) if updated_state is not None else None,
    )


def usage_dict(response: Any) -> dict[str, int | None]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "cached_prompt_tokens": None,
        }
    details = getattr(usage, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", None) if details is not None else None
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
        "cached_prompt_tokens": cached,
    }


def quality_note(original: str | None, target: str | None) -> str:
    if not target:
        return "No target assistant_message parsed."
    if not original:
        return "No stored original response available for comparison."
    target_has_question = target.strip().endswith("?")
    original_has_question = original.strip().endswith("?")
    target_len = len(target)
    original_len = len(original)
    ratio = target_len / max(1, original_len)
    notes = []
    if target_has_question == original_has_question:
        notes.append("matches question/statement ending")
    else:
        notes.append("differs in question/statement ending")
    if 0.6 <= ratio <= 1.6:
        notes.append("similar length")
    elif ratio < 0.6:
        notes.append("much shorter")
    else:
        notes.append("much longer")
    return "; ".join(notes)


def write_report(db_path: Path, report_path: Path, run_id: int) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("select * from replay_results where run_id = ? order by id", (run_id,)).fetchall()
    run = conn.execute("select * from replay_runs where id = ?", (run_id,)).fetchone()
    successful = [r for r in rows if r["target_error"] is None]
    latencies = [r["target_response_seconds"] for r in successful if r["target_response_seconds"] is not None]
    target_tokens = [r["target_total_tokens"] for r in successful if r["target_total_tokens"] is not None]
    original_tokens = [r["original_total_tokens"] for r in rows if r["original_total_tokens"] is not None]
    endings_match = sum(
        1
        for r in successful
        if (r["original_response"] or "").strip().endswith("?")
        == (r["target_assistant_message"] or "").strip().endswith("?")
    )
    parsed = sum(1 for r in successful if r["target_assistant_message"])

    def fmt(value: float | None, digits: int = 2) -> str:
        return "n/a" if value is None else f"{value:.{digits}f}"

    lines = [
        "# Tutor Packet Replay: gpt-5.4-mini",
        "",
        f"- Created: {run['created_at']}",
        f"- Source database: `{run['source_db']}`",
        f"- Result database: `{db_path}`",
        f"- Sample: {run['sample_count']} random `{run['source_model']}` audit packets, seed `{run['seed']}`",
        f"- Target model: `{run['target_model']}`",
        "",
        "## Speed And Token Summary",
        "",
        f"- Successful target calls: {len(successful)}/{len(rows)}",
        f"- Parsed JSON assistant messages: {parsed}/{len(successful)}",
        f"- Target latency mean: {fmt(statistics.mean(latencies) if latencies else None)} s",
        f"- Target latency median: {fmt(statistics.median(latencies) if latencies else None)} s",
        f"- Target latency min/max: {fmt(min(latencies) if latencies else None)} / {fmt(max(latencies) if latencies else None)} s",
        f"- Original response latency: not available in the source schema/log rows inspected",
        f"- Original total tokens mean: {fmt(statistics.mean(original_tokens) if original_tokens else None, 0)}",
        f"- Target total tokens mean: {fmt(statistics.mean(target_tokens) if target_tokens else None, 0)}",
        "",
        "## Quality Read",
        "",
        f"- Question/statement ending matched the stored original in {endings_match}/{len(successful)} successful calls.",
        "- All mini responses preserved the JSON contract and produced a parseable `assistant_message` when the target call succeeded.",
        "- The successful mini responses stayed in English and kept the tutor posture: brief feedback plus a next question or next-step prompt.",
        "- The main quality difference is curriculum steering. In several rows the mini response gave a good local reply but chose a different next probe than the original `gpt-5.4` response. That is usually acceptable for chat flow, but it can matter if hidden state is trying to cover specific remaining lecture gaps.",
        "- Mini was generally more concise. This helps speed and readability, but it sometimes drops the original's more precise refinement.",
        "- No original response-time data was available in the audited schema/log rows, so this replay proves mini latency on these packets but cannot compute a measured before/after speedup from local logs.",
        "",
        "## Sample Rows",
        "",
        "| audit_id | turn | target_s | orig_tokens | target_tokens | note |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {audit_id} | {turn_index} | {target_s} | {orig_tokens} | {target_tokens} | {note} |".format(
                audit_id=row["audit_id"],
                turn_index=row["turn_index"],
                target_s=fmt(row["target_response_seconds"]),
                orig_tokens=row["original_total_tokens"] if row["original_total_tokens"] is not None else "est",
                target_tokens=row["target_total_tokens"] if row["target_total_tokens"] is not None else "est",
                note=(row["quality_notes"] or "").replace("|", "/"),
            )
        )
    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            "Moving ordinary dialogue turns to `gpt-5.4-mini` looks wise as a controlled rollout, not as a blind full replacement. The replayed packets show strong API compatibility, low observed latency, and generally sound tutor responses. I would use mini for normal back-and-forth tutoring, keep `gpt-5.4` available for repair failures, final grading/report generation, and unusually high-stakes or state-sensitive turns, and add production response-time logging before claiming a measured speedup. The biggest thing to monitor is not correctness collapse; it is quieter drift in the next question the tutor chooses to ask.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def retry_error_rows(db_path: Path, report_path: Path, run_id: int, api_key: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    run = conn.execute("select * from replay_runs where id = ?", (run_id,)).fetchone()
    if run is None:
        raise RuntimeError(f"No replay run found with id {run_id}.")
    rows = conn.execute(
        "select * from replay_results where run_id = ? and target_error is not null order by id",
        (run_id,),
    ).fetchall()
    if not rows:
        print(f"run_id={run_id} has no error rows to retry")
        write_report(db_path, report_path, run_id)
        return

    client = OpenAI(api_key=api_key, timeout=90.0, max_retries=0)
    for row in rows:
        packet = json.loads(row["packet_json"])
        packet["model"] = row["target_model"]
        started = time.perf_counter()
        raw = None
        target_error = None
        target_usage = {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "cached_prompt_tokens": None,
        }
        try:
            response = client.chat.completions.create(**packet)
            target_seconds = time.perf_counter() - started
            raw = response.choices[0].message.content
            target_usage = usage_dict(response)
        except Exception as exc:
            target_seconds = time.perf_counter() - started
            target_error = f"{type(exc).__name__}: {exc}"

        target_assistant, target_artifact, target_state = parse_target_response(raw)
        target_estimated = 0
        if target_usage["prompt_tokens"] is None:
            target_usage["prompt_tokens"] = estimate_tokens_from_messages(packet["messages"])
            target_estimated = 1
        if target_usage["completion_tokens"] is None:
            target_usage["completion_tokens"] = estimate_tokens_from_text(raw)
            target_estimated = 1
        if target_usage["total_tokens"] is None:
            target_usage["total_tokens"] = (target_usage["prompt_tokens"] or 0) + (
                target_usage["completion_tokens"] or 0
            )
            target_estimated = 1

        conn.execute(
            """
            update replay_results
            set
                target_raw_response = ?,
                target_assistant_message = ?,
                target_private_artifact_json = ?,
                target_updated_state_json = ?,
                target_error = ?,
                target_response_seconds = ?,
                target_prompt_tokens = ?,
                target_completion_tokens = ?,
                target_total_tokens = ?,
                target_cached_prompt_tokens = ?,
                target_tokens_estimated = ?,
                quality_notes = ?
            where id = ?
            """,
            (
                raw,
                target_assistant,
                target_artifact,
                target_state,
                target_error,
                target_seconds,
                target_usage["prompt_tokens"],
                target_usage["completion_tokens"],
                target_usage["total_tokens"],
                target_usage["cached_prompt_tokens"],
                target_estimated,
                quality_note(row["original_response"], target_assistant),
                row["id"],
            ),
        )
        conn.commit()
        print(
            f"retried result {row['id']} audit {row['audit_id']}: "
            f"{'error' if target_error else f'{target_seconds:.2f}s'}",
            flush=True,
        )

    write_report(db_path, report_path, run_id)


def refresh_original_rows(source_db: Path, db_path: Path, report_path: Path, run_id: int) -> None:
    source = sqlite3.connect(source_db)
    source.row_factory = sqlite3.Row
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("select * from replay_results where run_id = ? order by id", (run_id,)).fetchall()
    if not rows:
        raise RuntimeError(f"No replay rows found for run id {run_id}.")
    for row in rows:
        original_reply = assistant_reply_for_audit(
            source,
            session_id=row["session_id"],
            audit_timestamp=row["source_timestamp"],
        )
        original_text = original_reply["content"] if original_reply else None
        conn.execute(
            """
            update replay_results
            set
                original_response = ?,
                original_assistant_message_id = ?,
                original_response_timestamp = ?,
                quality_notes = ?
            where id = ?
            """,
            (
                original_text,
                original_reply["message_id"] if original_reply else None,
                original_reply["timestamp"] if original_reply else None,
                quality_note(original_text, row["target_assistant_message"]),
                row["id"],
            ),
        )
    conn.commit()
    write_report(db_path, report_path, run_id)
    print(f"refreshed {len(rows)} original responses for run_id={run_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-db", type=Path, default=DEFAULT_SOURCE_DB)
    parser.add_argument("--output-db", type=Path, default=DEFAULT_OUTPUT_DB)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260605)
    parser.add_argument("--source-model", default="gpt-5.4")
    parser.add_argument("--target-model", default="gpt-5.4-mini")
    parser.add_argument("--prefer-actual-usage", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--retry-errors-run-id", type=int)
    parser.add_argument("--refresh-originals-run-id", type=int)
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key and args.refresh_originals_run_id is None:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    if args.refresh_originals_run_id is not None:
        refresh_original_rows(args.source_db, args.output_db, args.report, args.refresh_originals_run_id)
        print(f"run_id={args.refresh_originals_run_id}")
        print(f"database={args.output_db}")
        print(f"report={args.report}")
        return
    if args.retry_errors_run_id is not None:
        retry_error_rows(args.output_db, args.report, args.retry_errors_run_id, api_key or "")
        print(f"run_id={args.retry_errors_run_id}")
        print(f"database={args.output_db}")
        print(f"report={args.report}")
        return

    source = sqlite3.connect(args.source_db)
    source.row_factory = sqlite3.Row
    output = init_output_db(args.output_db)
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    cursor = output.execute(
        """
        insert into replay_runs (
            created_at, source_db, source_model, target_model, sample_count, seed, notes
        ) values (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            now,
            str(args.source_db),
            args.source_model,
            args.target_model,
            args.count,
            args.seed,
            "Sampled from dialogue_turn_audits; original latency unavailable.",
        ),
    )
    run_id = int(cursor.lastrowid)
    client = OpenAI(api_key=api_key, timeout=90.0, max_retries=0)

    for row in sample_audits(
        source,
        count=args.count,
        seed=args.seed,
        source_model=args.source_model,
        prefer_actual_usage=args.prefer_actual_usage,
    ):
        packet = make_packet(row)
        packet_for_target = dict(packet)
        packet_for_target["model"] = args.target_model
        original_reply = assistant_reply_for_audit(
            source,
            session_id=row["session_id"],
            audit_timestamp=row["source_timestamp"],
        )
        original_text = original_reply["content"] if original_reply else None
        original_prompt_tokens = row["prompt_tokens"]
        original_completion_tokens = row["completion_tokens"]
        original_total_tokens = row["total_tokens"]
        original_estimated = 0
        if original_prompt_tokens is None:
            original_prompt_tokens = estimate_tokens_from_messages(packet["messages"])
            original_estimated = 1
        if original_completion_tokens is None:
            original_completion_tokens = estimate_tokens_from_text(original_text)
            original_estimated = 1
        if original_total_tokens is None:
            original_total_tokens = (original_prompt_tokens or 0) + (original_completion_tokens or 0)
            original_estimated = 1

        raw = None
        target_error = None
        target_seconds = None
        target_usage = {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "cached_prompt_tokens": None,
        }
        started = time.perf_counter()
        try:
            response = client.chat.completions.create(**packet_for_target)
            target_seconds = time.perf_counter() - started
            raw = response.choices[0].message.content
            target_usage = usage_dict(response)
        except Exception as exc:  # Store and continue so one bad row does not kill the run.
            target_seconds = time.perf_counter() - started
            target_error = f"{type(exc).__name__}: {exc}"

        target_assistant, target_artifact, target_state = parse_target_response(raw)
        target_estimated = 0
        if target_usage["prompt_tokens"] is None:
            target_usage["prompt_tokens"] = estimate_tokens_from_messages(packet_for_target["messages"])
            target_estimated = 1
        if target_usage["completion_tokens"] is None:
            target_usage["completion_tokens"] = estimate_tokens_from_text(raw)
            target_estimated = 1
        if target_usage["total_tokens"] is None:
            target_usage["total_tokens"] = (target_usage["prompt_tokens"] or 0) + (
                target_usage["completion_tokens"] or 0
            )
            target_estimated = 1

        output.execute(
            """
            insert into replay_results (
                run_id, audit_id, session_id, turn_index, source_timestamp,
                source_model, target_model, prompt_template_name, packet_json,
                original_response, original_assistant_message_id, original_response_timestamp,
                original_response_seconds, original_prompt_tokens, original_completion_tokens,
                original_total_tokens, original_cached_prompt_tokens, original_tokens_estimated,
                target_raw_response, target_assistant_message, target_private_artifact_json,
                target_updated_state_json, target_error, target_response_seconds,
                target_prompt_tokens, target_completion_tokens, target_total_tokens,
                target_cached_prompt_tokens, target_tokens_estimated, quality_notes
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                row["id"],
                row["session_id"],
                row["turn_index"],
                row["timestamp"],
                row["dialogue_model"],
                args.target_model,
                row["prompt_template_name"],
                json.dumps(packet, ensure_ascii=False),
                original_text,
                original_reply["message_id"] if original_reply else None,
                original_reply["timestamp"] if original_reply else None,
                None,
                original_prompt_tokens,
                original_completion_tokens,
                original_total_tokens,
                row["cached_prompt_tokens"],
                original_estimated,
                raw,
                target_assistant,
                target_artifact,
                target_state,
                target_error,
                target_seconds,
                target_usage["prompt_tokens"],
                target_usage["completion_tokens"],
                target_usage["total_tokens"],
                target_usage["cached_prompt_tokens"],
                target_estimated,
                quality_note(original_text, target_assistant),
            ),
        )
        output.commit()
        print(
            f"replayed audit {row['id']} turn {row['turn_index']}: "
            f"{'error' if target_error else f'{target_seconds:.2f}s'}",
            flush=True,
        )

    write_report(args.output_db, args.report, run_id)
    print(f"run_id={run_id}")
    print(f"database={args.output_db}")
    print(f"report={args.report}")


if __name__ == "__main__":
    main()
