import functools as functools_
import json as j_
import logging as logging_
import math as math_
import pathlib as pathlib_
import random as random_
import re as re_

import openai as openai_
import sqlalchemy.orm as sqlalchemy_orm_

import app.config as config_module
import app.models as models_module
import app.session_manager as session_manager_module
from app.policy_decider import HARD_BACKSTOP_PATTERNS, PolicyDecider
from app.schema import (
    ClassifierInput,
    ClassifierMessage,
    ClassifierResult,
    ClassifierStateExcerpt,
    PolicyDecision,
)

_log = logging_.getLogger(__name__)

_GRADE_WEIGHTS = [55, 25, 13, 4, 3]

_TOPIC_SECTION_RE = re_.compile(r'^### (T\d+)\.\s+(.+)$', re_.MULTILINE)
_IMPORTANCE_RE = re_.compile(r'\*\*Importance:\*\*\s+(\w+)')

_FALLBACK_DIALOGUE_MESSAGE = (
    "I'm having trouble updating the tutoring state cleanly. "
    "Let's keep going with one focused question: "
    "what idea from this lecture seems most important to you, and why?"
)

# ---------------------------------------------------------------------------
# Policy routing constants and helpers
# ---------------------------------------------------------------------------

_POLICY_TO_PROMPT: dict[str, str] = {
    "respond": "tutor_prompt.md",
    "provide_content_support": "tutor_prompt.md",
    "provide_technical_support": "tutor_prompt.md",
    "redirect": "redirect_prompt.md",
    "seek_clarification": "tutor_prompt.md",
}

# These policies receive lecture content and rubric text in their prompts.
_CONTENT_POLICIES: frozenset[str] = frozenset({"respond", "provide_content_support", "provide_technical_support", "seek_clarification"})

# Matches {identifier} placeholders while leaving {}, {"key": value}, etc. intact.
_TEMPLATE_VAR_RE = re_.compile(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}')
_ALLOWED_LINE_STATUSES = {"productive", "low_yield", "needs_repair", "ready_to_wrap", "unclear"}
_MAX_MUST_NOT_REPEAT_ITEMS = 4
_MAX_MUST_NOT_REPEAT_ITEM_LEN = 120
_CHALLENGE_LABELS = {
    1: "recognition / naming",
    2: "criterion / definition",
    3: "distinction / contrast",
    4: "explanation / why",
    5: "application / transfer",
    6: "practical interpretation",
    7: "independent correction / critique",
}
_MOVE_NARRATION_PATTERNS = [
    re_.compile(r"\bthe next move is\b", re_.IGNORECASE),
    re_.compile(r"\bthe next step is\b", re_.IGNORECASE),
    re_.compile(r"\bthe most useful next step is\b", re_.IGNORECASE),
    re_.compile(r"\bthe clean next move (?:is|would be)\b", re_.IGNORECASE),
    re_.compile(r"\bthe most useful question\b", re_.IGNORECASE),
    re_.compile(r"\bif you want[,]?\s+i can\b", re_.IGNORECASE),
    re_.compile(r"\bwe can use\b", re_.IGNORECASE),
]
_PROCEDURAL_QUESTION_PATTERNS = [
    re_.compile(r"\bwould you like\b", re_.IGNORECASE),
    re_.compile(r"\bdo you want\b", re_.IGNORECASE),
    re_.compile(r"\bready for\b", re_.IGNORECASE),
    re_.compile(r"\bswitch topics\b", re_.IGNORECASE),
    re_.compile(r"\bmove on\b", re_.IGNORECASE),
]
_SOURCE_BOUNDED_REPLACEMENTS = {
    "posterior kernel": "prior × likelihood before normalization",
    "unnormalized posterior": "prior × likelihood before normalization",
    "normalizing constant": "evidence",
}
_REPETITION_COMPLAINT_RE = re_.compile(
    r"(repeating yourself|same question|not again|what (?:exactly )?was missing|what was missing|already said|asked .* again)",
    re_.IGNORECASE,
)
_REQUEST_HARDER_RE = re_.compile(r"(harder|get me points|most likely to improve my grade|most useful question|too easy|high[- ]value)", re_.IGNORECASE)
_REQUEST_SWITCH_RE = re_.compile(r"\b(switch topics|switch topic|move on|different topic|fresh topic|other topics?)\b", re_.IGNORECASE)
_REQUEST_HINT_RE = re_.compile(r"\b(hint|what are you trying to get at|what do you mean|what am i missing)\b", re_.IGNORECASE)


def _prompt_template_name_for_policy(effective_policy: str) -> str:
    return _POLICY_TO_PROMPT[effective_policy]


@functools_.lru_cache(maxsize=32)
def _load_prompt(prompt_dir_str: str, filename: str) -> str:
    """Load and cache a prompt file from disk."""
    return (pathlib_.Path(prompt_dir_str) / filename).read_text(encoding="utf-8")


@functools_.lru_cache(maxsize=1)
def _get_policy_decider() -> PolicyDecider:
    settings = config_module.get_settings()
    return PolicyDecider(
        hard_backstops=HARD_BACKSTOP_PATTERNS,
        top1_min=settings.policy_top1_min,
        top2_trigger=settings.policy_top2_trigger,
        ambiguity_gap_max=settings.policy_ambiguity_gap_max,
        clarification_redirect_threshold=settings.clarification_redirect_threshold,
    )


def _render_prompt(template: str, **kwargs: object) -> str:
    """Substitute {name} placeholders; leave unrecognised ones intact."""
    def _replace(m: re_.Match) -> str:
        key = m.group(1)
        return str(kwargs[key]) if key in kwargs else m.group(0)
    return _TEMPLATE_VAR_RE.sub(_replace, template)


