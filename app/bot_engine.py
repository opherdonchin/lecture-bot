import json as j_
import logging as logging_
import math as math_
import random as random_
import re as re_

import openai as openai_

import app.config as config_module
import app.language_policy as language_policy
import app.prompt_loader as prompt_loader

_log = logging_.getLogger(__name__)

_GRADE_WEIGHTS = [55, 25, 13, 4, 3]
_RUNTIME_CONTEXT_KEYS = ("bot_notes", "slides", "handout", "minutes")
_DECISION_TARGET_TYPES = {
    "criterion",
    "distinction",
    "explanation",
    "application",
    "practical_interpretation",
    "self_correction",
}
_DECISION_MOVE_TYPES = {
    "open_probe",
    "narrowing_question",
    "contrastive_prompt",
    "criterion_check",
    "explanation_check",
    "application_check",
    "practical_interpretation",
    "hint",
    "partial_frame",
    "compact_explanation",
    "concise_reformulation",
    "topic_switch",
    "self_correction_prompt",
}
_DECISION_TRACE_CHECK_KEYS = (
    "most_productive",
    "minimally_revealing",
    "smuggles_answer",
    "asks_one_contribution",
)

_TOPIC_SECTION_RE = re_.compile(r'^### (T\d+)(?:\.|\s+[—-])\s+(.+)$', re_.MULTILINE)
_IMPORTANCE_RE = re_.compile(r'\*\*Importance:\*\*\s+(\w+)')
_BARE_TOPIC_ID_RE = re_.compile(r"\b(T\d+)\b")
_TIME_CLAIM_RE = re_.compile(r"\b\d+\s+minutes?\s+left\b", re_.IGNORECASE)
_NON_ALNUM_RE = re_.compile(r"[^a-z0-9]+")

_FALLBACK_DIALOGUE_MESSAGE = (
    "I'm having trouble updating the tutoring state cleanly. "
    "Let's keep going with one focused question: "
    "what idea from this lecture seems most important to you, and why?"
)
_DIALOGUE_PROMPT_TEMPLATE = "dialogue_system_prompt.md"


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


def normalize_topic_defs(topic_defs: list[dict] | None) -> list[dict]:
    """Return canonical topic defs with duplicate topic IDs removed.

    Some rubric sections repeat canonical `### Tn.` headings later in the file
    (for example under evidence standards). We keep the first occurrence for
    each topic ID so the lecture config, sampled topics, and grading views stay
    aligned to one canonical topic list.
    """
    normalized: list[dict] = []
    by_topic_id: dict[str, dict] = {}
    for topic in topic_defs or []:
        if not isinstance(topic, dict):
            continue
        topic_id = str(topic.get("topic_id", "")).strip()
        label = str(topic.get("label", "")).strip()
        if not topic_id or not label:
            continue
        importance = str(topic.get("importance", "unknown") or "unknown").strip()
        existing = by_topic_id.get(topic_id)
        if existing is None:
            canonical_topic = {
                "topic_id": topic_id,
                "label": label,
                "importance": importance,
            }
            normalized.append(canonical_topic)
            by_topic_id[topic_id] = canonical_topic
            continue
        if existing["importance"] == "unknown" and importance != "unknown":
            existing["importance"] = importance
    return normalized


def _unique_topic_ids(topic_ids: list[str] | None) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for topic_id in topic_ids or []:
        if not isinstance(topic_id, str) or not topic_id or topic_id in seen:
            continue
        seen.add(topic_id)
        unique.append(topic_id)
    return unique


def _normalize_selection_text(text: str) -> str:
    return _NON_ALNUM_RE.sub(" ", text.lower()).strip()


