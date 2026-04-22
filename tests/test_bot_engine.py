"""Unit tests for pure helper functions in app/bot_engine.py."""
import math
import unittest.mock as mock

import pytest

import app.bot_engine as bot_engine
import app.language_policy as language_policy
import app.prompt_loader as prompt_loader


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


def test_parse_rubric_topics_deduplicates_repeated_topic_headings():
    rubric = """\
### T1. Topic 1

- **Importance:** core

### T2. Topic 2

- **Importance:** important

## Evidence standards

### T1. Topic 1

Evidence text.

### T2. Topic 2

More evidence text.
"""
    topics = bot_engine.parse_rubric_topics(rubric)
    assert topics == [
        {"topic_id": "T1", "label": "Topic 1", "importance": "core"},
        {"topic_id": "T2", "label": "Topic 2", "importance": "important"},
    ]


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


# ---------------------------------------------------------------------------
# build_opening_message
# ---------------------------------------------------------------------------

def test_build_opening_message_includes_sampled_topic_labels(monkeypatch):
    lecture_package = {
        "lecture_id": "lecture_01",
        "config": {"title": "Lecture 1"},
        "rubric": SAMPLE_RUBRIC,
        "topics": [
            {"topic_id": "T1", "label": "Reality–Data–Model distinction", "importance": "core"},
            {"topic_id": "T2", "label": "Purpose of statistics", "importance": "core"},
            {"topic_id": "T3", "label": "Definition and structure of data", "importance": "important"},
        ],
    }
    monkeypatch.setattr(
        bot_engine.config_module,
        "get_settings",
        lambda: type("Settings", (), {"opening_topic_choice_count": 3})(),
    )
    message = bot_engine.build_opening_message(
        lecture_package,
        sampled_topic_ids=["T1", "T2", "T3"],
    )
    assert "Welcome to the review bot for Lecture 1." in message
    assert "A few good places to start are:" in message
    assert "- Reality–Data–Model distinction" in message
    assert "- Purpose of statistics" in message
    assert "- Definition and structure of data" in message
    assert "Which would you like to begin with?" in message


def test_build_opening_message_falls_back_without_resolved_sampled_topics(monkeypatch):
    lecture_package = {
        "lecture_id": "lecture_01",
        "config": {"title": "Lecture 1"},
        "rubric": SAMPLE_RUBRIC,
        "topics": [
            {"topic_id": "T1", "label": "Reality–Data–Model distinction", "importance": "core"},
        ],
    }
    monkeypatch.setattr(
        bot_engine.config_module,
        "get_settings",
        lambda: type("Settings", (), {"opening_topic_choice_count": 3})(),
    )
    message = bot_engine.build_opening_message(
        lecture_package,
        sampled_topic_ids=["T99"],
    )
    assert message == (
        "Welcome to the review bot for Lecture 1. "
        "We can start wherever feels most useful. "
        "What topic from this lecture would you like to begin with?"
    )


def test_generate_report_fallback_uses_scannable_bullets(monkeypatch):
    lecture_package = {
        "lecture_id": "lecture_01",
        "config": {"title": "Lecture 1"},
        "rubric": SAMPLE_RUBRIC,
    }
    grading_result = {
        "final_grade": 80,
        "explanation": "Strongest evidence is in model-vs-data distinctions.",
        "scored_topics": ["Reality–Data–Model distinction", "Purpose of statistics"],
        "missing_topics": ["Definition and structure of data"],
        "topic_scores": [
            {"topic_id": "T1", "score": 90},
            {"topic_id": "T2", "score": 70},
        ],
    }
    monkeypatch.setattr(
        bot_engine.config_module,
        "get_settings",
        lambda: type("Settings", (), {"openai_api_key": "test-key", "openai_model": "test-model"})(),
    )
    mock_client = mock.MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("boom")
    monkeypatch.setattr(bot_engine.openai_, "OpenAI", lambda **kwargs: mock_client)

    result = bot_engine.generate_report(
        lecture_package=lecture_package,
        messages=[{"role": "user", "content": "Hello"}],
        state={},
        grading_result=grading_result,
        session_id="session-1",
        student_id="student-1",
        timestamp_iso="2026-04-19T12:00:00+00:00",
    )

    assert "Summary:" in result["report_text"]
    assert "Stronger areas:" in result["report_text"]
    assert "Next steps:" in result["report_text"]
    assert "Coverage:" in result["report_text"]
    assert "- Reality–Data–Model distinction, Purpose of statistics." in result["report_text"]
    assert "- Not yet covered: Definition and structure of data." in result["report_text"]


