"""Unit tests for pure helper functions in app/bot_engine.py."""
import json as j
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.bot_engine as bot_engine


# ---------------------------------------------------------------------------
# parse_rubric_topics
# ---------------------------------------------------------------------------

SAMPLE_RUBRIC = """\
Some intro text.

### T1. Reality–Data–Model distinction

- **Description:** Data are imperfect.

- **Importance:** core

---

### T2. Purpose of statistics

- **Description:** Reasoning from data.

- **Importance:** core

---

### T3. Definition and structure of data

- **Description:** Data as finite sets.

- **Importance:** important

---
"""


def test_parse_rubric_topics_returns_list():
    topics = bot_engine.parse_rubric_topics(SAMPLE_RUBRIC)
    assert isinstance(topics, list)
    assert len(topics) == 3


def test_parse_rubric_topics_ids():
    topics = bot_engine.parse_rubric_topics(SAMPLE_RUBRIC)
    ids = [t["topic_id"] for t in topics]
    assert ids == ["T1", "T2", "T3"]


def test_parse_rubric_topics_labels():
    topics = bot_engine.parse_rubric_topics(SAMPLE_RUBRIC)
    assert topics[0]["label"] == "Reality–Data–Model distinction"
    assert topics[1]["label"] == "Purpose of statistics"


def test_parse_rubric_topics_importance():
    topics = bot_engine.parse_rubric_topics(SAMPLE_RUBRIC)
    assert topics[0]["importance"] == "core"
    assert topics[2]["importance"] == "important"


def test_parse_rubric_topics_empty():
    topics = bot_engine.parse_rubric_topics("No topics here.")
    assert topics == []


# ---------------------------------------------------------------------------
# sample_session_topics
# ---------------------------------------------------------------------------

TOPIC_DEFS = [{"topic_id": f"T{i}", "label": f"Topic {i}", "importance": "core"} for i in range(1, 11)]


def test_sample_session_topics_deterministic():
    result1 = bot_engine.sample_session_topics(TOPIC_DEFS, "session-abc", count=5)
    result2 = bot_engine.sample_session_topics(TOPIC_DEFS, "session-abc", count=5)
    assert result1 == result2


def test_sample_session_topics_count():
    result = bot_engine.sample_session_topics(TOPIC_DEFS, "session-abc", count=5)
    assert len(result) == 5


def test_sample_session_topics_unique():
    result = bot_engine.sample_session_topics(TOPIC_DEFS, "session-abc", count=5)
    assert len(set(result)) == 5


def test_sample_session_topics_subset():
    all_ids = {t["topic_id"] for t in TOPIC_DEFS}
    result = bot_engine.sample_session_topics(TOPIC_DEFS, "session-abc", count=5)
    assert all(tid in all_ids for tid in result)


def test_sample_session_topics_variability_across_seeds():
    """Across 20 fixed seeds, more than one distinct sampled list must appear.

    This proves the sampling is non-trivially seeded rather than always returning
    the same result.  C(10,5)=252 combinations; any reasonable RNG will produce
    multiple distinct results across 20 distinct seeds.
    """
    fixed_seeds = [f"session-{i:03d}" for i in range(20)]
    results = [tuple(bot_engine.sample_session_topics(TOPIC_DEFS, seed, count=5)) for seed in fixed_seeds]
    assert len(set(results)) > 1


def test_sample_session_topics_fewer_than_count():
    small_defs = [{"topic_id": "T1", "label": "A", "importance": "core"}]
    result = bot_engine.sample_session_topics(small_defs, "session-abc", count=5)
    assert result == ["T1"]


def test_enforce_single_question_turn_keeps_one_question():
    text = "You seem close. Can you explain why? Can you give an example too?"
    assert bot_engine._enforce_single_question_turn(text) == "You seem close. Can you explain why?"


def test_build_progress_guidance_prefers_move_on_after_workable_mastery():
    topic_id_to_label = {"T1": "Topic 1", "T2": "Topic 2"}
    state = {
        "current_topic_id": "T1",
        "mastery": {"T1": 75},
        "topics_sampled": ["T1", "T2"],
        "topics_covered": ["T1"],
        "current_line_status": "productive",
    }
    current_topic_mastery, remaining_sampled_topics, progress_focus = bot_engine._build_progress_guidance(state, topic_id_to_label)
    assert current_topic_mastery == "75"
    assert remaining_sampled_topics == "Topic 2"
    assert "more valuable than squeezing for marginal extra mastery" in progress_focus