def rewrite_opening_topic_selection(
    *,
    lecture_package: dict,
    state: dict,
    user_message: str,
) -> str:
    """Rewrite an opening-turn topic pick into explicit selection intent.

    This prevents short menu replies like "Why sample" from being treated as
    content answers to the topic itself.
    """
    if state.get("turn_count", 0) != 0:
        return user_message
    if state.get("current_topic_id") is not None:
        return user_message

    topic_defs = resolve_topic_defs(lecture_package)
    topic_id_to_label = {topic["topic_id"]: topic["label"] for topic in topic_defs}
    sampled_labels = [
        topic_id_to_label[topic_id]
        for topic_id in _unique_topic_ids(state.get("topics_sampled", []))
        if topic_id in topic_id_to_label
    ]
    normalized_user = _normalize_selection_text(user_message)
    if not normalized_user:
        return user_message

    for label in sampled_labels:
        normalized_label = _normalize_selection_text(label)
        if not normalized_label:
            continue
        if normalized_user == normalized_label:
            return (
                f"I want to begin with the topic '{label}'. "
                "Treat my message as a topic selection, not as a content answer. "
                "Ask the first substantive question for that topic."
            )
        if len(normalized_user) >= 6 and normalized_label.startswith(normalized_user):
            return (
                f"I want to begin with the topic '{label}'. "
                "Treat my message as a topic selection, not as a content answer. "
                "Ask the first substantive question for that topic."
            )

    return user_message


def resolve_topic_defs(lecture_package: dict) -> list[dict]:
    """Load canonical topic defs from lecture config or rubric."""
    return normalize_topic_defs(
        lecture_package.get("topics") or parse_rubric_topics(lecture_package["rubric"])
    )


