import json as j_
import dataclasses as dataclasses_
import logging as logging_
import math as math_
import random as random_
import re as re_

import jsonschema as jsonschema_
import openai as openai_

import app.config as config_module
import app.language_policy as language_policy
import app.prompt_loader as prompt_loader

_log = logging_.getLogger(__name__)

_GRADE_POLICY_ID = "ranked-target-saturation-v1"
_GRADE_WEIGHTS = [55, 25, 13, 7]
_GRADE_FULL_CREDIT_TARGETS = [90, 82, 74, 62]
_RUNTIME_CONTEXT_KEYS = ("bot_notes", "slides", "handout", "minutes")
_TOPIC_SECTION_RE = re_.compile(r'^### (T\d+)(?:\.|\s+[—-])\s+(.+)$', re_.MULTILINE)
_IMPORTANCE_RE = re_.compile(r'\*\*Importance:\*\*\s+(\w+)')
_BARE_TOPIC_ID_RE = re_.compile(r"\b(T\d+)\b")
_TIME_CLAIM_RE = re_.compile(r"\b\d+\s+minutes?\s+left\b", re_.IGNORECASE)
_NON_ALNUM_RE = re_.compile(r"[^a-z0-9]+")
_BELL_CHAR = "\x07"
_BELL_WRAPPED_INLINE_MATH_RE = re_.compile(r"\x07([^\x07\r\n]{1,200})\x07")

_FALLBACK_DIALOGUE_MESSAGE = (
    "The app cannot connect to the backend AI. "
    "Please try again in a minute. "
    "If the problem persists, try again in half an hour. "
    "If there is still no connection, please post the problem on Moodle."
)


@dataclasses_.dataclass(frozen=True)
class DialogueUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cached_prompt_tokens: int | None = None


@dataclasses_.dataclass(frozen=True)
class DialogueReply:
    assistant_message: str
    updated_state: dict
    private_artifact: object | None
    usage: DialogueUsage | None = None

    def __iter__(self):
        yield self.assistant_message
        yield self.updated_state
        yield self.private_artifact


def _usage_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _extract_dialogue_usage(response: object) -> DialogueUsage | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    cached = None
    ptd = getattr(usage, "prompt_tokens_details", None)
    if ptd is not None:
        cached = _usage_int(getattr(ptd, "cached_tokens", None))
    dialogue_usage = DialogueUsage(
        prompt_tokens=_usage_int(getattr(usage, "prompt_tokens", None)),
        completion_tokens=_usage_int(getattr(usage, "completion_tokens", None)),
        total_tokens=_usage_int(getattr(usage, "total_tokens", None)),
        cached_prompt_tokens=cached,
    )
    if (
        dialogue_usage.prompt_tokens is None
        and dialogue_usage.completion_tokens is None
        and dialogue_usage.total_tokens is None
        and dialogue_usage.cached_prompt_tokens is None
    ):
        return None
    return dialogue_usage


def get_tutor_prompt_template(lecture_package: dict | None = None) -> str:
    """Return the tutor prompt template name, allowing lecture config override."""
    # Try lecture_package['config']['tutor_prompt_template'] if present
    if lecture_package and "config" in lecture_package:
        config = lecture_package["config"]
        if isinstance(config, dict) and "tutor_prompt_template" in config:
            return config["tutor_prompt_template"]
    # Otherwise, use global config
    return config_module.get_settings().tutor_prompt_template



# ---------------------------------------------------------------------------
# Public: opening message
# ---------------------------------------------------------------------------

