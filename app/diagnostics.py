import json as j
import re as re_
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import sqlalchemy.orm as sqlalchemy_orm

import app.bot_engine as bot_engine
import app.config as config_module
import app.lecture_loader as lecture_loader
import app.models as models

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "can", "could", "data", "did",
    "do", "does", "for", "from", "get", "give", "how", "i", "if", "in", "is", "it", "like",
    "me", "my", "of", "on", "or", "so", "study", "that", "the", "their", "them", "then",
    "there", "they", "this", "to", "using", "what", "when", "which", "why", "with", "would",
    "you", "your",
}
_ACK_RE = re_.compile(r"^(yes|right|correct|exactly|that's right|you had the right idea)\b", re_.IGNORECASE)
_STRONG_ANSWER_RE = re_.compile(r"\b(because|since|so that|rather than|therefore|which means)\b", re_.IGNORECASE)
_LEVEL_PATTERNS: list[tuple[int, list[re_.Pattern[str]]]] = [
    (7, [re_.compile(r"\b(critique|correct this|what is wrong with|fix the mistake)\b", re_.IGNORECASE)]),
    (6, [re_.compile(r"\b(what does that imply|how would you interpret|practical meaning|in practice)\b", re_.IGNORECASE)]),
    (5, [re_.compile(r"\b(suppose|if a study|if the study|fresh case|apply|transfer|how would)\b", re_.IGNORECASE)]),
    (4, [re_.compile(r"\b(why|one reason|how does|what makes)\b", re_.IGNORECASE)]),
    (3, [re_.compile(r"\b(difference|distinction|contrast|versus|vs\.?)\b", re_.IGNORECASE)]),
    (2, [re_.compile(r"\b(define|definition|what does .* mean|criterion)\b", re_.IGNORECASE)]),
    (1, [re_.compile(r"\b(which of these|which are|what type|name|is that|categorical|continuous|ordinal)\b", re_.IGNORECASE)]),
]
_SOURCE_TERMS = tuple(bot_engine._SOURCE_BOUNDED_REPLACEMENTS.keys())


@dataclass
class DiagnosticTurnRecord:
    session_id: str
    lecture_id: str
    lecture_title: str
    turn_index: int
    user_message: str
    assistant_message: str
    recent_messages: list[dict]
    classifier: dict | None
    policy_decision: dict | None
    effective_policy: str | None
    prompt_template_name: str | None
    tutor_mode: str | None
    action_hint: dict
    challenge_level: int | None
    current_topic_id: str | None
    target_topic_id: str | None
    ended_with_content_question: bool
    repetition_complaint: bool
    switched_topics: bool


@dataclass
class DiagnosticCase:
    kind: str
    session_id: str
    lecture_id: str
    turn_index: int
    score: str
    likely_cause: str
    evidence: list[str]
    user_message: str
    assistant_message: str
    effective_policy: str | None
    tutor_mode: str | None
    current_topic_id: str | None
    target_topic_id: str | None
    action_hint: dict
    realized_question_level: int | None


@dataclass
class SessionDiagnosticReport:
    session_id: str
    lecture_id: str
    lecture_title: str
    user_turns: int
    case_counts: dict[str, dict[str, int]]
    cause_counts: dict[str, int]
    session_metrics: dict[str, object]
    cases: list[DiagnosticCase]


def _tokenize(text: str) -> list[str]:
    return [
        token for token in re_.findall(r"[a-z0-9]+", text.lower())
        if token not in _STOPWORDS and len(token) > 1
    ]


def _first_question(text: str) -> str:
    if "?" not in text:
        return ""
    return text.split("?", 1)[0].strip() + "?"


def guess_question_level(text: str) -> int | None:
    question = _first_question(text) or text.strip()
    if not question:
        return None
    for level, patterns in _LEVEL_PATTERNS:
        if any(pattern.search(question) for pattern in patterns):
            return level
    if question.endswith("?"):
        return 3
    return None


def is_near_duplicate_question(previous_text: str, current_text: str) -> bool:
    previous_question = _first_question(previous_text)
    current_question = _first_question(current_text)
    if not previous_question or not current_question:
        return False
    previous_tokens = set(_tokenize(previous_question))
    current_tokens = set(_tokenize(current_question))
    if not previous_tokens or not current_tokens:
        return False
    overlap = len(previous_tokens & current_tokens) / len(previous_tokens | current_tokens)
    return overlap >= 0.55


def detect_external_terms(assistant_message: str, user_message: str, lecture_package: dict) -> list[str]:
    lecture_terms = bot_engine._lecture_terms_blob(lecture_package)
    student_terms = user_message.lower()
    lowered = assistant_message.lower()
    found: list[str] = []
    for term in _SOURCE_TERMS:
        if term in lecture_terms or term in student_terms:
            continue
        if term in lowered:
            found.append(term)
    return found