def build_opening_message(lecture_package: dict, sampled_topic_ids: list[str] | None = None) -> str:
    title = lecture_package["config"].get("title", lecture_package["lecture_id"])
    topic_defs = resolve_topic_defs(lecture_package)
    topic_id_to_label = {t["topic_id"]: t["label"] for t in topic_defs}

    settings = config_module.get_settings()
    sampled_labels = [
        topic_id_to_label[topic_id]
        for topic_id in (sampled_topic_ids or [])[:settings.opening_topic_choice_count]
        if topic_id in topic_id_to_label
    ]
    if sampled_labels:
        return (
            f"Welcome to the review bot for {title}. "
            "We can start wherever feels most useful. "
            f"Want to begin with {_join_topic_labels(sampled_labels)}?"
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
    lecture_package: dict,
    recent_messages: list,
    state: dict,
    user_message: str,
    timing_context: dict | None = None,
) -> tuple[str, dict]:
    """Generate a tutoring reply using OpenAI.

    Returns (assistant_message, sanitized_updated_state).
    Falls back to a generic message if OpenAI fails or returns malformed output.
    """
    settings = config_module.get_settings()
    topic_defs = resolve_topic_defs(lecture_package)
    allowed_topic_ids = {t["topic_id"] for t in topic_defs}
    context = build_dialogue_context(lecture_package, settings.max_dialogue_context_chars)
    normalized_user_message = rewrite_opening_topic_selection(
        lecture_package=lecture_package,
        state=state,
        user_message=user_message,
    )
    system_prompt = build_dialogue_system_prompt(
        lecture_package=lecture_package,
        state=state,
        topic_defs=topic_defs,
        lecture_context=context,
        timing_context=timing_context,
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(recent_messages)
    messages.append({"role": "user", "content": normalized_user_message})

    try:
        client = openai_.OpenAI(api_key=settings.openai_api_key, timeout=30.0, max_retries=0)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        raw = response.choices[0].message.content
        parsed = j_.loads(raw)
        assistant_message = sanitize_assistant_message(
            str(parsed["assistant_message"]),
            topic_defs=topic_defs,
            timing_context=timing_context,
        )
        raw_updated_state = parsed.get("updated_state", {})
        raw_decision_trace = parsed.get("decision_trace")
    except openai_.AuthenticationError:
        _log.exception("generate_reply failed: OpenAI authentication error")
        fallback_state = dict(state)
        fallback_state["turn_count"] = state.get("turn_count", 0) + 1
        return _FALLBACK_DIALOGUE_MESSAGE, fallback_state
    except openai_.APIError:
        # Rate limits, timeouts, connection errors from the OpenAI API.
        _log.exception("generate_reply failed: OpenAI API error")
        fallback_state = dict(state)
        fallback_state["turn_count"] = state.get("turn_count", 0) + 1
        return _FALLBACK_DIALOGUE_MESSAGE, fallback_state
    except Exception:
        # Catches malformed JSON, missing model output keys, and other unexpected
        # response-parsing failures. sanitize_state_update (our code) is deliberately
        # outside this block so bugs there propagate as 500 instead of hiding as fallback.
        _log.exception("generate_reply failed")
        fallback_state = dict(state)
        fallback_state["turn_count"] = state.get("turn_count", 0) + 1
        return _FALLBACK_DIALOGUE_MESSAGE, fallback_state
    # sanitize_state_update is our own code — bugs here propagate as 500, not masked
    updated_state = sanitize_state_update(
        state,
        raw_updated_state,
        allowed_topic_ids,
        raw_decision_trace=raw_decision_trace,
    )
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
    return normalize_topic_defs(topics)


def sample_session_topics(topic_defs: list[dict], session_id: str, count: int = 5) -> list[str]:
    """Sample a deterministic subset of topic IDs seeded by session_id."""
    topic_ids = _unique_topic_ids([t["topic_id"] for t in normalize_topic_defs(topic_defs)])
    rng = random_.Random(session_id)
    k = min(count, len(topic_ids))
    return rng.sample(topic_ids, k)


def build_dialogue_system_prompt(
    *,
    lecture_package: dict,
    state: dict,
    topic_defs: list[dict],
    lecture_context: str,
    timing_context: dict | None = None,
) -> str:
    """Build the runtime system prompt around the committed markdown prompt."""
    prompt_body = prompt_loader.load_prompt_template(_DIALOGUE_PROMPT_TEMPLATE).strip()
    topic_id_to_label = {t["topic_id"]: t["label"] for t in topic_defs}
    sampled_topic_ids = _unique_topic_ids(state.get("topics_sampled", []))
    sampled_topics = [
        {
            "topic_id": tid,
            "label": topic_id_to_label.get(tid, tid),
        }
        for tid in sampled_topic_ids
    ]
    current_state = {
        "topics_sampled": list(sampled_topic_ids),
        "topics_covered": list(state.get("topics_covered", [])),
        "mastery": dict(state.get("mastery", {})),
        "best_mastery": dict(state.get("best_mastery", {})),
        "evidence_notes": dict(state.get("evidence_notes", {})),
        "current_topic_id": state.get("current_topic_id"),
        "tutor_comment": state.get("tutor_comment", ""),
        "turn_count": state.get("turn_count", 0) + 1,
    }

    injected_context = {
        "lecture_title": lecture_package["config"].get("title", lecture_package["lecture_id"]),
        "sampled_topics": sampled_topics,
        "topic_structure_note": "Use the rubric text below as the equivalent topic-to-element map or rubric structure.",
        "current_tutoring_state": current_state,
        "session_timing": timing_context or {},
        "rubric_text": lecture_package["rubric"],
        "lecture_context": lecture_context,
    }

    return (
        f"{prompt_body}\n\n"
        "Runtime context\n\n"
        "## Injected lecture/runtime data\n"
        f"{j_.dumps(injected_context, indent=2, ensure_ascii=False)}"
    )


def build_dialogue_context(lecture_package: dict, max_chars: int) -> str:
    """Build lecture context string with deterministic truncation.

    Use the configured context_sections order from lecture config / lectures defaults.
    """
    sections = [
        (f"## {section['label']}", section.get("content", ""))
        for section in lecture_package.get("context_sections", [])
        if section.get("key") in _RUNTIME_CONTEXT_KEYS
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


def sanitize_assistant_message(
    assistant_message: str,
    *,
    topic_defs: list[dict],
    timing_context: dict | None = None,
) -> str:
    """Apply hard guardrails to the student-facing tutor message."""
    topic_id_to_label = {topic["topic_id"]: topic["label"] for topic in topic_defs}

    def replace_topic_id(match):
        topic_id = match.group(1)
        return topic_id_to_label.get(topic_id, "this topic")

    sanitized = _BARE_TOPIC_ID_RE.sub(replace_topic_id, assistant_message).strip()
    if not timing_context or not timing_context.get("timing_reliable", False):
        sanitized = _TIME_CLAIM_RE.sub("time left", sanitized)
    return language_policy.ensure_english_text(
        sanitized,
        language_policy.ENGLISH_ONLY_ASSISTANT_FALLBACK,
    )


def compute_weighted_grade(topic_scores: list[dict]) -> int:
    """Compute the weighted student-facing grade from per-topic scores.

    Sorts scores descending, pads to 5 slots with zeros, applies weights
    [55, 25, 13, 4, 3], returns floor of the weighted sum.
    """
    scores = sorted((ts["score"] for ts in topic_scores), reverse=True)
    padded = (scores + [0, 0, 0, 0, 0])[:5]
    return math_.floor(sum(w * s / 100 for w, s in zip(_GRADE_WEIGHTS, padded)))


def _sanitize_decision_trace(raw_trace: object, allowed_topic_ids: set[str]) -> dict | None:
    if not isinstance(raw_trace, dict):
        return None

    def _sanitize_topic_option(raw_option: object) -> dict:
        if not isinstance(raw_option, dict):
            raw_option = {}
        topic_id = str(raw_option.get("topic_id", "")).strip()
        return {
            "topic_id": topic_id if topic_id in allowed_topic_ids else None,
            "why_consider": str(raw_option.get("why_consider", "")).strip()[:240],
        }

    def _sanitize_topic_value(raw_value: object) -> dict:
        if not isinstance(raw_value, dict):
            raw_value = {}
        topic_id = str(raw_value.get("topic_id", "")).strip()
        return {
            "topic_id": topic_id if topic_id in allowed_topic_ids else None,
            "grade_value": _safe_rating(raw_value.get("grade_value", 1)),
            "pedagogical_value": _safe_rating(raw_value.get("pedagogical_value", 1)),
            "engagement_value": _safe_rating(raw_value.get("engagement_value", 1)),
            "reason": str(raw_value.get("reason", "")).strip()[:240],
        }

    def _sanitize_weighted_topic_comparison(raw_comparison: object) -> dict:
        if not isinstance(raw_comparison, dict):
            raw_comparison = {}
        preferred_topic_id = str(raw_comparison.get("preferred_topic_id", "")).strip()
        current_total_raw = raw_comparison.get("current_topic_total", 0)
        alternative_total_raw = raw_comparison.get("alternative_topic_total", 0)
        try:
            current_topic_total = max(0, min(99, int(current_total_raw or 0)))
        except (TypeError, ValueError):
            current_topic_total = 0
        try:
            alternative_topic_total = max(0, min(99, int(alternative_total_raw or 0)))
        except (TypeError, ValueError):
            alternative_topic_total = 0
        return {
            "grade_weight": _safe_rating(raw_comparison.get("grade_weight", 1)),
            "pedagogical_weight": _safe_rating(raw_comparison.get("pedagogical_weight", 1)),
            "engagement_weight": _safe_rating(raw_comparison.get("engagement_weight", 1)),
            "current_topic_total": current_topic_total,
            "alternative_topic_total": alternative_topic_total,
            "preferred_topic_id": preferred_topic_id if preferred_topic_id in allowed_topic_ids else None,
            "reason": str(raw_comparison.get("reason", "")).strip()[:240],
        }

    def _sanitize_chosen_topic(raw_topic: object) -> dict:
        if not isinstance(raw_topic, dict):
            raw_topic = {}
        topic_id = str(raw_topic.get("topic_id", "")).strip()
        choice_type = str(raw_topic.get("choice_type", "")).strip()
        return {
            "topic_id": topic_id if topic_id in allowed_topic_ids else None,
            "choice_type": choice_type if choice_type in {"stay", "switch"} else "",
            "reason": str(raw_topic.get("reason", "")).strip()[:240],
        }

    def _sanitize_student_model(raw_model: object) -> dict:
        if not isinstance(raw_model, dict):
            raw_model = {}
        return {
            "understanding": str(raw_model.get("understanding", "")).strip()[:240],
            "uncertainty": str(raw_model.get("uncertainty", "")).strip()[:240],
            "failure_mode": str(raw_model.get("failure_mode", "")).strip()[:240],
        }

    def _sanitize_evidence_target(raw_target: object) -> dict:
        if not isinstance(raw_target, dict):
            raw_target = {}
        topic_id = str(raw_target.get("topic_id", "")).strip()
        target_type = str(raw_target.get("target_type", "")).strip()
        return {
            "topic_id": topic_id if topic_id in allowed_topic_ids else None,
            "element": str(raw_target.get("element", "")).strip()[:160],
            "target_type": target_type if target_type in _DECISION_TARGET_TYPES else "",
            "why_now": str(raw_target.get("why_now", "")).strip()[:240],
        }

    def _safe_rating(value: object) -> int:
        try:
            return max(1, min(5, int(value or 1)))
        except (TypeError, ValueError):
            return 1

    def _sanitize_move_candidates(raw_candidates: object) -> list[dict]:
        move_candidates: list[dict] = []
        if not isinstance(raw_candidates, list):
            return move_candidates
        for item in raw_candidates[:4]:
            if not isinstance(item, dict):
                continue
            move_type = str(item.get("move_type", "")).strip()
            move_candidates.append(
                {
                    "move_type": move_type if move_type in _DECISION_MOVE_TYPES else "open_probe",
                    "prompt_sketch": str(item.get("prompt_sketch", "")).strip()[:200],
                    "revealing": _safe_rating(item.get("revealing", 1)),
                    "productive": _safe_rating(item.get("productive", 1)),
                    "fit": _safe_rating(item.get("fit", 1)),
                }
            )
        return move_candidates

    def _sanitize_choice(raw_choice: object) -> dict:
        if not isinstance(raw_choice, dict):
            raw_choice = {}
        chosen_move_type = str(
            raw_choice.get("chosen_move", raw_choice.get("move_type", ""))
        ).strip()
        return {
            "chosen_move": chosen_move_type if chosen_move_type in _DECISION_MOVE_TYPES else "open_probe",
            "reason": str(raw_choice.get("reason", "")).strip()[:240],
        }

    def _sanitize_reply_draft(raw_draft: object) -> dict:
        if not isinstance(raw_draft, dict):
            raw_draft = {}
        return {
            "draft": str(raw_draft.get("draft", "")).strip()[:280],
        }

    def _sanitize_reply_check(raw_check: object) -> dict:
        if not isinstance(raw_check, dict):
            raw_check = {}
        return {
            key: bool(raw_check.get(key, False))
            for key in _DECISION_TRACE_CHECK_KEYS
        }

    def _sanitize_revision(raw_revision: object) -> dict:
        if not isinstance(raw_revision, dict):
            raw_revision = {}
        return {
            "revised": bool(raw_revision.get("revised", False)),
            "reason": str(raw_revision.get("reason", "")).strip()[:240],
        }

    stepwise_present = any(key.startswith("step_") for key in raw_trace)

    if "step_6_chosen_topic" in raw_trace or "step_14_final_move" in raw_trace:
        trace = {
            "step_1_current_topic_option": _sanitize_topic_option(raw_trace.get("step_1_current_topic_option")),
            "step_2_alternative_topic_option": _sanitize_topic_option(raw_trace.get("step_2_alternative_topic_option")),
            "step_3_current_topic_value": _sanitize_topic_value(raw_trace.get("step_3_current_topic_value")),
            "step_4_alternative_topic_value": _sanitize_topic_value(raw_trace.get("step_4_alternative_topic_value")),
            "step_5_weighted_topic_comparison": _sanitize_weighted_topic_comparison(raw_trace.get("step_5_weighted_topic_comparison")),
            "step_6_chosen_topic": _sanitize_chosen_topic(raw_trace.get("step_6_chosen_topic")),
            "step_7_student_model": _sanitize_student_model(raw_trace.get("step_7_student_model")),
            "step_8_evidence_target": _sanitize_evidence_target(raw_trace.get("step_8_evidence_target")),
            "step_9_move_candidates": _sanitize_move_candidates(raw_trace.get("step_9_move_candidates")),
            "step_10_choice": _sanitize_choice(raw_trace.get("step_10_choice")),
            "step_11_reply_draft": _sanitize_reply_draft(raw_trace.get("step_11_reply_draft")),
            "step_12_reply_check": _sanitize_reply_check(raw_trace.get("step_12_reply_check")),
            "step_13_revision": _sanitize_revision(raw_trace.get("step_13_revision")),
            "step_14_final_move": _sanitize_choice(raw_trace.get("step_14_final_move")),
        }
        if (
            not any(v for v in trace["step_6_chosen_topic"].values() if v)
            and not any(trace["step_7_student_model"].values())
            and not any(v for v in trace["step_8_evidence_target"].values() if v)
            and not trace["step_9_move_candidates"]
            and not trace["step_11_reply_draft"]["draft"]
        ):
            return None
        return trace

    if stepwise_present:
        student_model = _sanitize_student_model(raw_trace.get("step_1_student_model"))
        evidence_target = _sanitize_evidence_target(raw_trace.get("step_2_evidence_target"))
        move_candidates = _sanitize_move_candidates(raw_trace.get("step_3_move_candidates"))
        chosen_move = _sanitize_choice(raw_trace.get("step_4_choice"))
        chosen_topic_id = evidence_target.get("topic_id")

        if (
            not any(student_model.values())
            and not move_candidates
            and not any(v for v in evidence_target.values() if v)
        ):
            return None

        return {
            "step_1_current_topic_option": {
                "topic_id": chosen_topic_id,
                "why_consider": "",
            },
            "step_2_alternative_topic_option": {
                "topic_id": None,
                "why_consider": "",
            },
            "step_3_current_topic_value": {
                "topic_id": chosen_topic_id,
                "grade_value": 1,
                "pedagogical_value": 1,
                "engagement_value": 1,
                "reason": "",
            },
            "step_4_alternative_topic_value": {
                "topic_id": None,
                "grade_value": 1,
                "pedagogical_value": 1,
                "engagement_value": 1,
                "reason": "",
            },
            "step_5_weighted_topic_comparison": {
                "grade_weight": 1,
                "pedagogical_weight": 1,
                "engagement_weight": 1,
                "current_topic_total": 0,
                "alternative_topic_total": 0,
                "preferred_topic_id": chosen_topic_id,
                "reason": "",
            },
            "step_6_chosen_topic": {
                "topic_id": chosen_topic_id,
                "choice_type": "stay" if chosen_topic_id else "",
                "reason": "",
            },
            "step_7_student_model": student_model,
            "step_8_evidence_target": evidence_target,
            "step_9_move_candidates": move_candidates,
            "step_10_choice": chosen_move,
            "step_11_reply_draft": _sanitize_reply_draft(raw_trace.get("step_5_reply_draft")),
            "step_12_reply_check": _sanitize_reply_check(raw_trace.get("step_6_reply_check")),
            "step_13_revision": _sanitize_revision(raw_trace.get("step_7_revision")),
            "step_14_final_move": _sanitize_choice(raw_trace.get("step_8_final_move")),
        }

    student_model = _sanitize_student_model(raw_trace.get("student_model"))
    evidence_target = _sanitize_evidence_target(raw_trace.get("evidence_target"))
    move_candidates = _sanitize_move_candidates(raw_trace.get("move_candidates"))
    chosen_move = _sanitize_choice(raw_trace.get("chosen_move"))

    if not any(student_model.values()) and not move_candidates and not any(v for v in evidence_target.values() if v):
        return None

    # Backward-compatible upgrade path: store legacy traces in the new stepwise shape.
    return {
        "step_1_current_topic_option": {
            "topic_id": evidence_target.get("topic_id"),
            "why_consider": "",
        },
        "step_2_alternative_topic_option": {
            "topic_id": None,
            "why_consider": "",
        },
        "step_3_current_topic_value": {
            "topic_id": evidence_target.get("topic_id"),
            "grade_value": 1,
            "pedagogical_value": 1,
            "engagement_value": 1,
            "reason": "",
        },
        "step_4_alternative_topic_value": {
            "topic_id": None,
            "grade_value": 1,
            "pedagogical_value": 1,
            "engagement_value": 1,
            "reason": "",
        },
        "step_5_weighted_topic_comparison": {
            "grade_weight": 1,
            "pedagogical_weight": 1,
            "engagement_weight": 1,
            "current_topic_total": 0,
            "alternative_topic_total": 0,
            "preferred_topic_id": evidence_target.get("topic_id"),
            "reason": "",
        },
        "step_6_chosen_topic": {
            "topic_id": evidence_target.get("topic_id"),
            "choice_type": "stay" if evidence_target.get("topic_id") else "",
            "reason": "",
        },
        "step_7_student_model": student_model,
        "step_8_evidence_target": evidence_target,
        "step_9_move_candidates": move_candidates,
        "step_10_choice": chosen_move,
        "step_11_reply_draft": {"draft": ""},
        "step_12_reply_check": {key: False for key in _DECISION_TRACE_CHECK_KEYS},
        "step_13_revision": {"revised": False, "reason": ""},
        "step_14_final_move": chosen_move,
    }


def sanitize_state_update(
    old_state: dict,
    llm_state: dict,
    allowed_topic_ids: set,
    *,
    raw_decision_trace: object | None = None,
) -> dict:
    """Sanitize a model-returned state update.

    Rules enforced:
    - topics_sampled: immutable, taken from old_state
    - timeout_warning_sent: backend-owned, preserved from old_state
    - best_mastery: backend-owned, preserved from old_state
    - current_grade: backend-owned, preserved from old_state
    - topics_covered: cumulative topics with at least a meaningful foothold
    - mastery: keys in allowed_topic_ids, values clamped int 0-100
    - evidence_notes: keys in allowed_topic_ids, short strings
    - current_topic_id: one allowed topic id or None
    - tutor_comment: short string
    - turn_count: old_turn_count + 1
    - private_decision_trace: backend-stored, never shown to the student
    - unknown keys dropped
    """
    result = {
        "topics_sampled": _unique_topic_ids(old_state.get("topics_sampled", [])),
        "timeout_warning_sent": bool(old_state.get("timeout_warning_sent", False)),
        "best_mastery": {
            k: max(0, min(100, int(v)))
            for k, v in old_state.get("best_mastery", {}).items()
            if isinstance(k, str) and k in allowed_topic_ids and isinstance(v, int | float)
        },
        "current_grade": float(old_state.get("current_grade", 0.0) or 0.0),
    }

    result["mastery"] = {
        k: v
        for k, v in old_state.get("mastery", {}).items()
        if isinstance(k, str) and k in allowed_topic_ids and isinstance(v, int | float)
    }
    raw_mastery = llm_state.get("mastery")
    if isinstance(raw_mastery, dict):
        for k, v in raw_mastery.items():
            if isinstance(k, str) and k in allowed_topic_ids:
                try:
                    result["mastery"][k] = max(0, min(100, int(v)))
                except (ValueError, TypeError):
                    pass

    result["evidence_notes"] = {
        k: str(v)
        for k, v in old_state.get("evidence_notes", {}).items()
        if isinstance(k, str) and k in allowed_topic_ids
    }
    raw_evidence_notes = llm_state.get("evidence_notes")
    if isinstance(raw_evidence_notes, dict):
        for k, v in raw_evidence_notes.items():
            if isinstance(k, str) and k in allowed_topic_ids:
                result["evidence_notes"][k] = str(v)

    prior_topics_covered = [
        t for t in old_state.get("topics_covered", [])
        if isinstance(t, str) and t in allowed_topic_ids
    ]
    meaningful_topics = [
        topic_id
        for topic_id, score in result["mastery"].items()
        if isinstance(score, int | float) and int(score) >= 45
    ]
    seen_topics = set()
    result["topics_covered"] = []
    for topic_id in prior_topics_covered + meaningful_topics:
        if topic_id in seen_topics:
            continue
        seen_topics.add(topic_id)
        result["topics_covered"].append(topic_id)

    raw_current_topic_id = llm_state.get("current_topic_id", old_state.get("current_topic_id"))
    result["current_topic_id"] = (
        raw_current_topic_id
        if isinstance(raw_current_topic_id, str) and raw_current_topic_id in allowed_topic_ids
        else None
    )

    raw_tutor_comment = llm_state.get("tutor_comment", old_state.get("tutor_comment", ""))
    result["tutor_comment"] = str(raw_tutor_comment)

    result["turn_count"] = old_state.get("turn_count", 0) + 1
    result["private_decision_trace"] = _sanitize_decision_trace(raw_decision_trace, allowed_topic_ids)

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
          "scored_topics": ["Topic 1"],
          "missing_topics": ["T8"]
        }

    Falls back to empty scores on any failure.
    """
    settings = config_module.get_settings()
    topic_defs = resolve_topic_defs(lecture_package)
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
    except openai_.AuthenticationError:
        _log.exception("generate_topic_scores failed: OpenAI authentication error")
        return {
            "topic_scores": [],
            "explanation": "Grading unavailable.",
            "scored_topics": [],
            "missing_topics": [],
        }
    except openai_.APIError:
        # Rate limits, timeouts, connection errors from the OpenAI API.
        _log.exception("generate_topic_scores failed: OpenAI API error")
        return {
            "topic_scores": [],
            "explanation": "Grading unavailable.",
            "scored_topics": [],
            "missing_topics": [],
        }
    except Exception:
        # Catches malformed JSON, missing model output keys, and other unexpected
        # response-parsing failures. Our own validation code below is deliberately
        # outside this block so bugs there propagate as 500 instead of hiding as fallback.
        _log.exception("generate_topic_scores failed")
        return {
            "topic_scores": [],
            "explanation": "Grading unavailable.",
            "scored_topics": [],
            "missing_topics": [],
        }
    # Our own validation logic — bugs here propagate as 500, not masked as fallback
    allowed_topic_ids = {t["topic_id"] for t in topic_defs}
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
    topic_scores = list(seen.values())
    scored_topic_ids = {ts["topic_id"] for ts in topic_scores}
    scored_topics = [
        topic["label"]
        for topic in topic_defs
        if topic["topic_id"] in scored_topic_ids
    ]
    labelled_missing = [
        topic["label"]
        for topic in topic_defs
        if topic["topic_id"] not in scored_topic_ids
    ]
    return {
        "topic_scores": topic_scores,
        "explanation": explanation,
        "scored_topics": scored_topics,
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
        report_text = language_policy.ensure_english_text(
            str(parsed["report_text"]),
            language_policy.ENGLISH_ONLY_REPORT_FALLBACK,
        )
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
