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
    "respond": "respond_prompt.md",
    "provide_content_support": "provide_content_support_prompt.md",
    "provide_technical_support": "provide_technical_support_prompt.md",
    "redirect": "redirect_prompt.md",
    "seek_clarification": "clarification_prompt.md",
}

# These policies receive lecture content and rubric text in their prompts.
_CONTENT_POLICIES: frozenset[str] = frozenset({"respond", "provide_content_support", "seek_clarification"})

# Matches {identifier} placeholders while leaving {}, {"key": value}, etc. intact.
_TEMPLATE_VAR_RE = re_.compile(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}')
_ALLOWED_LINE_STATUSES = {"productive", "stalled", "over_scaffolded", "unclear"}
_MAX_SYNOPSIS_TEXT_LEN = 240
_MAX_DO_NOT_REPEAT_ITEMS = 4
_MAX_DO_NOT_REPEAT_ITEM_LEN = 120


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


def _format_synopsis_text(value: object) -> str:
    if not isinstance(value, str):
        return "none"
    text = " ".join(value.split()).strip()
    return text or "none"


def _format_do_not_repeat(value: object) -> str:
    if not isinstance(value, list):
        return "none"
    cleaned = []
    for item in value:
        if isinstance(item, str):
            text = " ".join(item.split()).strip()
            if text:
                cleaned.append(text)
    return " | ".join(cleaned) if cleaned else "none"


def _enforce_single_question_turn(text: str) -> str:
    stripped = text.strip()
    if stripped.count("?") <= 1:
        return stripped
    first_q = stripped.find("?")
    if first_q == -1:
        return stripped
    return stripped[:first_q + 1].rstrip()


def _sanitize_synopsis_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).strip()[:_MAX_SYNOPSIS_TEXT_LEN]


