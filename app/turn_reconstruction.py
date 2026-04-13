import json as j
from pathlib import Path

import sqlalchemy as sa
import sqlalchemy.orm as sqlalchemy_orm

import app.bot_engine as bot_engine
import app.config as config_module
import app.lecture_loader as lecture_loader
import app.models as models
import app.session_manager as session_manager

UNKNOWN_HISTORY_VALUE = "<UNRECOVERABLE_FROM_HISTORY>"
CURRENT_PROMPT_NOTE = (
    "Best-effort reconstruction uses the prompt templates currently on disk. "
    "If prompts changed after the session, this will not exactly match the historical prompt."
)

_UNKNOWN_RENDER_VARS = {
    "topics_covered": UNKNOWN_HISTORY_VALUE,
    "mastery": UNKNOWN_HISTORY_VALUE,
    "evidence_notes": UNKNOWN_HISTORY_VALUE,
    "current_topic_id": UNKNOWN_HISTORY_VALUE,
    "current_line_status": UNKNOWN_HISTORY_VALUE,
    "last_challenge_level": UNKNOWN_HISTORY_VALUE,
    "must_not_repeat": UNKNOWN_HISTORY_VALUE,
    "tutor_mode": UNKNOWN_HISTORY_VALUE,
    "recommended_action": UNKNOWN_HISTORY_VALUE,
    "target_topic_id": UNKNOWN_HISTORY_VALUE,
    "target_topic_label": UNKNOWN_HISTORY_VALUE,
    "challenge_level": UNKNOWN_HISTORY_VALUE,
    "challenge_label": UNKNOWN_HISTORY_VALUE,
    "reason_code": UNKNOWN_HISTORY_VALUE,
    "secondary_reason_code": UNKNOWN_HISTORY_VALUE,
    "action_must_not_repeat": UNKNOWN_HISTORY_VALUE,
    "source_scope_note": UNKNOWN_HISTORY_VALUE,
}


def _topic_id_to_label(lecture_package: dict) -> dict[str, str]:
    topic_defs = lecture_package.get("topics") or bot_engine.parse_rubric_topics(lecture_package["rubric"])
    return {t["topic_id"]: t["label"] for t in topic_defs}


def _sampled_labels_string(lecture_package: dict, topics_sampled: list[str]) -> str:
    topic_id_to_label = _topic_id_to_label(lecture_package)
    return ", ".join(topic_id_to_label.get(tid, tid) for tid in topics_sampled) or "all topics"


def _build_best_effort_rendered_prompt(
    settings: config_module.Settings,
    lecture_package: dict,
    prompt_template_name: str,
    topics_sampled: list[str],
    recent_messages: list[dict],
    turn_index: int,
) -> str:
    template = bot_engine._load_prompt(str(settings.prompt_dir), prompt_template_name)
    render_vars = dict(_UNKNOWN_RENDER_VARS)
    render_vars.update({
        "sampled_labels": _sampled_labels_string(lecture_package, topics_sampled),
        "recent_messages": bot_engine._format_messages_for_prompt(recent_messages),
        "turn_count": turn_index + 1,
        "lecture_title": lecture_package["config"].get("title", lecture_package["lecture_id"]),
    })
    if prompt_template_name == "tutor_prompt.md":
        render_vars["rubric_text"] = lecture_package["rubric"]
        render_vars["context"] = bot_engine.build_dialogue_context(lecture_package, settings.max_dialogue_context_chars)
    return bot_engine._render_prompt(template, **render_vars)


def _replay_routing_state(
    lecture_package: dict,
    topics_sampled: list[str],
    prior_logs: list[models.ClassificationLogModel],
) -> dict:
    state = session_manager.build_initial_state(lecture_package, topics_sampled)
    for row in prior_logs:
        classification = bot_engine.ClassifierResult.model_validate(j.loads(row.classifier_json))
        policy_decision = bot_engine.PolicyDecision.model_validate(j.loads(row.policy_decision_json))
        old_state = dict(state)
        bot_engine._apply_routing_state(state, classification, policy_decision, old_state)
        state["turn_count"] = old_state.get("turn_count", 0) + 1
    return state