def test_rewrite_opening_topic_selection_rewrites_prefix_match():
    lecture_package = {
        "lecture_id": "lecture_03",
        "config": {"title": "Lecture 3"},
        "rubric": SAMPLE_RUBRIC,
        "topics": [
            {"topic_id": "T1", "label": "Reading posterior output in ArviZ", "importance": "core"},
            {"topic_id": "T2", "label": "Why sample, and what a posterior draw is", "importance": "core"},
            {"topic_id": "T3", "label": "Point estimation from the posterior", "importance": "core"},
        ],
    }
    state = {
        "topics_sampled": ["T1", "T2", "T3"],
        "turn_count": 0,
        "current_topic_id": None,
    }
    rewritten = bot_engine.rewrite_opening_topic_selection(
        lecture_package=lecture_package,
        state=state,
        user_message="Why sample",
    )
    assert "Treat my message as a topic selection" in rewritten
    assert "Why sample, and what a posterior draw is" in rewritten


def test_rewrite_opening_topic_selection_leaves_nonopening_turn_alone():
    lecture_package = {
        "lecture_id": "lecture_03",
        "config": {"title": "Lecture 3"},
        "rubric": SAMPLE_RUBRIC,
        "topics": [
            {"topic_id": "T2", "label": "Why sample, and what a posterior draw is", "importance": "core"},
        ],
    }
    state = {
        "topics_sampled": ["T2"],
        "turn_count": 1,
        "current_topic_id": "T2",
    }
    original = "Why sample"
    rewritten = bot_engine.rewrite_opening_topic_selection(
        lecture_package=lecture_package,
        state=state,
        user_message=original,
    )
    assert rewritten == original


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
    "best_mastery": {},
    "evidence_notes": {},
    "current_topic_id": None,
    "tutor_comment": "",
    "private_decision_trace": None,
    "current_grade": 0.0,
    "timeout_warning_sent": False,
    "turn_count": 1,
}
ALLOWED_IDS = {"T1", "T2", "T3", "T4", "T5"}


def test_sanitize_topics_sampled_immutable():
    llm_state = {"topics_sampled": ["X9", "X10"], "topics_covered": [], "mastery": {}}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert result["topics_sampled"] == ["T1", "T2", "T3"]


def test_sanitize_turn_count_incremented():
    llm_state = {"topics_covered": [], "mastery": {}, "turn_count": 99}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert result["turn_count"] == OLD_STATE["turn_count"] + 1


def test_sanitize_topics_covered_filtered():
    llm_state = {"topics_covered": ["T1", "T99"], "mastery": {"T1": 45}}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert result["topics_covered"] == ["T1"]


def test_sanitize_mastery_keys_filtered():
    llm_state = {"topics_covered": [], "mastery": {"T1": 80, "T99": 50}}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert "T1" in result["mastery"]
    assert "T99" not in result["mastery"]


def test_sanitize_mastery_values_clamped():
    llm_state = {"topics_covered": [], "mastery": {"T1": 150, "T2": -10}}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert result["mastery"]["T1"] == 100
    assert result["mastery"]["T2"] == 0


def test_sanitize_best_mastery_preserved():
    old_state = dict(OLD_STATE)
    old_state["best_mastery"] = {"T1": 90}
    result = bot_engine.sanitize_state_update(old_state, {"mastery": {"T1": 20}}, ALLOWED_IDS)
    assert result["best_mastery"] == {"T1": 90}


def test_sanitize_current_grade_preserved():
    old_state = dict(OLD_STATE)
    old_state["current_grade"] = 55.0
    result = bot_engine.sanitize_state_update(old_state, {"mastery": {"T1": 100}}, ALLOWED_IDS)
    assert result["current_grade"] == 55.0


def test_sanitize_evidence_notes_filtered_and_merged():
    old_state = dict(OLD_STATE)
    old_state["evidence_notes"] = {"T1": "old note"}
    llm_state = {"evidence_notes": {"T1": "new note", "T99": "bad"}}
    result = bot_engine.sanitize_state_update(old_state, llm_state, ALLOWED_IDS)
    assert result["evidence_notes"] == {"T1": "new note"}


def test_sanitize_current_topic_id_filtered():
    llm_state = {"current_topic_id": "T99"}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert result["current_topic_id"] is None


def test_sanitize_tutor_comment_preserved_when_missing():
    old_state = dict(OLD_STATE)
    old_state["tutor_comment"] = "stay on T1"
    result = bot_engine.sanitize_state_update(old_state, {}, ALLOWED_IDS)
    assert result["tutor_comment"] == "stay on T1"