def _format_opening_topic_choices(labels: list[str]) -> str:
    if not labels:
        return ""
    return "\n".join(f"- {label}" for label in labels)


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
        topic_choices = _format_opening_topic_choices(sampled_labels)
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
    lecture_package: dict,
    recent_messages: list,
    state: dict,
    user_message: str,
    timing_context: dict | None = None,
    private_artifact_schema_json: str | None = None,
    repair_instruction: str | None = None,
) -> DialogueReply:
    """Generate a tutoring reply using OpenAI.

    Returns an object that unpacks as (assistant_message, sanitized_updated_state, private_artifact)
    and also carries token usage metadata when the API returns it.
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
        private_artifact_schema_json=private_artifact_schema_json,
    )
    if repair_instruction:
        system_prompt = f"{system_prompt}\n\nRepair instruction\n\n{repair_instruction.strip()}"

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
        dialogue_usage = _extract_dialogue_usage(response)
        try:
            if dialogue_usage is not None:
                _log.info(
                    "dialogue usage: prompt=%s completion=%s total=%s cached=%s",
                    dialogue_usage.prompt_tokens,
                    dialogue_usage.completion_tokens,
                    dialogue_usage.total_tokens,
                    dialogue_usage.cached_prompt_tokens,
                )
        except Exception:
            pass
        raw = response.choices[0].message.content
        try:
            parsed = j_.loads(raw)
        except j_.JSONDecodeError:
            _log.error("raw response unparseable (first 2000 chars): %r", raw[:2000])
            raise
        assistant_message = sanitize_assistant_message(
            str(parsed["assistant_message"]),
            topic_defs=topic_defs,
            timing_context=timing_context,
        )
        raw_updated_state = parsed.get("updated_state", {})
        private_artifact = parsed.get("private_artifact")
    except openai_.AuthenticationError:
        _log.exception("generate_reply failed: OpenAI authentication error")
        fallback_state = dict(state)
        fallback_state["turn_count"] = state.get("turn_count", 0) + 1
        return DialogueReply(_FALLBACK_DIALOGUE_MESSAGE, fallback_state, None)
    except openai_.APIError:
        # Rate limits, timeouts, connection errors from the OpenAI API.
        _log.exception("generate_reply failed: OpenAI API error")
        fallback_state = dict(state)
        fallback_state["turn_count"] = state.get("turn_count", 0) + 1
        return DialogueReply(_FALLBACK_DIALOGUE_MESSAGE, fallback_state, None)
    except Exception:
        # Catches malformed JSON, missing model output keys, and other unexpected
        # response-parsing failures. sanitize_state_update (our code) is deliberately
        # outside this block so bugs there propagate as 500 instead of hiding as fallback.
        _log.exception("generate_reply failed")
        fallback_state = dict(state)
        fallback_state["turn_count"] = state.get("turn_count", 0) + 1
        return DialogueReply(_FALLBACK_DIALOGUE_MESSAGE, fallback_state, None)
    # sanitize_state_update is our own code — bugs here propagate as 500, not masked
    updated_state = sanitize_state_update(
        state,
        raw_updated_state,
        allowed_topic_ids,
    )
    return DialogueReply(assistant_message, updated_state, private_artifact, dialogue_usage)


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



def _build_static_dialogue_prompt_prefix(
    *,
    prompt_body: str,
    lecture_title: str,
    topic_structure_note: str,
    rubric_text: str,
    lecture_context: str,
    private_artifact_schema_json: str | None = None,
) -> str:
    """Build the cache-stable prefix: everything that is identical for the same lecture and prompt template."""
    static_fields: dict = {
        "lecture_context": lecture_context,
        "lecture_title": lecture_title,
        "rubric_text": rubric_text,
        "topic_structure_note": topic_structure_note,
    }
    if private_artifact_schema_json is not None:
        static_fields["private_artifact_schema_json"] = private_artifact_schema_json
    return (
        f"{prompt_body}\n\n"
        "Runtime context\n\n"
        "## Injected lecture/runtime data\n"
        f"{j_.dumps(static_fields, indent=2, ensure_ascii=False, sort_keys=True)}"
    )


def _build_dynamic_dialogue_prompt_suffix(
    *,
    sampled_topics: list[dict],
    current_state: dict,
    timing_context: dict | None,
) -> str:
    """Build the per-session/per-turn suffix that follows the static prefix."""
    dynamic_fields = {
        "sampled_topics": sampled_topics,
        "current_tutoring_state": current_state,
        "session_timing": timing_context or {},
    }
    return (
        "\n\n## Current session state\n"
        f"{j_.dumps(dynamic_fields, indent=2, ensure_ascii=False)}"
    )


def build_dialogue_system_prompt(
    *,
    lecture_package: dict,
    state: dict,
    topic_defs: list[dict],
    lecture_context: str,
    timing_context: dict | None = None,
    private_artifact_schema_json: str | None = None,
) -> str:
    """Build the runtime system prompt around the committed markdown prompt."""
    prompt_template = get_tutor_prompt_template(lecture_package)
    prompt_body = prompt_loader.load_prompt_template(prompt_template).strip()
    topic_id_to_label = {t["topic_id"]: t["label"] for t in topic_defs}
    sampled_topic_ids = _unique_topic_ids(state.get("topics_sampled", []))
    sampled_topics = [
        {
            "topic_id": tid,
            "label": topic_id_to_label.get(tid, tid),
        }
        for tid in sampled_topic_ids
    ]
    best_mastery = dict(state.get("best_mastery", {}))
    ranked_credit = compute_ranked_credit_state(best_mastery)
    grade_impact_deltas = compute_grade_impact_deltas(
        list(sampled_topic_ids), best_mastery
    )
    current_state = {
        "topics_sampled": list(sampled_topic_ids),
        "topics_covered": list(state.get("topics_covered", [])),
        "mastery": dict(state.get("mastery", {})),
        "best_mastery": best_mastery,
        "evidence_notes": dict(state.get("evidence_notes", {})),
        "current_topic_id": state.get("current_topic_id"),
        "tutor_comment": state.get("tutor_comment", ""),
        "turn_count": state.get("turn_count", 0) + 1,
        "grade_impact_deltas": grade_impact_deltas,
        "session_credit_status": ranked_credit["session_credit_status"],
        "grade_relevant_next_move": grade_relevant_next_move(
            list(sampled_topic_ids), best_mastery
        ),
        "ranked_credit_state": ranked_credit["ranked_credit_state"],
    }
    prefix = _build_static_dialogue_prompt_prefix(
        prompt_body=prompt_body,
        lecture_title=lecture_package["config"].get("title", lecture_package["lecture_id"]),
        topic_structure_note="Use the rubric text below as the equivalent topic-to-element map or rubric structure.",
        rubric_text=lecture_package["rubric"],
        lecture_context=lecture_context,
        private_artifact_schema_json=private_artifact_schema_json,
    )
    suffix = _build_dynamic_dialogue_prompt_suffix(
        sampled_topics=sampled_topics,
        current_state=current_state,
        timing_context=timing_context,
    )
    return prefix + suffix


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


def _normalize_malformed_math_text(text: str) -> str:
    """Repair common malformed LaTeX artifacts before showing text to students."""
    normalized = text.replace(f"{_BELL_CHAR}lpha", r"\alpha")
    normalized = _BELL_WRAPPED_INLINE_MATH_RE.sub(r"\\(\1\\)", normalized)
    return normalized.replace(_BELL_CHAR, "")


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

    sanitized = _normalize_malformed_math_text(assistant_message)
    sanitized = _BARE_TOPIC_ID_RE.sub(replace_topic_id, sanitized).strip()
    if not timing_context or not timing_context.get("timing_reliable", False):
        sanitized = _TIME_CLAIM_RE.sub("time left", sanitized)
    return language_policy.ensure_english_text(
        sanitized,
        language_policy.ENGLISH_ONLY_ASSISTANT_FALLBACK,
    )


_SCORE_IF_SUCCESS = [
    (0,   0,   45),
    (1,   30,  42),
    (31,  54,  62),
    (55,  71,  77),
    (72,  87,  92),
    (88,  99, 100),  # robust but below perfect — project to 100
    (100, 100, None),  # already at perfect mastery — no gain possible
]


def grade_policy_snapshot() -> dict:
    """Return the fixed grade policy metadata stored with future grade events."""
    return {
        "policy_id": _GRADE_POLICY_ID,
        "ranked_topic_weights": list(_GRADE_WEIGHTS),
        "ranked_full_credit_targets": list(_GRADE_FULL_CREDIT_TARGETS),
    }


def _topic_sort_key(topic_id: str | None) -> tuple[int, int | str]:
    """Sort canonical topic IDs by numeric order, with stable fallback."""
    if isinstance(topic_id, str) and topic_id.startswith("T") and topic_id[1:].isdigit():
        return (0, int(topic_id[1:]))
    return (1, topic_id or "")


def _ranked_positive_scores(scores: dict[str, int]) -> list[tuple[str, int]]:
    return sorted(
        ((topic_id, int(score)) for topic_id, score in scores.items() if int(score) > 0),
        key=lambda item: (-item[1], _topic_sort_key(item[0])),
    )


def _calibrated_grade_from_scores(
    scores: list[int],
    *,
    weights: list[int] | None = None,
    targets: list[int] | None = None,
) -> int:
    weights = weights or _GRADE_WEIGHTS
    targets = targets or _GRADE_FULL_CREDIT_TARGETS
    ranked = sorted(scores, reverse=True)[:len(weights)]
    padded = (ranked + [0] * len(weights))[:len(weights)]
    total = 0.0
    for weight, raw, target in zip(weights, padded, targets):
        completion = min(raw / target, 1.0) if target > 0 else 0.0
        total += weight * completion
    return math_.floor(total)


def _grade_from_scores(scores: dict[str, int]) -> int:
    """Compute calibrated grade from a {topic_id: score} dict."""
    return _calibrated_grade_from_scores(list(scores.values()))


def compute_ranked_credit_state(
    best_mastery: dict[str, int],
    *,
    weights: list[int] | None = None,
    targets: list[int] | None = None,
) -> dict:
    """Return calibrated credit-state diagnostics for the ranked topic slots."""
    weights = weights or _GRADE_WEIGHTS
    targets = targets or _GRADE_FULL_CREDIT_TARGETS
    ranked = _ranked_positive_scores(best_mastery)
    rows = []
    for index, (weight, target) in enumerate(zip(weights, targets)):
        if index < len(ranked):
            topic_id, raw = ranked[index]
        else:
            topic_id, raw = None, 0
        completion = min(raw / target, 1.0) if target > 0 else 0.0
        rows.append({
            "topic_id": topic_id,
            "raw_mastery": raw,
            "rank": index + 1,
            "target_for_full_credit": target,
            "credit_completion": round(completion, 4),
            "credit_contribution": round(weight * completion, 4),
            "raw_mastery_gap_to_rank_target": max(0, target - raw),
            "status": "full_credit_satisfied" if raw >= target else "below_target",
        })
    grade = _calibrated_grade_from_scores([raw for _, raw in ranked], weights=weights, targets=targets)
    full_credit = grade == sum(weights) and all(
        row["topic_id"] is not None and row["status"] == "full_credit_satisfied"
        for row in rows
    )
    return {
        "grade_policy": grade_policy_snapshot(),
        "grade": grade,
        "ranked_credit_state": rows,
        "session_credit_status": "full_credit_reached" if full_credit else "in_progress",
    }


def compute_grade_impact_deltas(
    sampled_topic_ids: list[str],
    best_mastery: dict[str, int],
) -> dict[str, int]:
    """Return calibrated ΔGrade for each sampled topic if its next probe succeeds.

    The delta is the actual trial difference under the calibrated policy, with
    full re-ranking. It is not forced to zero for target-satisfied topics.
    """
    base_scores = {
        str(tid): int(score)
        for tid, score in (best_mastery or {}).items()
        if int(score) > 0
    }
    for tid in sampled_topic_ids:
        base_scores.setdefault(tid, 0)
    current = _grade_from_scores(base_scores)
    deltas: dict[str, int] = {}
    for tid in sampled_topic_ids:
        cur = base_scores[tid]
        sif = next((s for lo, hi, s in _SCORE_IF_SUCCESS if lo <= cur <= hi), None)
        if sif is None:
            deltas[tid] = 0
        else:
            trial = dict(base_scores)
            trial[tid] = sif
            deltas[tid] = max(0, _grade_from_scores(trial) - current)
    return deltas


def grade_relevant_next_move(
    sampled_topic_ids: list[str],
    best_mastery: dict[str, int],
) -> str | None:
    """Return the sampled topic with the largest positive calibrated delta."""
    deltas = compute_grade_impact_deltas(sampled_topic_ids, best_mastery)
    positive = [(topic_id, delta) for topic_id, delta in deltas.items() if delta > 0]
    if not positive:
        return None
    return sorted(positive, key=lambda item: (-item[1], _topic_sort_key(item[0])))[0][0]


def compute_weighted_grade(topic_scores: list[dict]) -> int:
    """Compute the calibrated student-facing grade from per-topic scores.

    Sorts scores descending, pads to the ranked grade slots with zeros,
    applies ranked weights and full-credit targets, and returns floor of the
    saturated contribution sum for policy ranked-target-saturation-v1.
    """
    return _calibrated_grade_from_scores([ts["score"] for ts in topic_scores])


def sanitize_state_update(
    old_state: dict,
    llm_state: dict,
    allowed_topic_ids: set,
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

    return result


def validate_private_artifact(
    private_artifact: object,
    private_artifact_schema_json: str | None,
) -> str | None:
    """Return a compact validation error, or None when the artifact is valid."""
    if private_artifact_schema_json is None:
        return None
    try:
        schema = j_.loads(private_artifact_schema_json)
    except Exception as exc:
        return _compact_validation_error(f"invalid private_artifact_schema_json: {exc}")
    if private_artifact is None:
        return "missing private_artifact"
    try:
        jsonschema_.Draft202012Validator.check_schema(schema)
        jsonschema_.validate(instance=private_artifact, schema=schema)
    except jsonschema_.ValidationError as exc:
        return _compact_validation_error(f"private_artifact validation failed: {exc.message}")
    except jsonschema_.SchemaError as exc:
        return _compact_validation_error(f"invalid private_artifact_schema_json: {exc.message}")
    return None


def _compact_validation_error(message: str, *, limit: int = 500) -> str:
    normalized = " ".join(str(message).split())
    return normalized[:limit]


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
    scored_topics = grading_result.get("scored_topics", [])
    missing_topics = grading_result.get("missing_topics", [])
    topic_scores = grading_result.get("topic_scores", [])
    session_credit_status = grading_result.get("session_credit_status")

    topic_summary = ", ".join(
        f"{ts['topic_id']}={ts['score']}" for ts in topic_scores
    ) if topic_scores else "none assessed"
    scored_summary = ", ".join(scored_topics) if scored_topics else "no strong footholds yet"
    missing_summary = ", ".join(missing_topics) if missing_topics else "none"

    system_prompt = (
        "You are writing a final mastery report for a student's tutoring session.\n"
        "Write a quick-read, professional report based on the assessment provided.\n"
        "Use short section headings and bullet points, not dense paragraphs.\n"
        "Keep it brief and easy to scan.\n"
        "Do not include a grade number — the backend will add that separately.\n\n"
        f"Final grade earned: {final_grade}/100\n"
        f"Session credit status: {session_credit_status or 'in_progress'}\n"
        f"Topic scores: {topic_summary}\n"
        f"Assessment: {explanation}\n"
        f"Stronger areas so far: {scored_summary}\n"
        f"Topics not yet evidenced: {missing_summary}\n\n"
        "Raw topic scores are diagnostic depth from 0 to 100, not grade gaps.\n"
        "If the student reached full session credit, frame remaining headroom as optional enrichment, "
        "not as work required for the grade.\n\n"
        "Rubric for reference:\n"
        f"{rubric_text}\n\n"
        "Return `report_text` as plain text with exactly these section headings:\n"
        "Summary:\n"
        "Stronger areas:\n"
        "Next steps:\n"
        "Coverage:\n"
        "Under each heading, use 1-3 short bullet points that start with '- '.\n"
        "Do not write multi-paragraph prose.\n\n"
        "Return JSON only:\n"
        '{"report_text": "your bullet-point report"}'
    )

    conversation_text = "\n\n".join(
        f"[{msg['role'].upper()}]: {msg['content']}" for msg in messages
    )

    if session_credit_status == "full_credit_reached":
        fallback_next_step = "Full session credit was reached; any next work is optional enrichment."
    else:
        fallback_next_step = (
            f"Strengthen evidence in {missing_topics[0]}."
            if missing_topics else
            "Keep pushing for one more clean distinction, explanation, or application."
        )
    fallback_report_text = (
        "Summary:\n"
        f"- {explanation or 'This session produced some usable evidence, but the picture is still incomplete.'}\n"
        "Stronger areas:\n"
        f"- {scored_summary}.\n"
        "Next steps:\n"
        f"- {fallback_next_step}\n"
        "Coverage:\n"
        f"- Covered: {scored_summary}.\n"
        f"- Not yet evidenced: {missing_summary}."
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