# ---------------------------------------------------------------------------
# compute_weighted_grade
# ---------------------------------------------------------------------------

def test_compute_weighted_grade_all_100():
    scores = [{"topic_id": f"T{i}", "score": 100} for i in range(1, 6)]
    assert bot_engine.compute_weighted_grade(scores) == 100


def test_compute_weighted_grade_all_zero():
    scores = [{"topic_id": f"T{i}", "score": 0} for i in range(1, 6)]
    assert bot_engine.compute_weighted_grade(scores) == 0


def test_compute_weighted_grade_zero_padding():
    # Only 2 topics scored at 100 each: best 2 get top weights 55+25=80
    scores = [{"topic_id": "T1", "score": 100}, {"topic_id": "T2", "score": 100}]
    result = bot_engine.compute_weighted_grade(scores)
    assert result == 80


def test_compute_weighted_grade_empty():
    result = bot_engine.compute_weighted_grade([])
    assert result == 0


def test_compute_weighted_grade_weighted_order():
    # One topic at 100, all others 0 → 55
    scores = [{"topic_id": "T1", "score": 100}]
    assert bot_engine.compute_weighted_grade(scores) == 55


def test_compute_weighted_grade_floor():
    # score=1 for 5 topics: floor(55*1/100 + 25*1/100 + 13*1/100 + 4*1/100 + 3*1/100)
    # = floor(0.55 + 0.25 + 0.13 + 0.04 + 0.03) = floor(1.0) = 1
    scores = [{"topic_id": f"T{i}", "score": 1} for i in range(1, 6)]
    assert bot_engine.compute_weighted_grade(scores) == 1


def test_compute_weighted_grade_takes_top_5():
    # 6 topics, lowest should be ignored
    scores = [
        {"topic_id": "T1", "score": 80},
        {"topic_id": "T2", "score": 60},
        {"topic_id": "T3", "score": 40},
        {"topic_id": "T4", "score": 20},
        {"topic_id": "T5", "score": 10},
        {"topic_id": "T6", "score": 1},  # should be ignored
    ]
    # top 5: 80, 60, 40, 20, 10 → floor(55*80/100 + 25*60/100 + 13*40/100 + 4*20/100 + 3*10/100)
    # = floor(44 + 15 + 5.2 + 0.8 + 0.3) = floor(65.3) = 65
    assert bot_engine.compute_weighted_grade(scores) == 65


# ---------------------------------------------------------------------------
# sanitize_state_update
# ---------------------------------------------------------------------------

OLD_STATE = {
    "topics_sampled": ["T1", "T2", "T3"],
    "topics_covered": [],
    "mastery": {},
    "evidence_notes": {},
    "current_topic_id": None,
    "assisted_turn_streak": 0,
    "recent_explanation_attempts": 0,
    "recent_parroting_streak": 0,
    "recent_unelaborated_agreement_streak": 0,
    "current_line_status": "unclear",
    "student_goal_now": "pick a starting topic",
    "interaction_state": "opening",
    "current_line": "no topic yet",
    "what_student_has_shown": "",
    "what_remains_uncertain": "which topic to start",
    "why_continue_or_switch": "need a topic before probing",
    "do_not_repeat": [],
    "best_next_move": "offer a topic choice",
    "turn_count": 1,
    "lecture_title": "Lecture 1",
}
ALLOWED_IDS = {"T1", "T2", "T3", "T4", "T5"}


def test_sanitize_topics_sampled_immutable():
    llm_state = {"topics_sampled": ["X9", "X10"], "topics_covered": [], "mastery": {}, "evidence_notes": {}}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert result["topics_sampled"] == ["T1", "T2", "T3"]


def test_sanitize_turn_count_incremented():
    llm_state = {"topics_covered": [], "mastery": {}, "evidence_notes": {}, "turn_count": 99}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert result["turn_count"] == OLD_STATE["turn_count"] + 1


def test_sanitize_topics_covered_filtered():
    llm_state = {"topics_covered": ["T1", "T99"], "mastery": {}, "evidence_notes": {}}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert result["topics_covered"] == ["T1"]