def _sanitize_do_not_repeat(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        text = " ".join(item.split()).strip()[:_MAX_DO_NOT_REPEAT_ITEM_LEN]
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
        if len(cleaned) >= _MAX_DO_NOT_REPEAT_ITEMS:
            break
    return cleaned


def _build_progress_guidance(state: dict, topic_id_to_label: dict[str, str]) -> tuple[str, str, str]:
    current_topic_id = state.get("current_topic_id")
    mastery = state.get("mastery", {})
    topics_sampled = [tid for tid in state.get("topics_sampled", []) if tid in topic_id_to_label]
    topics_covered = set(state.get("topics_covered", []))

    current_topic_mastery = "none"
    if isinstance(current_topic_id, str):
        current_topic_mastery = str(int(mastery.get(current_topic_id, 0)))

    remaining_labels = [topic_id_to_label[tid] for tid in topics_sampled if tid not in topics_covered]
    remaining_sampled_topics = ", ".join(remaining_labels) if remaining_labels else "none"

    current_mastery_value = 0
    if isinstance(current_topic_id, str):
        try:
            current_mastery_value = int(mastery.get(current_topic_id, 0))
        except (TypeError, ValueError):
            current_mastery_value = 0

    line_status = state.get("current_line_status", "unclear")
    if remaining_labels and current_mastery_value >= 70:
        progress_focus = (
            "The current topic already has workable evidence. Unless the student explicitly wants depth or the next move is unusually diagnostic, "
            "a fresh sampled topic is probably more valuable than squeezing for marginal extra mastery here."
        )
    elif remaining_labels and line_status in {"stalled", "over_scaffolded"}:
        progress_focus = (
            "This line is losing yield and there are still untouched sampled topics. Prefer moving on unless the next move is clearly different and high-value."
        )
    elif remaining_labels:
        progress_focus = (
            "Continue only if the next move is distinct and likely to add meaningful evidence; otherwise consider moving to one of the remaining sampled topics."
        )
    else:
        progress_focus = "No sampled-topic coverage advantage is available from switching right now; continue only if the next move is genuinely useful."

    return current_topic_mastery, remaining_sampled_topics, progress_focus


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
        assisted_turn_streak=state.get("assisted_turn_streak", 0),
        recent_explanation_attempts=state.get("recent_explanation_attempts", 0),
        recent_parroting_streak=state.get("recent_parroting_streak", 0),
        recent_unelaborated_agreement_streak=state.get("recent_unelaborated_agreement_streak", 0),
        current_line_status=state.get("current_line_status"),
        student_goal_now=state.get("student_goal_now", ""),
        interaction_state=state.get("interaction_state", ""),
        current_line=state.get("current_line", ""),
        what_student_has_shown=state.get("what_student_has_shown", ""),
        what_remains_uncertain=state.get("what_remains_uncertain", ""),
        why_continue_or_switch=state.get("why_continue_or_switch", ""),
        do_not_repeat=state.get("do_not_repeat", []),
        best_next_move=state.get("best_next_move", ""),
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
) -> str:
    topic_defs = lecture_package.get("topics") or parse_rubric_topics(lecture_package["rubric"])
    topic_id_to_label = {t["topic_id"]: t["label"] for t in topic_defs}
    topics_sampled = state.get("topics_sampled", [])
    sampled_labels_str = ", ".join(
        topic_id_to_label.get(tid, tid) for tid in topics_sampled
    ) or "all topics"
    current_topic_mastery, remaining_sampled_topics, progress_focus = _build_progress_guidance(state, topic_id_to_label)

    template = _load_prompt(str(settings.prompt_dir), _POLICY_TO_PROMPT[effective_policy])
    render_vars: dict[str, object] = {
        "sampled_labels": sampled_labels_str,
        "topics_covered": state.get("topics_covered", []),
        "mastery": state.get("mastery", {}),
        "evidence_notes": state.get("evidence_notes", {}),
        "current_topic_id": state.get("current_topic_id") or "none",
        "assisted_turn_streak": state.get("assisted_turn_streak", 0),
        "recent_explanation_attempts": state.get("recent_explanation_attempts", 0),
        "recent_parroting_streak": state.get("recent_parroting_streak", 0),
        "recent_unelaborated_agreement_streak": state.get("recent_unelaborated_agreement_streak", 0),
        "current_line_status": state.get("current_line_status", "unclear"),
        "student_goal_now": _format_synopsis_text(state.get("student_goal_now")),
        "interaction_state": _format_synopsis_text(state.get("interaction_state")),
        "current_line": _format_synopsis_text(state.get("current_line")),
        "what_student_has_shown": _format_synopsis_text(state.get("what_student_has_shown")),
        "what_remains_uncertain": _format_synopsis_text(state.get("what_remains_uncertain")),
        "why_continue_or_switch": _format_synopsis_text(state.get("why_continue_or_switch")),
        "do_not_repeat": _format_do_not_repeat(state.get("do_not_repeat")),
        "best_next_move": _format_synopsis_text(state.get("best_next_move")),
        "current_topic_mastery": current_topic_mastery,
        "remaining_sampled_topics": remaining_sampled_topics,
        "progress_focus": progress_focus,
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

def _join_topic_labels(labels: list[str]) -> str:
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} or {labels[1]}"
    return f"{', '.join(labels[:-1])}, or {labels[-1]}"