def test_sanitize_unknown_keys_dropped():
    llm_state = {"topics_covered": [], "mastery": {}, "extra_field": "bad"}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert "extra_field" not in result


def test_sanitize_decision_trace_stored_privately():
    llm_state = {"topics_covered": [], "mastery": {}}
    raw_trace = {
        "student_model": {
            "understanding": "partial distinction",
            "uncertainty": "mixing up prior and likelihood",
            "failure_mode": "label recognition only",
        },
        "evidence_target": {
            "topic_id": "T1",
            "element": "prior vs likelihood arrows",
            "target_type": "distinction",
            "why_now": "student is close but still blurry",
        },
        "move_candidates": [
            {
                "move_type": "contrastive_prompt",
                "prompt_sketch": "Which arrow means prior and which means likelihood?",
                "revealing": 2,
                "productive": 4,
                "fit": 5,
            }
        ],
        "chosen_move": {
            "move_type": "contrastive_prompt",
            "reason": "best low-revealing clarification",
        },
    }
    result = bot_engine.sanitize_state_update(
        OLD_STATE,
        llm_state,
        ALLOWED_IDS,
        raw_decision_trace=raw_trace,
    )
    assert result["private_decision_trace"]["step_6_chosen_topic"]["topic_id"] == "T1"
    assert result["private_decision_trace"]["step_8_evidence_target"]["topic_id"] == "T1"
    assert result["private_decision_trace"]["step_10_choice"]["chosen_move"] == "contrastive_prompt"


def test_sanitize_stepwise_decision_trace_preserved():
    llm_state = {"topics_covered": [], "mastery": {}}
    raw_trace = {
        "step_1_current_topic_option": {
            "topic_id": "T1",
            "why_consider": "current line still has value",
        },
        "step_2_alternative_topic_option": {
            "topic_id": "T2",
            "why_consider": "strong breadth alternative",
        },
        "step_3_current_topic_value": {
            "topic_id": "T1",
            "grade_value": 4,
            "pedagogical_value": 3,
            "engagement_value": 2,
            "reason": "one more check could land",
        },
        "step_4_alternative_topic_value": {
            "topic_id": "T2",
            "grade_value": 3,
            "pedagogical_value": 5,
            "engagement_value": 4,
            "reason": "better momentum",
        },
        "step_5_weighted_topic_comparison": {
            "grade_weight": 3,
            "pedagogical_weight": 5,
            "engagement_weight": 4,
            "current_topic_total": 29,
            "alternative_topic_total": 41,
            "preferred_topic_id": "T2",
            "reason": "alternative topic wins overall",
        },
        "step_6_chosen_topic": {
            "topic_id": "T2",
            "choice_type": "switch",
            "reason": "better overall value",
        },
        "step_7_student_model": {
            "understanding": "basic prior role",
            "uncertainty": "support constraints still blurry",
            "failure_mode": "speaks generically",
        },
        "step_8_evidence_target": {
            "topic_id": "T2",
            "element": "support of beta prior",
            "target_type": "criterion",
            "why_now": "needed for the next check",
        },
        "step_9_move_candidates": [
            {
                "move_type": "contrastive_prompt",
                "prompt_sketch": "Can the parameter be outside [0,1]?",
                "revealing": 2,
                "productive": 5,
                "fit": 5,
            }
        ],
        "step_10_choice": {
            "chosen_move": "contrastive_prompt",
            "reason": "best low-reveal move",
        },
        "step_11_reply_draft": {
            "draft": "Can a coin probability ever be outside [0,1]?",
        },
        "step_12_reply_check": {
            "most_productive": True,
            "minimally_revealing": True,
            "smuggles_answer": False,
            "asks_one_contribution": True,
        },
        "step_13_revision": {
            "revised": False,
            "reason": "draft already fits",
        },
        "step_14_final_move": {
            "move_type": "contrastive_prompt",
            "reason": "same as chosen move after review",
        },
    }
    result = bot_engine.sanitize_state_update(
        OLD_STATE,
        llm_state,
        ALLOWED_IDS,
        raw_decision_trace=raw_trace,
    )
    assert result["private_decision_trace"]["step_6_chosen_topic"]["topic_id"] == "T2"
    assert result["private_decision_trace"]["step_7_student_model"]["understanding"] == "basic prior role"
    assert result["private_decision_trace"]["step_12_reply_check"]["asks_one_contribution"] is True
    assert result["private_decision_trace"]["step_14_final_move"]["chosen_move"] == "contrastive_prompt"