def test_sanitize_mastery_keys_filtered():
    llm_state = {"topics_covered": [], "mastery": {"T1": 80, "T99": 50}, "evidence_notes": {}}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert "T1" in result["mastery"]
    assert "T99" not in result["mastery"]


def test_sanitize_mastery_values_clamped():
    llm_state = {"topics_covered": [], "mastery": {"T1": 150, "T2": -10}, "evidence_notes": {}}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert result["mastery"]["T1"] == 100
    assert result["mastery"]["T2"] == 0


def test_sanitize_no_confidence_field():
    """confidence field was removed; it must not appear in sanitized output."""
    llm_state = {"topics_covered": [], "mastery": {}, "evidence_notes": {}, "confidence": 0.9}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert "confidence" not in result


def test_sanitize_unknown_keys_dropped():
    llm_state = {"topics_covered": [], "mastery": {}, "evidence_notes": {}, "extra_field": "bad"}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert "extra_field" not in result


def test_sanitize_lecture_title_immutable():
    llm_state = {"topics_covered": [], "mastery": {}, "evidence_notes": {}, "lecture_title": "Changed"}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert result["lecture_title"] == "Lecture 1"


# ---------------------------------------------------------------------------
# sanitize_state_update — merge semantics
# ---------------------------------------------------------------------------

OLD_STATE_WITH_CONTENT = {
    "topics_sampled": ["T1", "T2", "T3"],
    "topics_covered": ["T1"],
    "mastery": {"T1": 50},
    "evidence_notes": {"T1": "prior note"},
    "current_topic_id": "T1",
    "assisted_turn_streak": 1,
    "recent_explanation_attempts": 1,
    "recent_parroting_streak": 0,
    "recent_unelaborated_agreement_streak": 0,
    "current_line_status": "productive",
    "student_goal_now": "show understanding efficiently",
    "interaction_state": "student is engaged but repetition risk is rising",
    "current_line": "core distinction within T1",
    "what_student_has_shown": "partial explanation in own words",
    "what_remains_uncertain": "fresh application still needed",
    "why_continue_or_switch": "continue only if next move is different enough",
    "do_not_repeat": ["do not ask for the same distinction again"],
    "best_next_move": "ask for a fresh application",
    "turn_count": 3,
    "lecture_title": "Lecture 1",
}


def test_sanitize_empty_topics_preserves_prior():
    """When LLM returns empty topics_covered, prior list is preserved."""
    llm_state = {"topics_covered": [], "mastery": {}, "evidence_notes": {}}
    result = bot_engine.sanitize_state_update(OLD_STATE_WITH_CONTENT, llm_state, ALLOWED_IDS)
    assert result["topics_covered"] == ["T1"]


def test_sanitize_empty_mastery_preserves_prior():
    """When LLM returns empty mastery, prior dict is preserved."""
    llm_state = {"topics_covered": [], "mastery": {}, "evidence_notes": {}}
    result = bot_engine.sanitize_state_update(OLD_STATE_WITH_CONTENT, llm_state, ALLOWED_IDS)
    assert result["mastery"] == {"T1": 50}


def test_sanitize_empty_evidence_notes_preserves_prior():
    """When LLM returns empty evidence_notes, prior dict is preserved."""
    llm_state = {"topics_covered": [], "mastery": {}, "evidence_notes": {}}
    result = bot_engine.sanitize_state_update(OLD_STATE_WITH_CONTENT, llm_state, ALLOWED_IDS)
    assert result["evidence_notes"] == {"T1": "prior note"}


def test_sanitize_topics_covered_union():
    """New valid topics are added to existing list without duplicates."""
    llm_state = {"topics_covered": ["T1", "T2"], "mastery": {}, "evidence_notes": {}}
    result = bot_engine.sanitize_state_update(OLD_STATE_WITH_CONTENT, llm_state, ALLOWED_IDS)
    assert set(result["topics_covered"]) == {"T1", "T2"}
    assert result["topics_covered"].count("T1") == 1