def build_session_turn_records(
    db: sqlalchemy_orm.Session,
    session_id: str,
) -> tuple[dict, list[DiagnosticTurnRecord]]:
    settings = config_module.get_settings()
    session = (
        db.query(models.SessionModel)
        .filter(models.SessionModel.session_id == session_id)
        .first()
    )
    if not session:
        raise ValueError(f"Session not found: {session_id}")

    lecture_package = lecture_loader.load_lecture_package(settings.lectures_dir, session.lecture_id)
    lecture_title = lecture_package["config"].get("title", lecture_package["lecture_id"])

    message_rows = (
        db.query(models.MessageModel)
        .filter(models.MessageModel.session_id == session_id)
        .order_by(models.MessageModel.id.asc())
        .all()
    )
    messages = bot_engine.serialize_messages(message_rows)

    user_positions = [idx for idx, message in enumerate(messages) if message["role"] == "user"]
    classification_rows = (
        db.query(models.ClassificationLogModel)
        .filter(models.ClassificationLogModel.session_id == session_id)
        .order_by(models.ClassificationLogModel.turn_index.asc())
        .all()
    )
    logs_by_turn = {row.turn_index: row for row in classification_rows}
    audit_rows = (
        db.query(models.DialogueTurnAuditModel)
        .filter(models.DialogueTurnAuditModel.session_id == session_id)
        .order_by(models.DialogueTurnAuditModel.turn_index.asc())
        .all()
    )
    audits_by_turn = {row.turn_index: row for row in audit_rows}

    turn_records: list[DiagnosticTurnRecord] = []
    for turn_index, user_pos in enumerate(user_positions):
        user_message = messages[user_pos]["content"]
        assistant_message = ""
        for later in messages[user_pos + 1:]:
            if later["role"] == "assistant":
                assistant_message = later["content"]
                break

        recent_messages = messages[max(0, user_pos - settings.recent_message_limit):user_pos]
        log_row = logs_by_turn.get(turn_index)
        audit_row = audits_by_turn.get(turn_index)

        classifier = j.loads(log_row.classifier_json) if log_row else None
        policy_decision = j.loads(log_row.policy_decision_json) if log_row else None
        action_hint = j.loads(audit_row.action_hint_json) if audit_row and audit_row.action_hint_json else {}
        effective_policy = audit_row.effective_policy if audit_row else (policy_decision or {}).get("effective_policy")
        prompt_template_name = audit_row.prompt_template_name if audit_row else (
            bot_engine._prompt_template_name_for_policy(effective_policy) if effective_policy else None
        )

        turn_records.append(
            DiagnosticTurnRecord(
                session_id=session_id,
                lecture_id=session.lecture_id,
                lecture_title=lecture_title,
                turn_index=turn_index,
                user_message=user_message,
                assistant_message=assistant_message,
                recent_messages=recent_messages,
                classifier=classifier,
                policy_decision=policy_decision,
                effective_policy=effective_policy,
                prompt_template_name=prompt_template_name,
                tutor_mode=getattr(audit_row, "tutor_mode", None),
                action_hint=action_hint,
                challenge_level=getattr(audit_row, "challenge_level", None),
                current_topic_id=getattr(audit_row, "current_topic_id", None),
                target_topic_id=getattr(audit_row, "target_topic_id", None),
                ended_with_content_question=bool(getattr(audit_row, "ended_with_content_question", False)),
                repetition_complaint=bool(getattr(audit_row, "repetition_complaint", False)),
                switched_topics=bool(getattr(audit_row, "switched_topics", False)),
            )
        )

    return lecture_package, turn_records


def _append_case(
    cases: list[DiagnosticCase],
    record: DiagnosticTurnRecord,
    kind: str,
    score: str,
    likely_cause: str,
    evidence: list[str],
) -> None:
    cases.append(
        DiagnosticCase(
            kind=kind,
            session_id=record.session_id,
            lecture_id=record.lecture_id,
            turn_index=record.turn_index,
            score=score,
            likely_cause=likely_cause,
            evidence=evidence,
            user_message=record.user_message,
            assistant_message=record.assistant_message,
            effective_policy=record.effective_policy,
            tutor_mode=record.tutor_mode,
            current_topic_id=record.current_topic_id,
            target_topic_id=record.target_topic_id,
            action_hint=record.action_hint,
            realized_question_level=guess_question_level(record.assistant_message),
        )
    )


