import json as j_
import math as math_
import random as random_
import re as re_

import app.config as config_module

_GRADE_WEIGHTS = [55, 25, 13, 4, 3]

_TOPIC_SECTION_RE = re_.compile(r'^### (T\d+)\.\s+(.+)$', re_.MULTILINE)
_IMPORTANCE_RE = re_.compile(r'\*\*Importance:\*\*\s+(\w+)')

_FALLBACK_DIALOGUE_MESSAGE = (
    "I'm having trouble updating the tutoring state cleanly. "
    "Let's keep going with one focused question: "
    "what idea from this lecture seems most important to you, and why?"
)


# ---------------------------------------------------------------------------
# Public: opening message
# ---------------------------------------------------------------------------

def build_opening_message(lecture_package: dict) -> str:
    title = lecture_package["config"].get("title", lecture_package["lecture_id"])
    return (
        f"Welcome to the review bot for {title}. "
        "I'll work with you through a short conceptual review of this lecture. "
        "You can ask for your current grade or a final report at any time. "
        "Let's begin: what do you think was one central idea of this lecture?"
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
) -> tuple[str, dict]:
    """Generate a tutoring reply using OpenAI.

    Returns (assistant_message, sanitized_updated_state).
    Falls back to a generic message if OpenAI fails or returns malformed output.
    """
    settings = config_module.get_settings()
    topic_defs = parse_rubric_topics(lecture_package["rubric"])
    allowed_topic_ids = {t["topic_id"] for t in topic_defs}
    context = build_dialogue_context(lecture_package, settings.max_dialogue_context_chars)

    rubric_text = lecture_package["rubric"]
    topics_sampled = state.get("topics_sampled", [])
    topic_id_to_label = {t["topic_id"]: t["label"] for t in topic_defs}
    sampled_labels = [
        f"{tid}: {topic_id_to_label.get(tid, tid)}" for tid in topics_sampled
    ]

    system_prompt = (
        "You are a Socratic tutoring assistant conducting a short conceptual review of a lecture.\n"
        "Your job is to guide the student toward understanding through focused questions.\n\n"
        f"Session focus topics: {', '.join(sampled_labels) if sampled_labels else 'all topics'}\n"
        f"Topics covered so far: {state.get('topics_covered', [])}\n"
        f"Mastery estimates so far: {state.get('mastery', {})}\n\n"
        "Rubric:\n"
        f"{rubric_text}\n\n"
        "Lecture content:\n"
        f"{context}\n\n"
        "Rules:\n"
        "- Keep your reply short and pedagogically focused.\n"
        "- Ask at most ONE follow-up question.\n"
        "- Do NOT change the topics_sampled list.\n"
        "- Do NOT invent new topic IDs. Use only canonical IDs from the rubric (T1, T2, etc.).\n"
        "- Update topics_covered and mastery only for topics the student actually demonstrated understanding of.\n"
        "- Return JSON only. No extra text outside the JSON.\n\n"
        "Return exactly this JSON structure:\n"
        '{\n'
        '  "assistant_message": "your short pedagogical reply with one focused next question",\n'
        '  "updated_state": {\n'
        '    "topics_covered": ["T1"],\n'
        '    "mastery": {"T1": 60},\n'
        f'    "turn_count": {state.get("turn_count", 0) + 1},\n'
        '    "confidence": 0.35,\n'
        f'    "lecture_title": "{state.get("lecture_title", "")}"\n'
        '  }\n'
        '}'
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(recent_messages)
    messages.append({"role": "user", "content": user_message})

    try:
        import openai as openai_
        client = openai_.OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        raw = response.choices[0].message.content
        parsed = j_.loads(raw)
        assistant_message = str(parsed["assistant_message"])
        updated_state = sanitize_state_update(
            state, parsed.get("updated_state", {}), allowed_topic_ids
        )
        return assistant_message, updated_state
    except Exception:
        fallback_state = dict(state)
        fallback_state["turn_count"] = state.get("turn_count", 0) + 1
        return _FALLBACK_DIALOGUE_MESSAGE, fallback_state


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
    """Sanitize a model-returned state update.

    Rules enforced:
    - topics_sampled: immutable, taken from old_state
    - lecture_title: immutable, taken from old_state
    - topics_covered: subset of allowed_topic_ids
    - mastery: keys in allowed_topic_ids, values clamped int 0-100
    - turn_count: old_turn_count + 1
    - confidence: clamped float 0.0-1.0
    - unknown keys dropped
    """
    result = {
        "topics_sampled": list(old_state.get("topics_sampled", [])),
        "lecture_title": old_state.get("lecture_title", ""),
    }

    result["topics_covered"] = [
        t for t in llm_state.get("topics_covered", [])
        if isinstance(t, str) and t in allowed_topic_ids
    ]

    raw_mastery = llm_state.get("mastery", {})
    result["mastery"] = {}
    if isinstance(raw_mastery, dict):
        for k, v in raw_mastery.items():
            if isinstance(k, str) and k in allowed_topic_ids:
                try:
                    result["mastery"][k] = max(0, min(100, int(v)))
                except (ValueError, TypeError):
                    pass

    result["turn_count"] = old_state.get("turn_count", 0) + 1

    raw_conf = llm_state.get("confidence", old_state.get("confidence", 0.0))
    try:
        conf = float(raw_conf)
    except (TypeError, ValueError):
        conf = 0.0
    result["confidence"] = max(0.0, min(1.0, conf))

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
    topic_defs = parse_rubric_topics(lecture_package["rubric"])
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
        import openai as openai_
        client = openai_.OpenAI(api_key=settings.openai_api_key)
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
        # Validate structure defensively
        topic_scores = []
        for ts in parsed.get("topic_scores", []):
            if isinstance(ts, dict) and "topic_id" in ts and "score" in ts:
                topic_scores.append({
                    "topic_id": str(ts["topic_id"]),
                    "score": max(0, min(100, int(ts["score"]))),
                    "rationale": str(ts.get("rationale", "")),
                })
        return {
            "topic_scores": topic_scores,
            "explanation": str(parsed.get("explanation", "")),
            "missing_topics": [str(t) for t in parsed.get("missing_topics", []) if isinstance(t, str)],
        }
    except Exception:
        return {"topic_scores": [], "explanation": "Grading unavailable.", "missing_topics": []}


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

    try:
        import openai as openai_
        client = openai_.OpenAI(api_key=settings.openai_api_key)
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
    except Exception:
        report_text = (
            f"Session report for {student_id}. "
            f"Final grade: {final_grade}/100. "
            f"{explanation}"
        )

    return {
        "report_text": report_text,
        "report_json": {
            "session_id": session_id,
            "student_id": student_id,
            "timestamp": timestamp_iso,
            "final_grade": final_grade,
        },
    }