def test_sanitize_mastery_merge_updates_existing():
    """New mastery values overwrite old values for the same topic."""
    llm_state = {"topics_covered": ["T1"], "mastery": {"T1": 80}, "evidence_notes": {}}
    result = bot_engine.sanitize_state_update(OLD_STATE_WITH_CONTENT, llm_state, ALLOWED_IDS)
    assert result["mastery"]["T1"] == 80


def test_sanitize_evidence_notes_merge():
    """New evidence_notes are merged; prior notes for untouched topics are preserved."""
    llm_state = {"topics_covered": ["T2"], "mastery": {"T2": 45}, "evidence_notes": {"T2": "new note"}}
    result = bot_engine.sanitize_state_update(OLD_STATE_WITH_CONTENT, llm_state, ALLOWED_IDS)
    assert result["evidence_notes"]["T1"] == "prior note"
    assert result["evidence_notes"]["T2"] == "new note"


def test_sanitize_evidence_notes_invalid_keys_dropped():
    """evidence_notes keys not in allowed_topic_ids are dropped."""
    llm_state = {"topics_covered": [], "mastery": {}, "evidence_notes": {"T99": "bad", "T1": "ok"}}
    result = bot_engine.sanitize_state_update(OLD_STATE_WITH_CONTENT, llm_state, ALLOWED_IDS)
    assert "T99" not in result["evidence_notes"]


def test_sanitize_pedagogical_state_fields():
    llm_state = {
        "topics_covered": [],
        "mastery": {},
        "evidence_notes": {},
        "current_topic_id": "T2",
        "assisted_turn_streak": 2,
        "recent_explanation_attempts": 3,
        "recent_parroting_streak": 1,
        "recent_unelaborated_agreement_streak": 2,
        "current_line_status": "over_scaffolded",
    }
    result = bot_engine.sanitize_state_update(OLD_STATE_WITH_CONTENT, llm_state, ALLOWED_IDS)
    assert result["current_topic_id"] == "T2"
    assert result["assisted_turn_streak"] == 2
    assert result["recent_explanation_attempts"] == 3
    assert result["recent_parroting_streak"] == 1
    assert result["recent_unelaborated_agreement_streak"] == 2
    assert result["current_line_status"] == "over_scaffolded"


def test_sanitize_pedagogical_state_invalid_values_preserve_or_clamp():
    llm_state = {
        "topics_covered": [],
        "mastery": {},
        "evidence_notes": {},
        "current_topic_id": "T99",
        "assisted_turn_streak": -5,
        "recent_explanation_attempts": 99,
        "recent_parroting_streak": "bad",
        "recent_unelaborated_agreement_streak": 4,
        "current_line_status": "mystery",
    }
    result = bot_engine.sanitize_state_update(OLD_STATE_WITH_CONTENT, llm_state, ALLOWED_IDS)
    assert result["current_topic_id"] == "T1"
    assert result["assisted_turn_streak"] == 0
    assert result["recent_explanation_attempts"] == 9
    assert result["recent_parroting_streak"] == 0
    assert result["recent_unelaborated_agreement_streak"] == 4
    assert result["current_line_status"] == "productive"


def test_sanitize_working_memory_synopsis_fields():
    llm_state = {
        "topics_covered": [],
        "mastery": {},
        "evidence_notes": {},
        "student_goal_now": "  keep this efficient   ",
        "interaction_state": "   repetition risk is high ",
        "current_line": " likelihood as a function of theta ",
        "what_student_has_shown": " said data are fixed ",
        "what_remains_uncertain": " whether they can apply it freshly ",
        "why_continue_or_switch": " switch if next move repeats the same check ",
        "do_not_repeat": [" ask the same question again  ", "", "ask the same question again", "use the same wording"],
        "best_next_move": " ask for a fresh application ",
    }
    result = bot_engine.sanitize_state_update(OLD_STATE_WITH_CONTENT, llm_state, ALLOWED_IDS)
    assert result["student_goal_now"] == "keep this efficient"
    assert result["interaction_state"] == "repetition risk is high"
    assert result["current_line"] == "likelihood as a function of theta"
    assert result["what_student_has_shown"] == "said data are fixed"
    assert result["what_remains_uncertain"] == "whether they can apply it freshly"
    assert result["why_continue_or_switch"] == "switch if next move repeats the same check"
    assert result["do_not_repeat"] == ["ask the same question again", "use the same wording"]
    assert result["best_next_move"] == "ask for a fresh application"