def diagnose_turn_records(lecture_package: dict, turn_records: list[DiagnosticTurnRecord]) -> SessionDiagnosticReport:
    cases: list[DiagnosticCase] = []
    near_duplicate_pairs = 0
    source_drift_turns = 0
    high_challenge_turns = 0
    switched_topic_turns = 0
    topics_targeted: set[str] = set()

    for index, record in enumerate(turn_records):
        action_hint = record.action_hint or {}
        realized_level = guess_question_level(record.assistant_message)
        if (record.challenge_level or 0) >= 5:
            high_challenge_turns += 1
        if record.switched_topics:
            switched_topic_turns += 1
        if record.target_topic_id:
            topics_targeted.add(record.target_topic_id)
        elif record.current_topic_id:
            topics_targeted.add(record.current_topic_id)

        if bot_engine._REQUEST_HARDER_RE.search(record.user_message):
            backend_ok = (
                action_hint.get("recommended_action") in {"escalate", "switch"}
                and int(action_hint.get("challenge_level", 0) or 0) >= 5
            )
            realization_ok = (realized_level or 0) >= 5
            evidence = [
                f"action={action_hint.get('recommended_action') or 'none'}",
                f"hint_level={action_hint.get('challenge_level') or 'none'}",
                f"realized_level={realized_level or 'none'}",
            ]
            if not backend_ok:
                _append_case(cases, record, "harder_request", "fail", "backend_action_hint", evidence)
            elif not realization_ok:
                _append_case(cases, record, "harder_request", "fail", "tutor_realization", evidence)
            else:
                _append_case(cases, record, "harder_request", "pass", "none", evidence)

        if bot_engine._REPETITION_COMPLAINT_RE.search(record.user_message):
            previous_assistant = turn_records[index - 1].assistant_message if index > 0 else ""
            duplicate = is_near_duplicate_question(previous_assistant, record.assistant_message)
            backend_ok = action_hint.get("recommended_action") in {"repair", "switch", "escalate"}
            evidence = [
                f"action={action_hint.get('recommended_action') or 'none'}",
                f"near_duplicate={duplicate}",
            ]
            if not backend_ok:
                _append_case(cases, record, "repetition_complaint", "fail", "backend_action_hint", evidence)
            elif duplicate:
                _append_case(cases, record, "repetition_complaint", "fail", "tutor_realization", evidence)
            else:
                _append_case(cases, record, "repetition_complaint", "pass", "none", evidence)

        if bot_engine._REQUEST_SWITCH_RE.search(record.user_message):
            backend_ok = action_hint.get("recommended_action") == "switch"
            realization_ok = record.switched_topics or (
                record.current_topic_id is not None and record.current_topic_id != record.target_topic_id
            ) or bool(record.target_topic_id)
            evidence = [
                f"action={action_hint.get('recommended_action') or 'none'}",
                f"target_topic={record.target_topic_id or 'none'}",
                f"switched={record.switched_topics}",
            ]
            if not backend_ok:
                _append_case(cases, record, "switch_request", "fail", "backend_action_hint", evidence)
            elif not realization_ok:
                _append_case(cases, record, "switch_request", "fail", "tutor_realization", evidence)
            else:
                _append_case(cases, record, "switch_request", "pass", "none", evidence)

        if record.effective_policy == "provide_technical_support":
            if bot_engine._REQUEST_HARDER_RE.search(record.user_message) or bot_engine._REQUEST_SWITCH_RE.search(record.user_message) or bot_engine._REQUEST_HINT_RE.search(record.user_message):
                moved_forward = record.ended_with_content_question
                narrated = any(pattern.search(record.assistant_message) for pattern in bot_engine._MOVE_NARRATION_PATTERNS)
                evidence = [
                    f"ended_with_content_question={record.ended_with_content_question}",
                    f"move_narration={narrated}",
                ]
                if not moved_forward or narrated:
                    _append_case(cases, record, "steering_reentry", "fail", "tutor_realization", evidence)
                else:
                    _append_case(cases, record, "steering_reentry", "pass", "none", evidence)

        external_terms = detect_external_terms(record.assistant_message, record.user_message, lecture_package)
        if external_terms:
            source_drift_turns += 1
            _append_case(
                cases,
                record,
                "source_drift",
                "fail",
                "tutor_realization",
                [f"external_terms={', '.join(external_terms)}"],
            )

        if index > 0:
            previous = turn_records[index - 1]
            duplicate = is_near_duplicate_question(previous.assistant_message, record.assistant_message)
            if duplicate:
                near_duplicate_pairs += 1
                same_topic = (
                    previous.target_topic_id == record.target_topic_id
                    or previous.current_topic_id == record.current_topic_id
                )
                if same_topic:
                    action = action_hint.get("recommended_action")
                    cause = "tutor_realization" if action in {"switch", "escalate", "repair"} else "backend_action_hint"
                    _append_case(
                        cases,
                        record,
                        "near_duplicate_followup",
                        "fail",
                        cause,
                        [
                            f"action={action or 'none'}",
                            f"previous_question={_first_question(previous.assistant_message)}",
                            f"current_question={_first_question(record.assistant_message)}",
                        ],
                    )

        strong_student_answer = len(record.user_message.split()) >= 10 or bool(_STRONG_ANSWER_RE.search(record.user_message))
        if strong_student_answer and _ACK_RE.search(record.assistant_message):
            if realized_level is not None and realized_level <= min(int(action_hint.get("challenge_level", 3) or 3), 3):
                cause = "tutor_realization" if int(action_hint.get("challenge_level", 0) or 0) >= 4 else "backend_action_hint"
                _append_case(
                    cases,
                    record,
                    "weak_stop_condition",
                    "fail",
                    cause,
                    [
                        f"hint_level={action_hint.get('challenge_level') or 'none'}",
                        f"realized_level={realized_level}",
                        "assistant_acknowledged_strong_answer=True",
                    ],
                )

    case_counter: dict[str, dict[str, int]] = {}
    by_kind: dict[str, Counter] = {}
    cause_counts: Counter = Counter()
    for case in cases:
        by_kind.setdefault(case.kind, Counter())[case.score] += 1
        cause_counts[case.likely_cause] += 1
    for kind, counter in by_kind.items():
        case_counter[kind] = dict(counter)

    report = SessionDiagnosticReport(
        session_id=turn_records[0].session_id if turn_records else "",
        lecture_id=turn_records[0].lecture_id if turn_records else "",
        lecture_title=turn_records[0].lecture_title if turn_records else "",
        user_turns=len(turn_records),
        case_counts=case_counter,
        cause_counts=dict(cause_counts),
        session_metrics={
            "topics_targeted": sorted(topics_targeted),
            "high_challenge_turns": high_challenge_turns,
            "source_drift_turns": source_drift_turns,
            "near_duplicate_pairs": near_duplicate_pairs,
            "switched_topic_turns": switched_topic_turns,
            "content_question_turns": sum(1 for record in turn_records if record.ended_with_content_question),
        },
        cases=cases,
    )
    return report