def _format_messages_for_prompt(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        role_label = "Student" if m["role"] == "user" else "Tutor"
        lines.append(f"[{role_label}]: {m['content']}")
    return "\n".join(lines)


def _format_must_not_repeat(value: object) -> str:
    if not isinstance(value, list):
        return "none"
    cleaned = []
    for item in value:
        if isinstance(item, str):
            text = " ".join(item.split()).strip()
            if text:
                cleaned.append(text)
    return " | ".join(cleaned) if cleaned else "none"


def _sanitize_must_not_repeat(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        text = " ".join(item.split()).strip()[:_MAX_MUST_NOT_REPEAT_ITEM_LEN]
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
        if len(cleaned) >= _MAX_MUST_NOT_REPEAT_ITEMS:
            break
    return cleaned


def _challenge_label(level: int) -> str:
    return _CHALLENGE_LABELS.get(level, _CHALLENGE_LABELS[3])


def _clamp_challenge_level(value: object, default: int = 3) -> int:
    try:
        level = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(7, level))


def _topic_importance_bonus(topic_id: str, topic_defs: list[dict]) -> int:
    for topic in topic_defs:
        if topic["topic_id"] != topic_id:
            continue
        importance = topic.get("importance", "unknown")
        if importance == "core":
            return 2
        if importance == "important":
            return 1
    return 0


def _student_turn_flags(user_message: str, recent_messages: list[dict]) -> dict[str, bool]:
    text = user_message.lower()
    last_assistant = ""
    for message in reversed(recent_messages):
        if message["role"] == "assistant":
            last_assistant = message["content"].lower()
            break
    return {
        "requested_switch": bool(_REQUEST_SWITCH_RE.search(text)),
        "requested_harder": bool(_REQUEST_HARDER_RE.search(text)),
        "requested_hint": bool(_REQUEST_HINT_RE.search(text)),
        "repetition_complaint": bool(_REPETITION_COMPLAINT_RE.search(text)),
        "explicitly_procedural_only": "just answer the procedural part" in text or "purely procedural" in text,
        "offered_options_recently": "which would you like" in last_assistant or "a few good places to start" in last_assistant,
    }


def _pick_switch_target(
    state: dict,
    topic_defs: list[dict],
    *,
    exclude_topic_id: str | None = None,
) -> str | None:
    topics_sampled = [topic["topic_id"] for topic in topic_defs if topic["topic_id"] in state.get("topics_sampled", [])]
    topics_covered = set(state.get("topics_covered", []))
    mastery = state.get("mastery", {})

    best_topic_id = None
    best_score = -10**9
    for topic_id in topics_sampled:
        if topic_id == exclude_topic_id:
            continue
        topic_score = 0
        if topic_id not in topics_covered:
            topic_score += 12
        topic_score += _topic_importance_bonus(topic_id, topic_defs) * 3
        topic_score += max(0, 6 - int(mastery.get(topic_id, 0) // 20))
        if topic_score > best_score:
            best_score = topic_score
            best_topic_id = topic_id
    return best_topic_id


def _action_base_level(current_mastery: int) -> int:
    if current_mastery >= 90:
        return 7
    if current_mastery >= 75:
        return 6
    if current_mastery >= 60:
        return 5
    if current_mastery >= 40:
        return 4
    if current_mastery >= 20:
        return 3
    return 2


def _compute_action_hint(
    state: dict,
    lecture_package: dict,
    recent_messages: list[dict],
    user_message: str,
) -> dict:
    topic_defs = lecture_package.get("topics") or parse_rubric_topics(lecture_package["rubric"])
    current_topic_id = state.get("current_topic_id")
    current_mastery = 0
    if isinstance(current_topic_id, str):
        current_mastery = int(state.get("mastery", {}).get(current_topic_id, 0))
    line_status = state.get("current_line_status", "unclear")
    flags = _student_turn_flags(user_message, recent_messages)
    target_topic_id = _pick_switch_target(state, topic_defs, exclude_topic_id=current_topic_id)
    must_not_repeat = list(state.get("must_not_repeat", []))

    if flags["repetition_complaint"]:
        must_not_repeat.append("do not ask the same question again")
    if flags["requested_harder"]:
        must_not_repeat.append("do not fall back to a recognition-only check")
    if flags["requested_switch"]:
        must_not_repeat.append("do not stay on the old topic")
    if flags["offered_options_recently"]:
        must_not_repeat.append("do not offer another topic menu")
    must_not_repeat = _sanitize_must_not_repeat(must_not_repeat)

    recommended_action = "stay"
    reason_code = "easy_points_available"
    secondary_reason_code = None
    chosen_target = current_topic_id or target_topic_id

    if flags["requested_switch"] and target_topic_id:
        recommended_action = "switch"
        chosen_target = target_topic_id
        reason_code = "student_requested_switch"
    elif flags["repetition_complaint"]:
        if target_topic_id and (current_mastery >= 60 or line_status in {"low_yield", "needs_repair", "ready_to_wrap"}):
            recommended_action = "switch"
            chosen_target = target_topic_id
            reason_code = "current_line_low_yield"
            secondary_reason_code = "student_reported_repetition"
        else:
            recommended_action = "repair"
            chosen_target = current_topic_id
            reason_code = "repair_after_repeat"
    elif flags["requested_harder"]:
        if current_topic_id and line_status == "productive":
            recommended_action = "escalate"
            chosen_target = current_topic_id
            reason_code = "student_requested_harder"
        elif target_topic_id:
            recommended_action = "switch"
            chosen_target = target_topic_id
            reason_code = "high_weight_open_topic"
            secondary_reason_code = "student_requested_harder"
    elif current_topic_id and current_mastery >= 80:
        if target_topic_id:
            recommended_action = "switch"
            chosen_target = target_topic_id
            reason_code = "high_weight_open_topic"
        else:
            recommended_action = "wrap"
            chosen_target = current_topic_id
            reason_code = "criterion_reached"
    elif current_topic_id and line_status in {"low_yield", "needs_repair"} and target_topic_id:
        recommended_action = "switch"
        chosen_target = target_topic_id
        reason_code = "current_line_low_yield"
    elif current_topic_id and current_mastery >= 55:
        recommended_action = "escalate"
        chosen_target = current_topic_id
        reason_code = "needs_transfer_check"
    elif not current_topic_id and target_topic_id:
        recommended_action = "switch"
        chosen_target = target_topic_id
        reason_code = "high_weight_open_topic"
    elif line_status == "needs_repair":
        recommended_action = "repair"
        chosen_target = current_topic_id
        reason_code = "repair_after_repeat"

    base_level = _action_base_level(current_mastery)
    if recommended_action == "switch":
        challenge_level = 5 if flags["requested_harder"] else max(3, min(5, base_level))
    elif recommended_action == "escalate":
        challenge_level = max(base_level + 1, 5 if flags["requested_harder"] else base_level)
    elif recommended_action == "repair":
        challenge_level = max(3, min(4, base_level))
    elif recommended_action == "wrap":
        challenge_level = max(5, base_level)
    else:
        challenge_level = base_level

    return {
        "recommended_action": recommended_action,
        "target_topic_id": chosen_target,
        "challenge_level": max(state.get("last_challenge_level", 1), 1) if flags["explicitly_procedural_only"] else _clamp_challenge_level(challenge_level),
        "reason_code": reason_code,
        "secondary_reason_code": secondary_reason_code,
        "must_not_repeat": must_not_repeat,
        "source_scope_note": (
            "Use lecture-native terminology only. Do not import outside textbook language, alternate conventions, "
            "or stronger framings unless they clearly appear in the lecture materials."
        ),
        "flags": flags,
    }


def _tutor_mode_for_turn(classification: ClassifierResult, effective_policy: str) -> str:
    if effective_policy == "seek_clarification":
        return "ambiguous_but_continue"
    if classification.top_classification == "technical_request":
        return "technical_request"
    if classification.top_classification == "content_question":
        return "content_question"
    return "content_answer"


def _enforce_single_question_turn(text: str) -> str:
    stripped = text.strip()
    if stripped.count("?") <= 1:
        return stripped
    first_q = stripped.find("?")
    if first_q == -1:
        return stripped
    return stripped[:first_q + 1].rstrip()


def _clean_control_chars(text: str) -> str:
    return "".join(ch for ch in text if ch in {"\n", "\t"} or ord(ch) >= 32)


def _drop_move_narration_sentences(text: str) -> str:
    parts = [part.strip() for part in re_.split(r"(?<=[.!?])\s+|\n+", text.strip()) if part.strip()]
    kept = [part for part in parts if not any(pattern.search(part) for pattern in _MOVE_NARRATION_PATTERNS)]
    if kept:
        return " ".join(kept).strip()
    return text.strip()


def _lecture_terms_blob(lecture_package: dict) -> str:
    topic_defs = lecture_package.get("topics") or parse_rubric_topics(lecture_package["rubric"])
    topic_labels = " ".join(topic["label"] for topic in topic_defs)
    return " ".join([
        lecture_package.get("rubric", ""),
        lecture_package.get("slides", ""),
        lecture_package.get("handout", ""),
        lecture_package.get("notebook", ""),
        lecture_package.get("bot_notes", ""),
        topic_labels,
    ]).lower()


def _enforce_source_boundedness(text: str, lecture_package: dict) -> tuple[str, bool]:
    lecture_terms = _lecture_terms_blob(lecture_package)
    updated = text
    changed = False
    for external_term, replacement in _SOURCE_BOUNDED_REPLACEMENTS.items():
        if external_term in lecture_terms:
            continue
        pattern = re_.compile(re_.escape(external_term), re_.IGNORECASE)
        if not pattern.search(updated):
            continue
        updated = pattern.sub(replacement, updated)
        changed = True
    return updated, changed


def _contains_substantive_content_question(text: str) -> bool:
    if "?" not in text:
        return False
    question_text = text.strip().split("?")[0]
    return not any(pattern.search(question_text) for pattern in _PROCEDURAL_QUESTION_PATTERNS)


def _finalize_assistant_message(text: str, lecture_package: dict) -> tuple[str, bool]:
    cleaned = _clean_control_chars(text)
    cleaned = _drop_move_narration_sentences(cleaned)
    cleaned, source_rewrite_used = _enforce_source_boundedness(cleaned, lecture_package)
    cleaned = _enforce_single_question_turn(cleaned)
    return cleaned.strip(), source_rewrite_used


def _fallback_classification() -> ClassifierResult:
    return ClassifierResult(
        top_classification="content_answer",
        class_probabilities={
            "content_answer": 0.60,
            "content_question": 0.20,
            "technical_request": 0.10,
            "meta_request": 0.05,
            "off_task": 0.05,
        },
        recommended_policy="respond",
        policy_confidence=0.60,
        short_reason="Classifier fallback: treating as content answer.",
    )


def _classify_message(
    settings: config_module.Settings,
    user_message: str,
    recent_messages: list[dict],
    state: dict,
) -> ClassifierResult:
    """Run the intent classifier. Returns a ClassifierResult (falls back on any failure)."""
    state_excerpt = ClassifierStateExcerpt(
        last_top_classification=state.get("last_top_classification"),
        last_recommended_policy=state.get("last_recommended_policy"),
        last_effective_policy=state.get("last_effective_policy"),
        consecutive_redirects=state.get("consecutive_redirects", 0),
        consecutive_meta_requests=state.get("consecutive_meta_requests", 0),
        consecutive_clarifications=state.get("consecutive_clarifications", 0),
        last_policy_override_reason=state.get("last_policy_override_reason"),
        current_topic_id=state.get("current_topic_id"),
        current_line_status=state.get("current_line_status"),
        last_challenge_level=state.get("last_challenge_level", 1),
        last_action=state.get("last_action"),
        last_target_topic_id=state.get("last_target_topic_id"),
        last_reason_code=state.get("last_reason_code"),
        last_repetition_complaint=bool(state.get("last_repetition_complaint", False)),
        must_not_repeat=state.get("must_not_repeat", []),
        lecture_native_only=bool(state.get("lecture_native_only", True)),
    )
    window = recent_messages[-settings.classifier_recent_message_window:]
    classifier_input = ClassifierInput(
        latest_user_message=user_message,
        recent_messages=[ClassifierMessage(role=m["role"], content=m["content"]) for m in window],
        state=state_excerpt,
    )
    classifier_system_prompt = _load_prompt(str(settings.prompt_dir), "classifier_system_prompt.md")
    try:
        client = openai_.OpenAI(api_key=settings.openai_api_key, timeout=30.0, max_retries=0)
        response = client.chat.completions.create(
            model=settings.classifier_model,
            messages=[
                {"role": "system", "content": classifier_system_prompt},
                {"role": "user", "content": classifier_input.model_dump_json()},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        raw = response.choices[0].message.content
        parsed = j_.loads(raw)
        return ClassifierResult.model_validate(parsed)
    except Exception:
        _log.exception("Classifier failed; using fallback classification")
        return _fallback_classification()


def _build_system_prompt(
    settings: config_module.Settings,
    effective_policy: str,
    lecture_package: dict,
    state: dict,
    recent_messages: list[dict],
    tutor_mode: str,
    action_hint: dict,
) -> str:
    topic_defs = lecture_package.get("topics") or parse_rubric_topics(lecture_package["rubric"])
    topic_id_to_label = {t["topic_id"]: t["label"] for t in topic_defs}
    topics_sampled = state.get("topics_sampled", [])
    sampled_labels_str = ", ".join(
        topic_id_to_label.get(tid, tid) for tid in topics_sampled
    ) or "all topics"

    template = _load_prompt(str(settings.prompt_dir), _prompt_template_name_for_policy(effective_policy))
    target_topic_id = action_hint.get("target_topic_id")
    render_vars: dict[str, object] = {
        "tutor_mode": tutor_mode,
        "sampled_labels": sampled_labels_str,
        "topics_covered": state.get("topics_covered", []),
        "mastery": state.get("mastery", {}),
        "evidence_notes": state.get("evidence_notes", {}),
        "current_topic_id": state.get("current_topic_id") or "none",
        "current_line_status": state.get("current_line_status", "unclear"),
        "last_challenge_level": state.get("last_challenge_level", 1),
        "must_not_repeat": _format_must_not_repeat(state.get("must_not_repeat", [])),
        "recommended_action": action_hint.get("recommended_action", "stay"),
        "target_topic_id": target_topic_id or "none",
        "target_topic_label": topic_id_to_label.get(target_topic_id, target_topic_id or "none"),
        "challenge_level": action_hint.get("challenge_level", 3),
        "challenge_label": _challenge_label(_clamp_challenge_level(action_hint.get("challenge_level", 3))),
        "reason_code": action_hint.get("reason_code", "easy_points_available"),
        "secondary_reason_code": action_hint.get("secondary_reason_code") or "none",
        "action_must_not_repeat": _format_must_not_repeat(action_hint.get("must_not_repeat", [])),
        "source_scope_note": action_hint.get("source_scope_note", "Use lecture-native terminology only."),
        "recent_messages": _format_messages_for_prompt(recent_messages),
        "turn_count": state.get("turn_count", 0) + 1,
        "lecture_title": state.get("lecture_title", ""),
    }
    if effective_policy in _CONTENT_POLICIES:
        render_vars["rubric_text"] = lecture_package["rubric"]
        render_vars["context"] = build_dialogue_context(lecture_package, settings.max_dialogue_context_chars)
    return _render_prompt(template, **render_vars)


def _apply_routing_state(
    state: dict,
    classification: ClassifierResult,
    policy_decision: PolicyDecision,
    old_state: dict,
) -> None:
    """Write routing metadata into state in-place."""
    state["last_top_classification"] = classification.top_classification
    state["last_recommended_policy"] = classification.recommended_policy
    state["last_effective_policy"] = policy_decision.effective_policy
    state["last_policy_override_reason"] = policy_decision.override_reason
    if policy_decision.effective_policy == "redirect":
        state["consecutive_redirects"] = old_state.get("consecutive_redirects", 0) + 1
    else:
        state["consecutive_redirects"] = 0
    if classification.top_classification == "meta_request":
        state["consecutive_meta_requests"] = old_state.get("consecutive_meta_requests", 0) + 1
    else:
        state["consecutive_meta_requests"] = 0
    if policy_decision.effective_policy == "seek_clarification":
        state["consecutive_clarifications"] = old_state.get("consecutive_clarifications", 0) + 1
    else:
        state["consecutive_clarifications"] = 0


def _make_fallback_state(
    old_state: dict,
    classification: ClassifierResult,
    policy_decision: PolicyDecision,
) -> dict:
    fallback = dict(old_state)
    fallback["turn_count"] = old_state.get("turn_count", 0) + 1
    _apply_routing_state(fallback, classification, policy_decision, old_state)
    return fallback


# ---------------------------------------------------------------------------
# Public: opening message
# ---------------------------------------------------------------------------

def _format_opening_topic_choices(labels: list[str]) -> str:
    if not labels:
        return ""
    return "\n".join(f"- {label}" for label in labels)


def build_opening_message(lecture_package: dict, sampled_topic_ids: list[str] | None = None) -> str:
    title = lecture_package["config"].get("title", lecture_package["lecture_id"])
    topic_defs = lecture_package.get("topics") or parse_rubric_topics(lecture_package["rubric"])
    topic_id_to_label = {t["topic_id"]: t["label"] for t in topic_defs}
    choice_count = config_module.get_settings().opening_topic_choice_count
    chosen_ids = (sampled_topic_ids or [])[:choice_count]
    chosen_labels = [topic_id_to_label.get(tid, tid) for tid in chosen_ids if tid in topic_id_to_label]

    if chosen_labels:
        topic_choices = _format_opening_topic_choices(chosen_labels)
        return (
            f"Welcome to the review bot for {title}. "
            "We can start wherever feels most useful.\n"
            "A few good places to start are:\n"
            f"{topic_choices}\n\n"
            "Which would you like to begin with?"
        )

    return (
        f"Welcome to the review bot for {title}. "
        "We can start wherever feels most useful. "
        "What topic from this lecture would you like to begin with?"
    )


# ---------------------------------------------------------------------------
# Public: dialogue reply generation
# ---------------------------------------------------------------------------


def generate_reply(
    *,
    db: sqlalchemy_orm_.Session,
    session_id: str,
    turn_index: int,
    lecture_package: dict,
    recent_messages: list,
    state: dict,
    user_message: str,
) -> tuple[str, dict]:
    """Generate a tutoring reply via the policy routing pipeline.

    Returns (assistant_message, sanitized_updated_state).
    Falls back to a generic message if the dialogue LLM call fails.
    """
    settings = config_module.get_settings()
    topic_defs = lecture_package.get("topics") or parse_rubric_topics(lecture_package["rubric"])
    allowed_topic_ids = {t["topic_id"] for t in topic_defs}

    # 1. Classify the student message.
    classification = _classify_message(settings, user_message, recent_messages, state)

    # 2. Decide effective policy.
    policy_decision = _get_policy_decider().decide_policy(user_message, classification, state)
    effective_policy = policy_decision.effective_policy
    tutor_mode = _tutor_mode_for_turn(classification, effective_policy)
    action_hint = _compute_action_hint(state, lecture_package, recent_messages, user_message)

    # 3. Log classifier output and policy decision.
    session_manager_module.log_classification(
        db=db,
        session_id=session_id,
        turn_index=turn_index,
        classifier_json=classification.model_dump_json(),
        policy_decision_json=policy_decision.model_dump_json(),
    )

    # 4. Build system prompt from the appropriate prompt family.
    system_prompt = _build_system_prompt(
        settings,
        effective_policy,
        lecture_package,
        state,
        recent_messages,
        tutor_mode,
        action_hint,
    )
    prompt_template_name = _prompt_template_name_for_policy(effective_policy)

    # 5. Call the dialogue LLM.
    try:
        client = openai_.OpenAI(api_key=settings.openai_api_key, timeout=30.0, max_retries=0)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        raw = response.choices[0].message.content
        parsed = j_.loads(raw)
        assistant_message, _ = _finalize_assistant_message(str(parsed["assistant_message"]), lecture_package)
        raw_updated_state = parsed.get("updated_state", {})
    except openai_.AuthenticationError:
        _log.exception("generate_reply failed: OpenAI authentication error")
        return _FALLBACK_DIALOGUE_MESSAGE, _make_fallback_state(state, classification, policy_decision)
    except openai_.APIError:
        # Rate limits, timeouts, connection errors from the OpenAI API.
        _log.exception("generate_reply failed: OpenAI API error")
        return _FALLBACK_DIALOGUE_MESSAGE, _make_fallback_state(state, classification, policy_decision)
    except Exception:
        # Catches malformed JSON, missing model output keys, and other unexpected
        # response-parsing failures. sanitize_state_update (our code) is deliberately
        # outside this block so bugs there propagate as 500 instead of hiding as fallback.
        _log.exception("generate_reply failed")
        return _FALLBACK_DIALOGUE_MESSAGE, _make_fallback_state(state, classification, policy_decision)

    # sanitize_state_update and routing state are our own code — bugs propagate as 500.
    updated_state = sanitize_state_update(state, raw_updated_state, allowed_topic_ids)
    if action_hint.get("recommended_action") == "switch" and action_hint.get("target_topic_id"):
        updated_state["current_topic_id"] = action_hint["target_topic_id"]
    updated_state["last_challenge_level"] = _clamp_challenge_level(action_hint.get("challenge_level", 3))
    updated_state["must_not_repeat"] = _sanitize_must_not_repeat(
        list(updated_state.get("must_not_repeat", [])) + list(action_hint.get("must_not_repeat", []))
    )
    updated_state["lecture_native_only"] = True
    updated_state["last_action"] = action_hint.get("recommended_action")
    updated_state["last_target_topic_id"] = action_hint.get("target_topic_id")
    updated_state["last_reason_code"] = action_hint.get("reason_code")
    updated_state["last_repetition_complaint"] = bool(action_hint.get("flags", {}).get("repetition_complaint", False))
    updated_state["last_assistant_had_content_question"] = _contains_substantive_content_question(assistant_message)
    _apply_routing_state(updated_state, classification, policy_decision, state)
    try:
        session_manager_module.log_dialogue_turn_audit(
            db=db,
            session_id=session_id,
            turn_index=turn_index,
            effective_policy=effective_policy,
            prompt_template_name=prompt_template_name,
            dialogue_model=settings.openai_model,
            tutor_mode=tutor_mode,
            action_hint_json=j_.dumps(action_hint, ensure_ascii=False),
            challenge_level=_clamp_challenge_level(action_hint.get("challenge_level", 3)),
            current_topic_id=state.get("current_topic_id"),
            target_topic_id=action_hint.get("target_topic_id"),
            ended_with_content_question=_contains_substantive_content_question(assistant_message),
            repetition_complaint=bool(action_hint.get("flags", {}).get("repetition_complaint", False)),
            switched_topics=bool(state.get("current_topic_id") != updated_state.get("current_topic_id")),
            state_before_json=j_.dumps(state, ensure_ascii=False),
            recent_messages_json=j_.dumps(recent_messages, ensure_ascii=False),
            user_message=user_message,
            rendered_system_prompt=system_prompt,
        )
    except Exception:
        _log.exception("Failed to persist dialogue turn audit")
    return assistant_message, updated_state


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def parse_rubric_topics(rubric_markdown: str) -> list[dict]:
    """Parse canonical topic definitions from rubric markdown.

    Returns a list of dicts with keys: topic_id, label, importance.
    Topics are identified by headers of the form '### T<n>. <label>'.
    """
    matches = list(_TOPIC_SECTION_RE.finditer(rubric_markdown))
    topics = []
    for i, match in enumerate(matches):
        topic_id = match.group(1)
        label = match.group(2).strip()
        section_end = matches[i + 1].start() if i + 1 < len(matches) else len(rubric_markdown)
        section_text = rubric_markdown[match.start():section_end]
        imp_match = _IMPORTANCE_RE.search(section_text)
        importance = imp_match.group(1) if imp_match else "unknown"
        topics.append({"topic_id": topic_id, "label": label, "importance": importance})
    return topics


def sample_session_topics(topic_defs: list[dict], session_id: str, count: int = 5) -> list[str]:
    """Sample a deterministic subset of topic IDs seeded by session_id."""
    topic_ids = [t["topic_id"] for t in topic_defs]
    rng = random_.Random(session_id)
    k = min(count, len(topic_ids))
    return rng.sample(topic_ids, k)


def build_dialogue_context(lecture_package: dict, max_chars: int) -> str:
    """Build lecture context string with deterministic truncation.

    Priority order (most important first): bot_notes, slides, handout, notebook.
    When budget is exceeded, notebook is trimmed first, then handout.
    """
    sections = [
        ("## Bot Notes", lecture_package.get("bot_notes", "")),
        ("## Slides", lecture_package.get("slides", "")),
        ("## Handout", lecture_package.get("handout", "")),
        ("## Notebook", lecture_package.get("notebook", "")),
    ]
    parts = []
    used = 0
    for header, content in sections:
        text = content.strip()
        if not text:
            continue
        section = f"{header}\n\n{text}"
        sep_cost = 2 if parts else 0  # len("\n\n")
        cost = len(section) + sep_cost
        if used + cost <= max_chars:
            parts.append(section)
            used += cost
        else:
            room = max_chars - used - sep_cost
            if room > len(header) + 3:
                parts.append(section[:room])
                used = max_chars
            break
    return "\n\n".join(parts)


def compute_weighted_grade(topic_scores: list[dict]) -> int:
    """Compute the weighted student-facing grade from per-topic scores.

    Sorts scores descending, pads to 5 slots with zeros, applies weights
    [55, 25, 13, 4, 3], returns floor of the weighted sum.
    """
    scores = sorted((ts["score"] for ts in topic_scores), reverse=True)
    padded = (scores + [0, 0, 0, 0, 0])[:5]
    return math_.floor(sum(w * s / 100 for w, s in zip(_GRADE_WEIGHTS, padded)))


def sanitize_state_update(old_state: dict, llm_state: dict, allowed_topic_ids: set) -> dict:
    """Sanitize a model-returned state update with merge semantics.

    Rules enforced:
    - topics_sampled: immutable, taken from old_state
    - lecture_title: immutable, taken from old_state
    - timeout_warning_sent: backend-owned flag preserved from old_state
    - current_topic_id: replaced only with a valid topic ID or explicit null
    - current_line_status: preserved when absent; must be one of the allowed status labels
    - last_challenge_level: preserved when absent; clamped 1-7 when present
    - must_not_repeat: preserved when absent; deduplicated and length-limited when present
    - backend-owned routing/action/source fields are preserved from old_state
    - topics_covered: union of old + new (new filtered to allowed_topic_ids);
      when new is empty the prior list is preserved unchanged
    - mastery: old merged with new (new values filtered and clamped 0-100);
      when new is empty the prior dict is preserved unchanged
    - evidence_notes: old merged with new (new values must be strings);
      when new is empty the prior dict is preserved unchanged
    - turn_count: old_turn_count + 1 (LLM value ignored)
    - unknown keys dropped
    """
    result = {
        "topics_sampled": list(old_state.get("topics_sampled", [])),
        "lecture_title": old_state.get("lecture_title", ""),
        "timeout_warning_sent": bool(old_state.get("timeout_warning_sent", False)),
        "current_topic_id": old_state.get("current_topic_id"),
        "current_line_status": old_state.get("current_line_status", "unclear"),
        "last_challenge_level": _clamp_challenge_level(old_state.get("last_challenge_level", 1), default=1),
        "must_not_repeat": _sanitize_must_not_repeat(old_state.get("must_not_repeat", [])),
        "lecture_native_only": bool(old_state.get("lecture_native_only", True)),
        "last_action": old_state.get("last_action"),
        "last_target_topic_id": old_state.get("last_target_topic_id"),
        "last_reason_code": old_state.get("last_reason_code"),
        "last_repetition_complaint": bool(old_state.get("last_repetition_complaint", False)),
        "last_assistant_had_content_question": bool(old_state.get("last_assistant_had_content_question", False)),
    }

    # current_topic_id: allow explicit null to clear the local focus
    if "current_topic_id" in llm_state:
        raw_topic = llm_state.get("current_topic_id")
        if raw_topic is None:
            result["current_topic_id"] = None
        elif isinstance(raw_topic, str) and raw_topic in allowed_topic_ids:
            result["current_topic_id"] = raw_topic

    # current_line_status: preserve prior unless an allowed label is provided
    raw_line_status = llm_state.get("current_line_status")
    if isinstance(raw_line_status, str) and raw_line_status in _ALLOWED_LINE_STATUSES:
        result["current_line_status"] = raw_line_status

    if "last_challenge_level" in llm_state:
        result["last_challenge_level"] = _clamp_challenge_level(llm_state.get("last_challenge_level"), default=result["last_challenge_level"])

    if "must_not_repeat" in llm_state:
        result["must_not_repeat"] = _sanitize_must_not_repeat(llm_state.get("must_not_repeat"))

    # topics_covered: union when LLM provides entries; preserve prior when empty
    new_topics = [
        t for t in llm_state.get("topics_covered", [])
        if isinstance(t, str) and t in allowed_topic_ids
    ]
    if new_topics:
        seen: set = set()
        merged: list = []
        for t in list(old_state.get("topics_covered", [])) + new_topics:
            if t not in seen:
                seen.add(t)
                merged.append(t)
        result["topics_covered"] = merged
    else:
        result["topics_covered"] = list(old_state.get("topics_covered", []))

    # mastery: merge new into old when LLM provides entries; preserve prior when empty
    raw_mastery = llm_state.get("mastery", {})
    new_mastery: dict[str, int] = {}
    if isinstance(raw_mastery, dict):
        for k, v in raw_mastery.items():
            if isinstance(k, str) and k in allowed_topic_ids:
                try:
                    new_mastery[k] = max(0, min(100, int(v)))
                except (ValueError, TypeError):
                    pass
    if new_mastery:
        result["mastery"] = {**old_state.get("mastery", {}), **new_mastery}
    else:
        result["mastery"] = dict(old_state.get("mastery", {}))

    # evidence_notes: merge new into old when LLM provides entries; preserve prior when empty
    raw_evidence = llm_state.get("evidence_notes", {})
    new_evidence: dict[str, str] = {}
    if isinstance(raw_evidence, dict):
        for k, v in raw_evidence.items():
            if isinstance(k, str) and k in allowed_topic_ids and isinstance(v, str):
                new_evidence[k] = v
    if new_evidence:
        result["evidence_notes"] = {**old_state.get("evidence_notes", {}), **new_evidence}
    else:
        result["evidence_notes"] = dict(old_state.get("evidence_notes", {}))

    result["turn_count"] = old_state.get("turn_count", 0) + 1

    return result


def serialize_messages(rows) -> list[dict]:
    """Convert message model rows into plain dicts for prompt construction."""
    return [{"role": row.role, "content": row.content} for row in rows]


# ---------------------------------------------------------------------------
# Public: grading
# ---------------------------------------------------------------------------

def generate_topic_scores(
    *,
    lecture_package: dict,
    messages: list,
    state: dict,
) -> dict:
    """Grade the student based on the conversation.

    Returns:
        {
          "topic_scores": [{"topic_id": "T1", "score": 85, "rationale": "..."}],
          "explanation": "...",
          "missing_topics": ["T8"]
        }

    Falls back to empty scores on any failure.
    """
    settings = config_module.get_settings()
    topic_defs = lecture_package.get("topics") or parse_rubric_topics(lecture_package["rubric"])
    context = build_dialogue_context(lecture_package, settings.max_grading_context_chars)
    rubric_text = lecture_package["rubric"]

    # Format conversation for grading
    conversation_text = "\n\n".join(
        f"[{msg['role'].upper()}]: {msg['content']}" for msg in messages
    )

    system_prompt = (
        "You are a mastery assessor reviewing a tutoring conversation.\n"
        "Grade only the topics that the student actually demonstrated understanding of.\n"
        "Do NOT compute or include a final numeric grade.\n"
        "Use only canonical topic IDs from the rubric (T1, T2, etc.).\n"
        "Score each touched topic 0–100 based on depth and accuracy.\n\n"
        "Rubric:\n"
        f"{rubric_text}\n\n"
        "Lecture content overview:\n"
        f"{context}\n\n"
        "Return JSON only. No extra text outside the JSON.\n"
        "Return exactly this structure:\n"
        "{\n"
        '  "topic_scores": [\n'
        '    {"topic_id": "T1", "score": 85, "rationale": "..."}\n'
        "  ],\n"
        '  "explanation": "brief overall summary",\n'
        '  "missing_topics": ["T8", "T10"]\n'
        "}"
    )

    user_message = f"Here is the tutoring conversation to grade:\n\n{conversation_text}"

    try:
        client = openai_.OpenAI(api_key=settings.openai_api_key, timeout=30.0, max_retries=0)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw = response.choices[0].message.content
        parsed = j_.loads(raw)
        raw_topic_scores = parsed.get("topic_scores", [])
        explanation = str(parsed.get("explanation", ""))
        raw_missing = [str(t) for t in parsed.get("missing_topics", []) if isinstance(t, str)]
    except openai_.AuthenticationError:
        _log.exception("generate_topic_scores failed: OpenAI authentication error")
        return {"topic_scores": [], "explanation": "Grading unavailable.", "missing_topics": []}
    except openai_.APIError:
        # Rate limits, timeouts, connection errors from the OpenAI API.
        _log.exception("generate_topic_scores failed: OpenAI API error")
        return {"topic_scores": [], "explanation": "Grading unavailable.", "missing_topics": []}
    except Exception:
        # Catches malformed JSON, missing model output keys, and other unexpected
        # response-parsing failures. Our own validation code below is deliberately
        # outside this block so bugs there propagate as 500 instead of hiding as fallback.
        _log.exception("generate_topic_scores failed")
        return {"topic_scores": [], "explanation": "Grading unavailable.", "missing_topics": []}
    # Our own validation logic — bugs here propagate as 500, not masked as fallback
    allowed_topic_ids = {t["topic_id"] for t in topic_defs}
    topic_id_to_label = {t["topic_id"]: t["label"] for t in topic_defs}
    seen: dict = {}
    for ts in raw_topic_scores:
        if not isinstance(ts, dict):
            continue
        tid = str(ts.get("topic_id", ""))
        if tid not in allowed_topic_ids:
            continue
        try:
            score = max(0, min(100, int(ts["score"])))
        except (KeyError, ValueError, TypeError):
            continue
        if tid not in seen or score > seen[tid]["score"]:
            seen[tid] = {
                "topic_id": tid,
                "score": score,
                "rationale": str(ts.get("rationale", "")),
            }
    labelled_missing = [
        topic_id_to_label.get(tid, tid)
        for tid in raw_missing
        if tid in allowed_topic_ids
    ]
    return {
        "topic_scores": list(seen.values()),
        "explanation": explanation,
        "missing_topics": labelled_missing,
    }


# ---------------------------------------------------------------------------
# Public: report generation
# ---------------------------------------------------------------------------

def generate_report(
    *,
    lecture_package: dict,
    messages: list,
    state: dict,
    grading_result: dict,
    session_id: str,
    student_id: str,
    timestamp_iso: str,
) -> dict:
    """Generate a final report using the authoritative grading result.

    Returns a dict with keys: report_text, report_json.
    Falls back to a basic report if OpenAI fails.
    """
    settings = config_module.get_settings()
    rubric_text = lecture_package["rubric"]
    final_grade = grading_result.get("final_grade", 0)
    explanation = grading_result.get("explanation", "")
    missing_topics = grading_result.get("missing_topics", [])
    topic_scores = grading_result.get("topic_scores", [])

    topic_summary = ", ".join(
        f"{ts['topic_id']}={ts['score']}" for ts in topic_scores
    ) if topic_scores else "none assessed"

    system_prompt = (
        "You are writing a final mastery report for a student's tutoring session.\n"
        "Write a clear, professional 2–3 paragraph report based on the assessment provided.\n"
        "Focus on: what the student demonstrated, where they showed strength, where growth is needed.\n"
        "Do not include a grade number — the backend will add that separately.\n\n"
        f"Final grade earned: {final_grade}/100\n"
        f"Topic scores: {topic_summary}\n"
        f"Assessment: {explanation}\n"
        f"Topics not covered: {missing_topics}\n\n"
        "Rubric for reference:\n"
        f"{rubric_text}\n\n"
        "Return JSON only:\n"
        '{"report_text": "your 2-3 paragraph report"}'
    )

    conversation_text = "\n\n".join(
        f"[{msg['role'].upper()}]: {msg['content']}" for msg in messages
    )

    fallback_report_text = (
        f"Session report for {student_id}. "
        f"Final grade: {final_grade}/100. "
        f"{explanation}"
    )

    try:
        client = openai_.OpenAI(api_key=settings.openai_api_key, timeout=30.0, max_retries=0)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Conversation:\n\n{conversation_text}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        raw = response.choices[0].message.content
        parsed = j_.loads(raw)
        report_text = str(parsed["report_text"])
    except openai_.AuthenticationError:
        _log.exception("generate_report failed: OpenAI authentication error")
        report_text = fallback_report_text
    except openai_.APIError:
        # Rate limits, timeouts, connection errors from the OpenAI API.
        _log.exception("generate_report failed: OpenAI API error")
        report_text = fallback_report_text
    except Exception:
        # Catches malformed JSON, missing model output keys, and other unexpected
        # response-parsing failures.
        _log.exception("generate_report failed")
        report_text = fallback_report_text

    return {
        "report_text": report_text,
        "report_json": {
            "session_id": session_id,
            "student_id": student_id,
            "timestamp": timestamp_iso,
            "final_grade": final_grade,
        },
    }