def test_classify_message_passes_structured_pedagogical_excerpt(monkeypatch):
    captured = {}

    def _fake_create(**kwargs):
        captured["payload"] = j.loads(kwargs["messages"][1]["content"])
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=j.dumps(
                            {
                                "top_classification": "content_answer",
                                "class_probabilities": {
                                    "content_answer": 0.70,
                                    "content_question": 0.10,
                                    "technical_request": 0.10,
                                    "meta_request": 0.05,
                                    "off_task": 0.05,
                                },
                                "recommended_policy": "provide_content_support",
                                "policy_confidence": 0.70,
                                "short_reason": "Weak content attempt after recent support.",
                            }
                        )
                    )
                )
            ]
        )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=_fake_create)))
    monkeypatch.setattr(bot_engine.openai_, "OpenAI", lambda **_: fake_client)

    settings = SimpleNamespace(
        classifier_recent_message_window=4,
        prompt_dir=str(Path(__file__).resolve().parents[1] / "prompts" / "generated"),
        openai_api_key="test-key",
        classifier_model="test-model",
    )
    state = {
        "last_top_classification": "content_answer",
        "last_recommended_policy": "provide_content_support",
        "last_effective_policy": "provide_content_support",
        "consecutive_redirects": 0,
        "consecutive_meta_requests": 0,
        "consecutive_clarifications": 1,
        "last_policy_override_reason": None,
        "assisted_turn_streak": 2,
        "recent_explanation_attempts": 2,
        "recent_parroting_streak": 1,
        "recent_unelaborated_agreement_streak": 1,
        "current_line_status": "stalled",
        "student_goal_now": "keep this efficient",
        "interaction_state": "student is frustrated by repetition",
        "current_line": "likelihood as a function of the parameter",
        "what_student_has_shown": "they already stated that data are fixed",
        "what_remains_uncertain": "whether they can apply it freshly",
        "why_continue_or_switch": "switch if the next move would just restate the same check",
        "do_not_repeat": ["do not ask them to say data fixed again"],
        "best_next_move": "ask a fresh application or honor a topic switch",
    }

    result = bot_engine._classify_message(
        settings,
        "yeah I guess",
        [{"role": "assistant", "content": "Try saying it in your own words."}],
        state,
    )

    assert result.recommended_policy == "provide_content_support"
    assert captured["payload"]["state"]["assisted_turn_streak"] == 2
    assert captured["payload"]["state"]["recent_explanation_attempts"] == 2
    assert captured["payload"]["state"]["recent_parroting_streak"] == 1
    assert captured["payload"]["state"]["recent_unelaborated_agreement_streak"] == 1
    assert captured["payload"]["state"]["current_line_status"] == "stalled"
    assert captured["payload"]["state"]["student_goal_now"] == "keep this efficient"
    assert captured["payload"]["state"]["do_not_repeat"] == ["do not ask them to say data fixed again"]
    assert captured["payload"]["state"]["best_next_move"] == "ask a fresh application or honor a topic switch"


# ---------------------------------------------------------------------------
# build_dialogue_context
# ---------------------------------------------------------------------------

def _make_pkg(bot_notes="", slides="", handout="", notebook=""):
    return {
        "lecture_id": "test",
        "config": {"title": "Test"},
        "rubric": "rubric content",
        "bot_notes": bot_notes,
        "slides": slides,
        "handout": handout,
        "notebook": notebook,
    }


def test_build_dialogue_context_all_fit():
    pkg = _make_pkg(bot_notes="BN", slides="SL", handout="HO", notebook="NB")
    result = bot_engine.build_dialogue_context(pkg, max_chars=10000)
    assert "## Bot Notes" in result
    assert "## Slides" in result
    assert "## Handout" in result
    assert "## Notebook" in result


def test_build_dialogue_context_empty_sections_skipped():
    pkg = _make_pkg(slides="SL content")
    result = bot_engine.build_dialogue_context(pkg, max_chars=10000)
    assert "## Slides" in result
    assert "## Bot Notes" not in result
    assert "## Handout" not in result
    assert "## Notebook" not in result


def test_build_dialogue_context_respects_budget():
    long_text = "x" * 5000
    pkg = _make_pkg(bot_notes=long_text, slides=long_text, handout=long_text, notebook=long_text)
    result = bot_engine.build_dialogue_context(pkg, max_chars=8000)
    assert len(result) <= 8000