def report_to_dict(report: SessionDiagnosticReport) -> dict:
    return {
        "session_id": report.session_id,
        "lecture_id": report.lecture_id,
        "lecture_title": report.lecture_title,
        "user_turns": report.user_turns,
        "case_counts": report.case_counts,
        "cause_counts": report.cause_counts,
        "session_metrics": report.session_metrics,
        "cases": [asdict(case) for case in report.cases],
    }


def render_markdown_report(report: SessionDiagnosticReport) -> str:
    lines = [
        f"# Diagnostics for {report.session_id}",
        "",
        f"- Lecture: `{report.lecture_id}` ({report.lecture_title})",
        f"- User turns: `{report.user_turns}`",
        "",
        "## Session metrics",
        "",
    ]
    for key, value in report.session_metrics.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Case counts", ""])
    for kind, counts in sorted(report.case_counts.items()):
        counts_text = ", ".join(f"{score}={count}" for score, count in sorted(counts.items()))
        lines.append(f"- `{kind}`: {counts_text}")
    lines.extend(["", "## Likely causes", ""])
    for cause, count in sorted(report.cause_counts.items()):
        lines.append(f"- `{cause}`: `{count}`")
    lines.extend(["", "## Cases", ""])
    for case in report.cases:
        lines.append(f"### {case.kind} turn {case.turn_index}")
        lines.append(f"- score: `{case.score}`")
        lines.append(f"- likely_cause: `{case.likely_cause}`")
        lines.append(f"- effective_policy: `{case.effective_policy}`")
        lines.append(f"- tutor_mode: `{case.tutor_mode}`")
        lines.append(f"- realized_question_level: `{case.realized_question_level}`")
        if case.evidence:
            lines.append(f"- evidence: {'; '.join(case.evidence)}")
        lines.append(f"- user: {case.user_message}")
        lines.append(f"- assistant: {case.assistant_message}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export_session_diagnostics(
    db: sqlalchemy_orm.Session,
    session_id: str,
    *,
    output_json: str | Path | None = None,
    output_markdown: str | Path | None = None,
) -> SessionDiagnosticReport:
    lecture_package, turn_records = build_session_turn_records(db, session_id)
    report = diagnose_turn_records(lecture_package, turn_records)
    if output_json is not None:
        json_path = Path(output_json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(j.dumps(report_to_dict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    if output_markdown is not None:
        md_path = Path(output_markdown)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(render_markdown_report(report), encoding="utf-8")
    return report