# ---------------------------------------------------------------------------
# build_dialogue_context
# ---------------------------------------------------------------------------

def _make_pkg(bot_notes="", slides="", handout="", minutes="", notebook=""):
    context_sections = []
    if bot_notes:
        context_sections.append({"key": "bot_notes", "label": "Bot Notes", "content": bot_notes})
    if slides:
        context_sections.append({"key": "slides", "label": "Slides", "content": slides})
    if handout:
        context_sections.append({"key": "handout", "label": "Handout", "content": handout})
    if minutes:
        context_sections.append({"key": "minutes", "label": "Instructional Minutes", "content": minutes})
    if notebook:
        context_sections.append({"key": "notebook", "label": "Notebook", "content": notebook})
    return {
        "lecture_id": "test",
        "config": {"title": "Test"},
        "rubric": "rubric content",
        "context_sections": context_sections,
    }


def test_build_dialogue_context_all_fit():
    pkg = _make_pkg(bot_notes="BN", slides="SL", handout="HO", minutes="MN", notebook="NB")
    result = bot_engine.build_dialogue_context(pkg, max_chars=10000)
    assert "## Bot Notes" in result
    assert "## Slides" in result
    assert "## Handout" in result
    assert "## Instructional Minutes" in result
    assert "## Notebook" not in result


def test_build_dialogue_context_empty_sections_skipped():
    pkg = _make_pkg(slides="SL content")
    result = bot_engine.build_dialogue_context(pkg, max_chars=10000)
    assert "## Slides" in result
    assert "## Bot Notes" not in result
    assert "## Handout" not in result
    assert "## Instructional Minutes" not in result
    assert "## Notebook" not in result


def test_build_dialogue_context_respects_budget():
    long_text = "x" * 5000
    pkg = _make_pkg(bot_notes=long_text, slides=long_text, handout=long_text, minutes=long_text, notebook=long_text)
    result = bot_engine.build_dialogue_context(pkg, max_chars=8000)
    assert len(result) <= 8000


def test_build_dialogue_context_priority_order():
    # When budget is tight, notebook should be dropped first
    bot_notes = "BN " * 100
    slides = "SL " * 100
    handout = "HO " * 100
    minutes = "MN " * 100
    notebook = "NB " * 10000  # very large, should be truncated/dropped
    pkg = _make_pkg(bot_notes=bot_notes, slides=slides, handout=handout, minutes=minutes, notebook=notebook)
    result = bot_engine.build_dialogue_context(pkg, max_chars=5000)
    assert len(result) <= 5000
    # bot_notes and slides should still be present
    assert "BN" in result
    assert "SL" in result
    assert "MN" in result


def test_sanitize_assistant_message_replaces_bare_topic_ids():
    message = "You've got T3. Let's move to T4 next."
    topic_defs = [
        {"topic_id": "T3", "label": "Posterior draws", "importance": "core"},
        {"topic_id": "T4", "label": "Posterior plots", "importance": "core"},
    ]
    result = bot_engine.sanitize_assistant_message(message, topic_defs=topic_defs, timing_context=None)
    assert "T3" not in result
    assert "T4" not in result
    assert "Posterior draws" in result
    assert "Posterior plots" in result


def test_language_policy_accepts_short_english_topic_pick():
    assert language_policy.is_english_text("Why sample")


def test_language_policy_accepts_technical_english_noun_phrase():
    assert language_policy.is_english_text("Normalized cerebellar volume")


def test_language_policy_rejects_hebrew_text():
    assert not language_policy.is_english_text("למה לדגום")


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
    "context_sections": [],
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


# ---------------------------------------------------------------------------
# prompt loading
# ---------------------------------------------------------------------------

def test_load_prompt_template_reads_tutor_prompt_markdown():
    loaded = prompt_loader.load_prompt_template("tutor_prompt.md")
    assert "You are the runtime tutor for a lecture-review dialogue" in loaded


def test_tutor_prompt_uses_backend_runtime_context_names():
    loaded = prompt_loader.load_prompt_template("tutor_prompt.md")
    assert "current_tutoring_state" in loaded
    assert "session_timing" in loaded
    assert "rubric_text" in loaded
    assert "sampled_topics" in loaded
    assert "turn_context" not in loaded
    assert "warning_reason" not in loaded