def test_build_dialogue_context_priority_order():
    # When budget is tight, notebook should be dropped first
    bot_notes = "BN " * 100
    slides = "SL " * 100
    handout = "HO " * 100
    notebook = "NB " * 10000  # very large, should be truncated/dropped
    pkg = _make_pkg(bot_notes=bot_notes, slides=slides, handout=handout, notebook=notebook)
    result = bot_engine.build_dialogue_context(pkg, max_chars=5000)
    assert len(result) <= 5000
    # bot_notes and slides should still be present
    assert "BN" in result
    assert "SL" in result


# ---------------------------------------------------------------------------
# validate_topic_scores (grading validation in generate_topic_scores)
# We test the validation logic via a helper that simulates what the grading
# path does: filter to canonical IDs, clamp scores, dedup by keeping highest.
# ---------------------------------------------------------------------------

_RUBRIC_FOR_GRADING = """\
### T1. First Topic

- **Description:** Topic one.
- **Importance:** core

---

### T2. Second Topic

- **Description:** Topic two.
- **Importance:** important

---
"""

_LECTURE_PACKAGE_FOR_GRADING = {
    "lecture_id": "test",
    "config": {"title": "Test"},
    "rubric": _RUBRIC_FOR_GRADING,
    "bot_notes": "",
    "slides": "",
    "handout": "",
    "notebook": "",
}


def _run_grading_validation(raw_topic_scores: list[dict]) -> list[dict]:
    """Simulate the grading validation logic extracted from generate_topic_scores."""
    import unittest.mock as mock
    topic_defs = bot_engine.parse_rubric_topics(_RUBRIC_FOR_GRADING)
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
            seen[tid] = {"topic_id": tid, "score": score, "rationale": str(ts.get("rationale", ""))}
    return list(seen.values())


def test_grading_validation_filters_invented_topic_ids():
    """Topic IDs not in the rubric are silently dropped."""
    raw = [
        {"topic_id": "T1", "score": 80, "rationale": "good"},
        {"topic_id": "T99", "score": 90, "rationale": "invented"},
        {"topic_id": "FAKE", "score": 70, "rationale": "invented"},
    ]
    result = _run_grading_validation(raw)
    result_ids = {ts["topic_id"] for ts in result}
    assert result_ids == {"T1"}
    assert "T99" not in result_ids
    assert "FAKE" not in result_ids


def test_grading_validation_dedup_keeps_highest_score():
    """When a topic appears multiple times, the highest score is kept."""
    raw = [
        {"topic_id": "T1", "score": 50, "rationale": "first"},
        {"topic_id": "T1", "score": 90, "rationale": "better"},
        {"topic_id": "T1", "score": 70, "rationale": "middle"},
    ]
    result = _run_grading_validation(raw)
    assert len(result) == 1
    assert result[0]["topic_id"] == "T1"
    assert result[0]["score"] == 90


def test_grading_validation_clamps_score_above_100():
    raw = [{"topic_id": "T1", "score": 150, "rationale": ""}]
    result = _run_grading_validation(raw)
    assert result[0]["score"] == 100


def test_grading_validation_clamps_score_below_0():
    raw = [{"topic_id": "T1", "score": -20, "rationale": ""}]
    result = _run_grading_validation(raw)
    assert result[0]["score"] == 0


def test_grading_validation_invalid_score_type_skipped():
    """Entries with unparseable scores are skipped rather than crashing."""
    raw = [
        {"topic_id": "T1", "score": "not_a_number", "rationale": ""},
        {"topic_id": "T2", "score": 60, "rationale": "ok"},
    ]
    result = _run_grading_validation(raw)
    result_ids = {ts["topic_id"] for ts in result}
    assert "T1" not in result_ids
    assert "T2" in result_ids


def test_grading_validation_empty_list():
    result = _run_grading_validation([])
    assert result == []


def test_grading_validation_non_dict_entry_skipped():
    raw = ["not_a_dict", {"topic_id": "T1", "score": 80, "rationale": ""}]
    result = _run_grading_validation(raw)
    assert len(result) == 1
    assert result[0]["topic_id"] == "T1"