def build_opening_message(lecture_package: dict, sampled_topic_ids: list[str] | None = None) -> str:
    title = lecture_package["config"].get("title", lecture_package["lecture_id"])
    topic_defs = lecture_package.get("topics") or parse_rubric_topics(lecture_package["rubric"])
    topic_id_to_label = {t["topic_id"]: t["label"] for t in topic_defs}
    choice_count = config_module.get_settings().opening_topic_choice_count
    chosen_ids = (sampled_topic_ids or [])[:choice_count]
    chosen_labels = [topic_id_to_label.get(tid, tid) for tid in chosen_ids if tid in topic_id_to_label]

    if chosen_labels:
        topic_choices = _join_topic_labels(chosen_labels)
        return (
            f"Welcome to the review bot for {title}. "
            "We can start wherever feels most useful. "
            f"Want to begin with {topic_choices}?"
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

    # 3. Log classifier output and policy decision.
    session_manager_module.log_classification(
        db=db,
        session_id=session_id,
        turn_index=turn_index,
        classifier_json=classification.model_dump_json(),
        policy_decision_json=policy_decision.model_dump_json(),
    )

    # 4. Build system prompt from the appropriate prompt family.
    system_prompt = _build_system_prompt(settings, effective_policy, lecture_package, state, recent_messages)

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
        assistant_message = _enforce_single_question_turn(str(parsed["assistant_message"]))
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
    _apply_routing_state(updated_state, classification, policy_decision, state)
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
    - assisted_turn_streak / recent_explanation_attempts / recent_parroting_streak /
      recent_unelaborated_agreement_streak: preserved when absent; clamped to a small non-negative range
    - current_line_status: preserved when absent; must be one of the allowed status labels
    - working-memory synopsis fields: preserved when absent; normalized and length-limited when present
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
        "assisted_turn_streak": int(old_state.get("assisted_turn_streak", 0)),
        "recent_explanation_attempts": int(old_state.get("recent_explanation_attempts", 0)),
        "recent_parroting_streak": int(old_state.get("recent_parroting_streak", 0)),
        "recent_unelaborated_agreement_streak": int(old_state.get("recent_unelaborated_agreement_streak", 0)),
        "current_line_status": old_state.get("current_line_status", "unclear"),
        "student_goal_now": _sanitize_synopsis_text(old_state.get("student_goal_now", "")),
        "interaction_state": _sanitize_synopsis_text(old_state.get("interaction_state", "")),
        "current_line": _sanitize_synopsis_text(old_state.get("current_line", "")),
        "what_student_has_shown": _sanitize_synopsis_text(old_state.get("what_student_has_shown", "")),
        "what_remains_uncertain": _sanitize_synopsis_text(old_state.get("what_remains_uncertain", "")),
        "why_continue_or_switch": _sanitize_synopsis_text(old_state.get("why_continue_or_switch", "")),
        "do_not_repeat": _sanitize_do_not_repeat(old_state.get("do_not_repeat", [])),
        "best_next_move": _sanitize_synopsis_text(old_state.get("best_next_move", "")),
    }

    # current_topic_id: allow explicit null to clear the local focus
    if "current_topic_id" in llm_state:
        raw_topic = llm_state.get("current_topic_id")
        if raw_topic is None:
            result["current_topic_id"] = None
        elif isinstance(raw_topic, str) and raw_topic in allowed_topic_ids:
            result["current_topic_id"] = raw_topic

    # small pedagogical counters: preserve prior when absent, clamp when present
    for field in (
        "assisted_turn_streak",
        "recent_explanation_attempts",
        "recent_parroting_streak",
        "recent_unelaborated_agreement_streak",
    ):
        if field in llm_state:
            try:
                result[field] = max(0, min(9, int(llm_state[field])))
            except (ValueError, TypeError):
                pass

    # current_line_status: preserve prior unless an allowed label is provided
    raw_line_status = llm_state.get("current_line_status")
    if isinstance(raw_line_status, str) and raw_line_status in _ALLOWED_LINE_STATUSES:
        result["current_line_status"] = raw_line_status

    for field in (
        "student_goal_now",
        "interaction_state",
        "current_line",
        "what_student_has_shown",
        "what_remains_uncertain",
        "why_continue_or_switch",
        "best_next_move",
    ):
        if field in llm_state:
            result[field] = _sanitize_synopsis_text(llm_state.get(field))

    if "do_not_repeat" in llm_state:
        result["do_not_repeat"] = _sanitize_do_not_repeat(llm_state.get("do_not_repeat"))

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