def test_tutor_prompt_describes_backend_owned_lifecycle_boundaries():
    loaded = prompt_loader.load_prompt_template("tutor_prompt.md")
    assert "The backend owns the opening message." in loaded
    assert "Timeout closure is backend-owned." in loaded
    assert "session_timing.closing_mode" in loaded
    assert "session_timing.timeout_warning_sent" in loaded


def test_tutor_generator_prompt_validates_contracts_and_sparse_delta():
    loaded = prompt_loader.load_prompt_template("tutor_generator_prompt.md")
    assert "You are given three authoritative inputs" in loaded
    assert "Tutor Specification Contract" in loaded
    assert "Backend–Tutor Runtime Contract" in loaded
    assert "Step 1 — Check tutor-spec conformance" in loaded
    assert "Step 2 — Check backend compatibility" in loaded
    assert "Step 4 — Generate the runtime tutor prompt only if Steps 1 and 2 both pass" in loaded
    assert "`current_tutoring_state`" in loaded
    assert "`session_timing`" in loaded
    assert "`rubric_text`" in loaded
    assert "`turn_context`" not in loaded
    assert "`updated_state` is a **sparse delta**" in loaded
    assert "Do not drift into full-state replacement language." in loaded
    assert "Do not output the runtime tutor prompt unless both checks pass." in loaded


def test_generate_reply_uses_tutor_prompt_markdown_with_injected_context():
    lecture_package = {
        "lecture_id": "lecture_01",
        "config": {"title": "Lecture 1"},
        "rubric": SAMPLE_RUBRIC,
        "context_sections": [
            {"key": "bot_notes", "label": "Bot Notes", "content": "Bot notes"},
            {"key": "slides", "label": "Slides", "content": "Slides body"},
            {"key": "handout", "label": "Handout", "content": "Handout body"},
            {
                "key": "minutes",
                "label": "Instructional Minutes",
                "content": '{"lecture_metadata": {"title": "Lecture 1"}}',
            },
        ],
        "topics": [
            {"topic_id": "T1", "label": "Reality–Data–Model distinction", "importance": "core"},
            {"topic_id": "T2", "label": "Purpose of statistics", "importance": "core"},
        ],
    }
    state = {
        "topics_sampled": ["T1"],
        "topics_covered": ["T1"],
        "mastery": {"T1": 80},
        "best_mastery": {"T1": 92},
        "evidence_notes": {"T1": "old note"},
        "current_topic_id": "T1",
        "tutor_comment": "stay on topic",
        "current_grade": 55.0,
        "timeout_warning_sent": False,
        "turn_count": 2,
        "private_decision_trace": None,
    }
    mock_resp = mock.MagicMock()
    mock_resp.choices[0].message.content = (
        '{"assistant_message": "Next question", '
        '"updated_state": {"topics_covered": ["T1"], "mastery": {"T1": 80}, '
        '"evidence_notes": {"T1": "student made a real distinction"}, '
        '"current_topic_id": "T1", "tutor_comment": "Keep pressing on T1."}}'
    )
    mock_client = mock.MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp

    with mock.patch("openai.OpenAI", return_value=mock_client):
        assistant_message, updated_state = bot_engine.generate_reply(
            lecture_package=lecture_package,
            recent_messages=[],
            state=state,
            user_message="I think data are imperfect measurements.",
            timing_context={
                "minutes_remaining": 4,
                "minutes_elapsed": 16,
                "session_duration_minutes": 20,
                "closing_mode": True,
                "timeout_warning_sent": False,
            },
        )

    create_kwargs = mock_client.chat.completions.create.call_args.kwargs
    system_prompt = create_kwargs["messages"][0]["content"]
    assert "You are the runtime tutor for a lecture-review dialogue" in system_prompt
    assert "Runtime context" in system_prompt
    assert '"topic_id": "T1"' in system_prompt
    assert '"label": "Reality–Data–Model distinction"' in system_prompt
    assert '"topics_covered": [' in system_prompt
    assert '"best_mastery": {' in system_prompt
    assert '"session_timing": {' in system_prompt
    assert '"current_tutoring_state": {' in system_prompt
    assert '"rubric_text":' in system_prompt
    assert '"closing_mode": true' in system_prompt
    assert '"minutes_elapsed": 16' in system_prompt
    assert '"session_duration_minutes": 20' in system_prompt
    assert "## Instructional Minutes" in system_prompt
    assert "## Notebook" not in system_prompt
    assert '"turn_count": 3' in system_prompt
    assert assistant_message == "Next question"
    assert updated_state["turn_count"] == 3
    assert updated_state["evidence_notes"]["T1"] == "student made a real distinction"