def reconstruct_session_turn_inputs(
    db: sqlalchemy_orm.Session,
    session_id: str,
) -> dict:
    settings = config_module.get_settings()
    session = (
        db.query(models.SessionModel)
        .filter(models.SessionModel.session_id == session_id)
        .first()
    )
    if not session:
        raise ValueError(f"Session not found: {session_id}")

    lecture_package = lecture_loader.load_lecture_package(settings.lectures_dir, session.lecture_id)
    final_state = session_manager.load_state(db, session_id)
    topics_sampled = final_state.get("topics_sampled", [])

    message_rows = (
        db.query(models.MessageModel)
        .filter(models.MessageModel.session_id == session_id)
        .order_by(models.MessageModel.id.asc())
        .all()
    )
    serialized_messages = bot_engine.serialize_messages(message_rows)
    user_positions = [i for i, m in enumerate(serialized_messages) if m["role"] == "user"]

    classification_rows = (
        db.query(models.ClassificationLogModel)
        .filter(models.ClassificationLogModel.session_id == session_id)
        .order_by(models.ClassificationLogModel.turn_index.asc())
        .all()
    )
    logs_by_turn = {row.turn_index: row for row in classification_rows}

    inspector = sa.inspect(db.get_bind())
    if inspector.has_table(models.DialogueTurnAuditModel.__tablename__):
        audit_rows = (
            db.query(models.DialogueTurnAuditModel)
            .filter(models.DialogueTurnAuditModel.session_id == session_id)
            .order_by(models.DialogueTurnAuditModel.turn_index.asc())
            .all()
        )
    else:
        audit_rows = []
    audits_by_turn = {row.turn_index: row for row in audit_rows}

    turns = []
    prior_logs: list[models.ClassificationLogModel] = []
    for turn_index, message_pos in enumerate(user_positions):
        user_message = serialized_messages[message_pos]["content"]
        recent_messages = serialized_messages[max(0, message_pos - settings.recent_message_limit):message_pos]
        log_row = logs_by_turn.get(turn_index)
        if log_row is None:
            continue
        classifier = j.loads(log_row.classifier_json)
        policy_decision = j.loads(log_row.policy_decision_json)
        effective_policy = policy_decision["effective_policy"]
        prompt_template_name = bot_engine._prompt_template_name_for_policy(effective_policy)

        audit_row = audits_by_turn.get(turn_index)
        if audit_row is not None:
            prompt_kind = "exact_from_audit"
            rendered_prompt = audit_row.rendered_system_prompt
            state_before = j.loads(audit_row.state_before_json)
            reconstruction_note = "Exact prompt reconstructed from stored dialogue turn audit."
            unrecoverable_fields: list[str] = []
        elif turn_index == 0:
            prompt_kind = "exact_initial_turn"
            state_before = session_manager.build_initial_state(lecture_package, topics_sampled)
            classification = bot_engine.ClassifierResult.model_validate(classifier)
            action_hint = bot_engine._compute_action_hint(state_before, lecture_package, recent_messages, user_message)
            rendered_prompt = bot_engine._build_system_prompt(
                settings,
                effective_policy,
                lecture_package,
                state_before,
                recent_messages,
                bot_engine._tutor_mode_for_turn(classification, effective_policy),
                action_hint,
            )
            reconstruction_note = "Exact prompt reconstructed from deterministic initial state."
            unrecoverable_fields = []
        else:
            prompt_kind = "best_effort_current_prompts"
            state_before = _replay_routing_state(lecture_package, topics_sampled, prior_logs)
            rendered_prompt = _build_best_effort_rendered_prompt(
                settings,
                lecture_package,
                prompt_template_name,
                topics_sampled,
                recent_messages,
                turn_index,
            )
            reconstruction_note = CURRENT_PROMPT_NOTE
            unrecoverable_fields = sorted(_UNKNOWN_RENDER_VARS)

        turns.append({
            "turn_index": turn_index,
            "user_message": user_message,
            "recent_messages": recent_messages,
            "classifier": classifier,
            "policy_decision": policy_decision,
            "effective_policy": effective_policy,
            "prompt_template_name": prompt_template_name,
            "prompt_reconstruction_kind": prompt_kind,
            "reconstruction_note": reconstruction_note,
            "routing_state_before_turn_exact": {
                "last_top_classification": state_before.get("last_top_classification"),
                "last_recommended_policy": state_before.get("last_recommended_policy"),
                "last_effective_policy": state_before.get("last_effective_policy"),
                "consecutive_redirects": state_before.get("consecutive_redirects"),
                "consecutive_meta_requests": state_before.get("consecutive_meta_requests"),
                "consecutive_clarifications": state_before.get("consecutive_clarifications"),
                "last_policy_override_reason": state_before.get("last_policy_override_reason"),
                "turn_count": state_before.get("turn_count"),
            },
            "unrecoverable_prompt_fields": unrecoverable_fields,
            "rendered_system_prompt": rendered_prompt,
        })
        prior_logs.append(log_row)

    return {
        "session_id": session.session_id,
        "lecture_id": session.lecture_id,
        "lecture_title": lecture_package["config"].get("title", lecture_package["lecture_id"]),
        "sampled_topics": topics_sampled,
        "turns": turns,
    }


def export_session_turn_inputs_json(
    db: sqlalchemy_orm.Session,
    session_id: str,
    output_path: str | Path,
) -> Path:
    output = Path(output_path)
    packet = reconstruct_session_turn_inputs(db, session_id)
    output.write_text(j.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
