"""Unit tests for pure helper functions in app/bot_engine.py."""
import math
import pathlib as pathlib_
import unittest.mock as mock

import pytest

import app.bot_engine as bot_engine
import app.config as config_module
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


def test_sample_session_topics_keeps_lecture_order():
    result = bot_engine.sample_session_topics(TOPIC_DEFS, "session-abc", count=5)
    assert result == sorted(result, key=lambda topic_id: int(topic_id[1:]))


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

def test_build_opening_message_picks_from_the_package_seeded_by_session():
    openings = [f"Opening {i}" for i in range(5)]
    lecture_package = {"lecture_id": "lecture_01", "config": {"opening_messages": openings}}
    picks = {bot_engine.build_opening_message(lecture_package, f"session-{i}") for i in range(30)}
    assert picks == set(openings)
    assert bot_engine.build_opening_message(lecture_package, "session-a") == bot_engine.build_opening_message(
        lecture_package, "session-a"
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
    assert "Demonstrated:" in result["report_text"]
    assert "Taught in this session:" in result["report_text"]
    assert "Next steps:" in result["report_text"]
    assert "Coverage:" in result["report_text"]
    assert "- Reality–Data–Model distinction, Purpose of statistics." in result["report_text"]
    assert "- Not part of this session: Definition and structure of data." in result["report_text"]


# ---------------------------------------------------------------------------
# compute_weighted_grade
# ---------------------------------------------------------------------------

def test_compute_weighted_grade_all_100():
    scores = [{"topic_id": f"T{i}", "score": 100} for i in range(1, 5)]
    assert bot_engine.compute_weighted_grade(scores) == 100


def test_compute_weighted_grade_four_perfect_topics_reach_100():
    assert bot_engine.compute_weighted_grade([
        {"topic_id": "T1", "score": 100},
        {"topic_id": "T2", "score": 100},
        {"topic_id": "T3", "score": 100},
        {"topic_id": "T4", "score": 100},
    ]) == 100


def test_compute_weighted_grade_targets_exact_full_credit():
    assert bot_engine.compute_weighted_grade([
        {"topic_id": "T1", "score": 90},
        {"topic_id": "T2", "score": 82},
        {"topic_id": "T3", "score": 74},
        {"topic_id": "T4", "score": 62},
    ]) == 100


def test_compute_weighted_grade_teacher_session_reaches_full_credit():
    assert bot_engine.compute_weighted_grade([
        {"topic_id": "T6", "score": 90},
        {"topic_id": "T3", "score": 82},
        {"topic_id": "T7", "score": 78},
        {"topic_id": "T1", "score": 74},
        {"topic_id": "T4", "score": 68},
    ]) == 100


def test_compute_weighted_grade_cumulative_perfect_topic_geometry():
    perfect_scores = [{"topic_id": f"T{i}", "score": 100} for i in range(1, 5)]
    assert bot_engine.compute_weighted_grade(perfect_scores[:1]) == 55
    assert bot_engine.compute_weighted_grade(perfect_scores[:2]) == 80
    assert bot_engine.compute_weighted_grade(perfect_scores[:3]) == 93
    assert bot_engine.compute_weighted_grade(perfect_scores[:4]) == 100


def test_compute_weighted_grade_all_zero():
    scores = [{"topic_id": f"T{i}", "score": 0} for i in range(1, 5)]
    assert bot_engine.compute_weighted_grade(scores) == 0


def test_compute_weighted_grade_zero_padding():
    # Only 2 target-satisfied topics: slots 3 and 4 contribute 0.
    scores = [{"topic_id": "T1", "score": 90}, {"topic_id": "T2", "score": 82}]
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
    scores = [{"topic_id": f"T{i}", "score": 1} for i in range(1, 5)]
    assert bot_engine.compute_weighted_grade(scores) == 1


def test_compute_weighted_grade_below_target_partial():
    scores = [{"topic_id": f"T{i}", "score": 45} for i in range(1, 5)]
    assert bot_engine.compute_weighted_grade(scores) == 75


def test_compute_weighted_grade_at_lowest_target_band():
    scores = [{"topic_id": f"T{i}", "score": 40} for i in range(1, 5)]
    assert bot_engine.compute_weighted_grade(scores) == 67


def test_compute_weighted_grade_raw_above_target_does_not_exceed_weight():
    scores = [
        {"topic_id": "T1", "score": 95},
        {"topic_id": "T2", "score": 90},
        {"topic_id": "T3", "score": 80},
        {"topic_id": "T4", "score": 70},
    ]
    assert bot_engine.compute_weighted_grade(scores) == 100


def test_compute_weighted_grade_takes_top_4():
    # Five scored inputs, lowest should be ignored
    scores = [
        {"topic_id": "T1", "score": 80},
        {"topic_id": "T2", "score": 60},
        {"topic_id": "T3", "score": 40},
        {"topic_id": "T4", "score": 20},
        {"topic_id": "T5", "score": 10},
    ]
    assert bot_engine.compute_weighted_grade(scores) == 93


def test_compute_weighted_grade_ignores_fifth_rank_even_when_touched():
    scores = [
        {"topic_id": "T1", "score": 100},
        {"topic_id": "T2", "score": 100},
        {"topic_id": "T3", "score": 100},
        {"topic_id": "T4", "score": 0},
        {"topic_id": "T5", "score": 100},
    ]
    assert bot_engine.compute_weighted_grade(scores) == 100


def test_grade_impact_deltas_use_four_ranked_slots():
    sampled_topic_ids = ["T1", "T2", "T3", "T4", "T5"]
    best_mastery = {"T1": 100, "T2": 100, "T3": 100, "T4": 100, "T5": 0}

    assert bot_engine.compute_grade_impact_deltas(sampled_topic_ids, best_mastery)["T5"] == 0


def test_compute_ranked_credit_state_matches_grade():
    best_mastery = {"T1": 80, "T2": 60, "T3": 40, "T4": 20}
    credit_state = bot_engine.compute_ranked_credit_state(best_mastery)
    contribution_grade = math.floor(
        sum(row["credit_contribution"] for row in credit_state["ranked_credit_state"])
    )
    assert credit_state["grade"] == contribution_grade
    assert credit_state["grade"] == bot_engine.compute_weighted_grade([
        {"topic_id": topic_id, "score": score}
        for topic_id, score in best_mastery.items()
    ])


def test_compute_ranked_credit_state_raw_above_target_status():
    credit_state = bot_engine.compute_ranked_credit_state({"T1": 95})
    row = credit_state["ranked_credit_state"][0]
    assert row["status"] == "full_credit_satisfied"
    assert row["credit_completion"] == 1.0
    assert row["credit_contribution"] == 55
    assert row["raw_mastery"] == 95
    assert credit_state["session_credit_status"] == "in_progress"


def test_compute_ranked_credit_state_below_target_status():
    credit_state = bot_engine.compute_ranked_credit_state({"T1": 50})
    row = credit_state["ranked_credit_state"][0]
    assert row["status"] == "below_target"
    assert row["credit_completion"] == 0.7692
    assert row["raw_mastery_gap_to_rank_target"] == 15


def test_compute_ranked_credit_state_padding_and_full_credit_status():
    padded = bot_engine.compute_ranked_credit_state({"T1": 90})
    assert [row["topic_id"] for row in padded["ranked_credit_state"][1:]] == [None, None, None]
    assert padded["session_credit_status"] == "in_progress"

    full = bot_engine.compute_ranked_credit_state({"T6": 90, "T3": 82, "T7": 78, "T1": 74})
    assert full["session_credit_status"] == "full_credit_reached"
    assert {row["status"] for row in full["ranked_credit_state"]} == {"full_credit_satisfied"}


def test_compute_ranked_credit_state_ranks_by_raw_mastery():
    credit_state = bot_engine.compute_ranked_credit_state({"T1": 50, "T2": 90})
    assert credit_state["ranked_credit_state"][0]["topic_id"] == "T2"


def test_grade_impact_delta_reranking_satisfied_slot_can_be_positive():
    best_mastery = {"T1": 64, "T2": 60, "T3": 50, "T4": 40}
    assert bot_engine.compute_weighted_grade([
        {"topic_id": topic_id, "score": score}
        for topic_id, score in best_mastery.items()
    ]) == 99
    deltas = bot_engine.compute_grade_impact_deltas(["T1", "T2", "T3", "T4"], best_mastery)
    assert deltas["T2"] == 1


def test_grade_impact_deltas_full_credit_no_positive_delta():
    sampled_topic_ids = ["T1", "T2", "T3", "T4"]
    best_mastery = {"T1": 92, "T2": 85, "T3": 80, "T4": 70}
    deltas = bot_engine.compute_grade_impact_deltas(sampled_topic_ids, best_mastery)
    assert set(deltas.values()) == {0}
    assert bot_engine.compute_ranked_credit_state(best_mastery)["session_credit_status"] == "full_credit_reached"


def test_grade_impact_delta_zero_at_raw_100_and_never_negative():
    deltas = bot_engine.compute_grade_impact_deltas(
        ["T1", "T2"],
        {"T1": 100, "T2": 45},
    )
    assert deltas["T1"] == 0
    assert all(delta >= 0 for delta in deltas.values())


def test_grade_relevant_next_move_largest_delta_and_numeric_tie_break():
    best_mastery = {"T2": 0, "T10": 0}
    assert bot_engine.grade_relevant_next_move(["T10", "T2"], best_mastery) == "T2"


def test_grade_relevant_next_move_none_without_positive_delta():
    assert bot_engine.grade_relevant_next_move(
        ["T1", "T2", "T3", "T4"],
        {"T1": 100, "T2": 100, "T3": 100, "T4": 100},
    ) is None


def test_grade_policy_snapshot_names_calibrated_policy():
    assert bot_engine.grade_policy_snapshot() == {
        "policy_id": "ranked-target-saturation-v2",
        "ranked_topic_weights": [55, 25, 13, 7],
        "ranked_full_credit_targets": [65, 60, 50, 40],
    }


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


def test_sanitize_private_artifact_not_merged_into_state():
    llm_state = {
        "topics_covered": [],
        "mastery": {},
        "private_artifact": {"governing_condition": "ordinary turn"},
    }
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert "private_artifact" not in result
    assert "private_decision_trace" not in result


def test_validate_private_artifact_accepts_schema_conformant_object():
    schema_json = '{"type": "object", "required": ["check"], "properties": {"check": {"type": "string"}}}'
    error = bot_engine.validate_private_artifact({"check": "ok"}, schema_json)
    assert error is None


def test_validate_private_artifact_reports_missing_artifact():
    schema_json = '{"type": "object"}'
    error = bot_engine.validate_private_artifact(None, schema_json)
    assert error == "missing private_artifact"


def test_validate_private_artifact_reports_schema_mismatch():
    schema_json = '{"type": "object", "required": ["check"]}'
    error = bot_engine.validate_private_artifact({}, schema_json)
    assert "private_artifact validation failed" in error


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


def test_sanitize_assistant_message_repairs_bell_math_artifacts():
    message = (
        "One change score per subject: \x07change_i = y_{i,last} - y_{i,first}\x07. "
        "Use $ \x07lpha = 0.06 $ as the threshold."
    )
    result = bot_engine.sanitize_assistant_message(message, topic_defs=[], timing_context=None)
    assert "\x07" not in result
    assert r"\(change_i = y_{i,last} - y_{i,first}\)" in result
    assert r"\alpha = 0.06" in result


def test_sanitize_assistant_message_repairs_doubled_math_delimiters():
    message = r"Yes: \\(B=\Sigma_{12}\Sigma_{22}^{-1}\\) and \\[S=\Sigma_{11}\\]; keep \(K\) as is."
    result = bot_engine.sanitize_assistant_message(message, topic_defs=[], timing_context=None)
    assert result == r"Yes: \(B=\Sigma_{12}\Sigma_{22}^{-1}\) and \[S=\Sigma_{11}\]; keep \(K\) as is."


def test_sanitize_assistant_message_restores_truncated_punctuation_escapes():
    message = "the input\x13output view \x14 a \x18shared\x19 \x1chat R\x1d"
    result = bot_engine.sanitize_assistant_message(message, topic_defs=[], timing_context=None)
    assert result == "the input\u2013output view \u2014 a \u2018shared\u2019 \u201chat R\u201d"


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

# ---------------------------------------------------------------------------
# build_dialogue_system_prompt — caching structure
# ---------------------------------------------------------------------------

_CACHING_LECTURE_PACKAGE = {
    "lecture_id": "lecture_cache",
    "config": {"title": "Cache Test Lecture"},
    "rubric": SAMPLE_RUBRIC,
    "context_sections": [
        {"key": "bot_notes", "label": "Bot Notes", "content": "Important lecture notes here."},
    ],
    "topics": [
        {"topic_id": "T1", "label": "Reality–Data–Model distinction", "importance": "core"},
        {"topic_id": "T2", "label": "Purpose of statistics", "importance": "core"},
        {"topic_id": "T3", "label": "Definition and structure of data", "importance": "important"},
    ],
}

_DYNAMIC_SECTION_HEADER = "\n\n## Current session state\n"


def _make_topic_defs_for_caching():
    return bot_engine.resolve_topic_defs(_CACHING_LECTURE_PACKAGE)


def _make_lecture_context_for_caching():
    return bot_engine.build_dialogue_context(_CACHING_LECTURE_PACKAGE, 10000)


def test_build_dialogue_system_prompt_static_prefix_identical_for_different_states():
    """The static prefix must be byte-identical across sessions using the same lecture."""
    topic_defs = _make_topic_defs_for_caching()
    context = _make_lecture_context_for_caching()

    state_a = {
        "topics_sampled": ["T1"],
        "topics_covered": ["T1"],
        "mastery": {"T1": 80},
        "best_mastery": {"T1": 92},
        "evidence_notes": {"T1": "good note"},
        "current_topic_id": "T1",
        "tutor_comment": "pressing on T1",
        "turn_count": 5,
    }
    state_b = {
        "topics_sampled": ["T2", "T3"],
        "topics_covered": [],
        "mastery": {},
        "best_mastery": {},
        "evidence_notes": {},
        "current_topic_id": None,
        "tutor_comment": "",
        "turn_count": 0,
    }

    prompt_a = bot_engine.build_dialogue_system_prompt(
        lecture_package=_CACHING_LECTURE_PACKAGE,
        state=state_a,
        topic_defs=topic_defs,
        lecture_context=context,
        timing_context={"minutes_remaining": 5, "closing_mode": True},
    )
    prompt_b = bot_engine.build_dialogue_system_prompt(
        lecture_package=_CACHING_LECTURE_PACKAGE,
        state=state_b,
        topic_defs=topic_defs,
        lecture_context=context,
        timing_context={"minutes_remaining": 18, "closing_mode": False},
    )

    assert _DYNAMIC_SECTION_HEADER in prompt_a
    assert _DYNAMIC_SECTION_HEADER in prompt_b
    prefix_a = prompt_a[: prompt_a.index(_DYNAMIC_SECTION_HEADER)]
    prefix_b = prompt_b[: prompt_b.index(_DYNAMIC_SECTION_HEADER)]
    assert prefix_a == prefix_b


def test_build_dialogue_system_prompt_dynamic_section_includes_state_fields():
    """The dynamic suffix must contain all session-specific state fields."""
    topic_defs = _make_topic_defs_for_caching()
    context = _make_lecture_context_for_caching()
    state = {
        "topics_sampled": ["T1"],
        "topics_covered": ["T1"],
        "mastery": {"T1": 75},
        "best_mastery": {"T1": 90},
        "evidence_notes": {"T1": "criterion stated"},
        "current_topic_id": "T1",
        "tutor_comment": "keep going",
        "turn_count": 2,
    }

    prompt = bot_engine.build_dialogue_system_prompt(
        lecture_package=_CACHING_LECTURE_PACKAGE,
        state=state,
        topic_defs=topic_defs,
        lecture_context=context,
        timing_context={"minutes_remaining": 8},
    )

    assert _DYNAMIC_SECTION_HEADER in prompt
    dynamic_part = prompt[prompt.index(_DYNAMIC_SECTION_HEADER):]

    assert '"current_tutoring_state"' in dynamic_part
    assert '"session_timing"' in dynamic_part
    assert '"sampled_topics"' in dynamic_part
    assert '"mastery"' in dynamic_part
    assert '"turn_count": 3' in dynamic_part
    assert '"current_topic_id"' in dynamic_part
    assert '"topics_covered"' in dynamic_part
    assert '"grade_impact_deltas"' in dynamic_part
    assert '"session_credit_status": "in_progress"' in dynamic_part
    assert '"grade_relevant_next_move"' in dynamic_part
    assert '"ranked_credit_state"' in dynamic_part
    assert '"ranked_credit_state"' not in prompt[: prompt.index(_DYNAMIC_SECTION_HEADER)]


def test_build_dialogue_system_prompt_static_content_precedes_dynamic_state():
    """Rubric and lecture context must appear in the prompt before dynamic state fields."""
    topic_defs = _make_topic_defs_for_caching()

    lecture_package = dict(_CACHING_LECTURE_PACKAGE)
    lecture_package["rubric"] = "RUBRIC_MARKER_TEXT\n" + SAMPLE_RUBRIC
    lecture_package["context_sections"] = [
        {"key": "bot_notes", "label": "Bot Notes", "content": "CONTEXT_MARKER_TEXT notes here."},
    ]
    context = bot_engine.build_dialogue_context(lecture_package, 10000)
    state = {
        "topics_sampled": ["T1"],
        "topics_covered": [],
        "mastery": {},
        "best_mastery": {},
        "evidence_notes": {},
        "current_topic_id": None,
        "tutor_comment": "",
        "turn_count": 0,
    }

    prompt = bot_engine.build_dialogue_system_prompt(
        lecture_package=lecture_package,
        state=state,
        topic_defs=topic_defs,
        lecture_context=context,
        timing_context={"minutes_remaining": 15},
    )

    rubric_pos = prompt.index("RUBRIC_MARKER_TEXT")
    context_pos = prompt.index("CONTEXT_MARKER_TEXT")
    state_pos = prompt.index('"current_tutoring_state"')
    timing_pos = prompt.index('"session_timing"')
    sampled_pos = prompt.index('"sampled_topics"')

    assert rubric_pos < state_pos, "rubric_text must precede current_tutoring_state"
    assert rubric_pos < timing_pos, "rubric_text must precede session_timing"
    assert rubric_pos < sampled_pos, "rubric_text must precede sampled_topics"
    assert context_pos < state_pos, "lecture_context must precede current_tutoring_state"
    assert context_pos < timing_pos, "lecture_context must precede session_timing"
    assert context_pos < sampled_pos, "lecture_context must precede sampled_topics"


def test_build_dialogue_system_prompt_private_artifact_schema_in_static_prefix():
    """private_artifact_schema_json must appear in the static prefix, not the dynamic suffix."""
    topic_defs = _make_topic_defs_for_caching()
    context = _make_lecture_context_for_caching()
    state = {
        "topics_sampled": ["T1"],
        "topics_covered": [],
        "mastery": {},
        "best_mastery": {},
        "evidence_notes": {},
        "current_topic_id": None,
        "tutor_comment": "",
        "turn_count": 0,
    }
    schema_json = '{"type": "object", "required": ["check"], "properties": {"check": {"type": "string"}}}'

    prompt = bot_engine.build_dialogue_system_prompt(
        lecture_package=_CACHING_LECTURE_PACKAGE,
        state=state,
        topic_defs=topic_defs,
        lecture_context=context,
        timing_context={"minutes_remaining": 10},
        private_artifact_schema_json=schema_json,
    )

    assert _DYNAMIC_SECTION_HEADER in prompt
    prefix = prompt[: prompt.index(_DYNAMIC_SECTION_HEADER)]
    assert '"private_artifact_schema_json"' in prefix


def test_build_dialogue_system_prompt_all_tutor_required_fields_present():
    """All keys referenced by the tutor prompt template must be present somewhere in the prompt."""
    topic_defs = _make_topic_defs_for_caching()
    context = _make_lecture_context_for_caching()
    state = {
        "topics_sampled": ["T1", "T2"],
        "topics_covered": ["T1"],
        "mastery": {"T1": 80},
        "best_mastery": {"T1": 85},
        "evidence_notes": {"T1": "noted"},
        "current_topic_id": "T1",
        "tutor_comment": "",
        "turn_count": 1,
    }
    schema_json = '{"type": "object"}'

    prompt = bot_engine.build_dialogue_system_prompt(
        lecture_package=_CACHING_LECTURE_PACKAGE,
        state=state,
        topic_defs=topic_defs,
        lecture_context=context,
        timing_context={"minutes_remaining": 12, "closing_mode": False},
        private_artifact_schema_json=schema_json,
    )

    # All keys listed in the tutor prompt template's "Runtime inputs available to you"
    assert "lecture_title" in prompt
    assert "sampled_topics" in prompt
    assert "topic_structure_note" in prompt
    assert "current_tutoring_state" in prompt
    assert "session_timing" in prompt
    assert "rubric_text" in prompt
    assert "lecture_context" in prompt
    assert "private_artifact_schema_json" in prompt


def test_load_prompt_template_reads_tutor_prompt_markdown():
    loaded = prompt_loader.load_prompt_template("tutor_prompt.md")
    assert "You are a focused, lecture-grounded, Socratic-but-pragmatic tutor" in loaded


def test_tutor_prompt_uses_backend_runtime_context_names():
    loaded = prompt_loader.load_prompt_template("tutor_prompt.md")
    assert "current_tutoring_state" in loaded
    assert "session_timing" in loaded
    assert "rubric_text" in loaded
    assert "sampled_topics" in loaded
    assert "private_artifact_schema_json" in loaded
    assert "private_artifact" in loaded
    assert "turn_context" not in loaded
    assert "warning_reason" not in loaded


def test_tutor_prompt_describes_backend_owned_lifecycle_boundaries():
    loaded = prompt_loader.load_prompt_template("tutor_prompt.md")
    assert "Do not independently claim timeout status" in loaded
    assert "If lifecycle information is not supplied, do not infer timeout status" in loaded
    assert "session_timing" in loaded
    assert "timeout_warning_sent" in loaded


def test_tutor_prompt_keeps_private_artifacts_out_of_state_and_message():
    loaded = prompt_loader.load_prompt_template("tutor_prompt.md")
    assert "If private_artifact_schema_json is present, return exactly" in loaded
    assert "Do not place private_artifact content inside assistant_message" in loaded
    assert "must conform to that injected schema" in loaded
    assert "updated_state is conservative and sparse" in loaded


def test_tutor_generator_prompt_validates_contracts_and_sparse_delta():
    loaded = prompt_loader.load_prompt_template("tutor_generator_prompt.md")
    assert "You are given these authoritative inputs" in loaded
    assert "Tutor Specification Contract" in loaded
    assert "Backend–Tutor Runtime Contract" in loaded
    assert "Step 1 — Check tutor-spec conformance" in loaded
    assert "Step 2 — Check backend compatibility" in loaded
    assert "Step 4 — Generate the private artifact JSON Schema and runtime tutor prompt only if Steps 1 and 2 both pass" in loaded
    assert "`current_tutoring_state`" in loaded
    assert "`session_timing`" in loaded
    assert "`rubric_text`" in loaded
    assert "`private_artifact_schema_json`" in loaded
    assert "`turn_context`" not in loaded
    assert "`updated_state` is a **sparse delta**" in loaded
    assert "Missing C5 means implicit delegation to prompt generation and runtime." in loaded
    assert "Do not include missing C5 in Recommended omissions" in loaded
    assert "If C5 is present, preserve and operationalize it." in loaded
    assert "If C5 is absent, synthesize inspectability / self-verification commitments" in loaded
    assert "be structural, minimal, runtime-facing, and derived from pedagogical commitments" in loaded
    assert "The backend derives or sanitizes `topics_covered`; do not allow the tutor to return it as a tutor-updatable field." in loaded
    assert "`best_mastery`" in loaded
    assert "`current_grade`" in loaded
    assert "`timeout_warning_sent`" in loaded
    assert "### Private artifact schema" in loaded
    assert "Do **not** generate the private artifact schema." in loaded
    assert "Do not drift into full-state replacement language." in loaded
    assert "schema registries" in loaded
    assert "prompt history" in loaded
    assert "Do not output the runtime tutor prompt unless both checks pass." in loaded


def test_tutor_specification_contract_defines_c5_implicit_delegation():
    contract = (prompt_loader._REPO_ROOT / "docs" / "tutor_specification_contract.md").read_text(encoding="utf-8")
    assert "C5. Inspectability / self-verification commitments" in contract
    assert "If C5 is present, it governs" in contract
    assert "If C5 is absent, inspectability and self-verification commitments are implicitly delegated" in contract
    assert "Missing C5 is therefore not a conformance failure" in contract


def test_backend_runtime_contract_defines_private_artifact_mechanics():
    contract = (prompt_loader._REPO_ROOT / "docs" / "backend_tutor_contract.md").read_text(encoding="utf-8")
    assert "private_artifact_schema_json" in contract
    assert "private_artifact" in contract
    assert "`private_artifact` must not appear inside `updated_state`" in contract
    assert "The backend must make one bounded repair attempt before accepting the turn." in contract
    assert "If repair fails, enter controlled fallback mode" in contract


def test_current_tutor_specification_defines_c5_and_delegates_runtime_mechanics():
    spec = (prompt_loader._REPO_ROOT / "docs" / "tutor_specification.md").read_text(encoding="utf-8")
    assert "Closing is not a tutor-owned pedagogical judgment" in spec
    assert "This specification does not define session creation, opening messages, timeout behavior" in spec


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
    }
    mock_resp = mock.MagicMock()
    mock_resp.choices[0].message.content = (
        "<assistant_message>\nNext question\n</assistant_message>\n"
        '{"updated_state": {"topics_covered": ["T1"], "mastery": {"T1": 80}, '
        '"evidence_notes": {"T1": "student made a real distinction"}, '
        '"current_topic_id": "T1", "tutor_comment": "Keep pressing on T1."}, '
        '"private_artifact": {"check": "ok"}}'
    )
    mock_client = mock.MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp

    with mock.patch("openai.OpenAI", return_value=mock_client):
        assistant_message, updated_state, private_artifact = bot_engine.generate_reply(
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
            private_artifact_schema_json='{"type": "object", "required": ["check"]}',
        )

    create_kwargs = mock_client.chat.completions.create.call_args.kwargs
    system_prompt = create_kwargs["messages"][0]["content"]
    assert "You are a focused, lecture-grounded, Socratic-but-pragmatic tutor" in system_prompt
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
    assert '"private_artifact_schema_json":' in system_prompt
    assert "## Instructional Minutes" in system_prompt
    assert "## Notebook" not in system_prompt
    assert '"turn_count": 3' in system_prompt
    assert assistant_message == "Next question"
    assert updated_state["turn_count"] == 3
    assert updated_state["evidence_notes"]["T1"] == "student made a real distinction"
    assert private_artifact == {"check": "ok"}


# ---------------------------------------------------------------------------
# Chat language (CHAT_LANGUAGE)
# ---------------------------------------------------------------------------

def test_sanitize_assistant_message_replaces_hebrew_when_chat_language_is_english():
    result = bot_engine.sanitize_assistant_message(
        "נכון. למה השונות קטנה?", topic_defs=[], timing_context=None, chat_language="english"
    )
    assert result == language_policy.ENGLISH_ONLY_ASSISTANT_FALLBACK


def test_sanitize_assistant_message_keeps_hebrew_when_chat_language_is_any():
    result = bot_engine.sanitize_assistant_message(
        "נכון. למה השונות קטנה?", topic_defs=[], timing_context=None, chat_language="any"
    )
    assert result == "נכון. למה השונות קטנה?"


@pytest.mark.parametrize("chat_language", ["english", "any"])
def test_dialogue_prompt_tells_the_tutor_the_chat_language(monkeypatch, chat_language):
    settings = config_module.Settings(chat_language=chat_language)
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)

    prompt = bot_engine.build_dialogue_system_prompt(
        lecture_package=_CACHING_LECTURE_PACKAGE,
        state={"topics_sampled": ["T1"], "turn_count": 0},
        topic_defs=_make_topic_defs_for_caching(),
        lecture_context=_make_lecture_context_for_caching(),
    )

    assert f'"chat_language": "{chat_language}"' in prompt


@pytest.mark.parametrize("value,expected", [("english", "english"), ("English", "english"), ("any", "any"), (" any, ", "any")])
def test_chat_language_setting_accepts_english_and_any(value, expected):
    assert config_module.Settings(chat_language=value).chat_language == expected


@pytest.mark.parametrize("value", ["hebrew", "hebrew,english", ""])
def test_chat_language_setting_rejects_other_values(value):
    with pytest.raises(ValueError):
        config_module.Settings(chat_language=value)


# ---------------------------------------------------------------------------
# PML tutor prompt (scope issue #31)
# ---------------------------------------------------------------------------

PML_PROMPT = "pml_tutor_prompt.md"


def test_pml_tutor_prompt_states_the_backend_contract():
    prompt = prompt_loader.load_prompt_template(PML_PROMPT)
    for required in (
        "assistant_message",
        "updated_state",
        "private_artifact",
        "private_artifact_schema_json",
        "mastery",
        "evidence_notes",
        "current_topic_id",
        "tutor_comment",
        "grade_impact_deltas",
        "chat_language",
        "rubric_text",
        "lecture_context",
    ):
        assert required in prompt, required


def test_pml_tutor_prompt_names_the_math_delimiters_the_chat_renders():
    prompt = prompt_loader.load_prompt_template(PML_PROMPT)
    chat_js = (pathlib_.Path(__file__).resolve().parents[1] / "app/static/chat.js").read_text(encoding="utf-8")
    assert '{ left: "\\\\(", right: "\\\\)", display: false }' in chat_js
    assert "\\(" in prompt
    assert "$...$" in prompt


def test_pml_tutor_prompt_handles_the_five_minute_warning():
    prompt = prompt_loader.load_prompt_template(PML_PROMPT)
    for required in ("session_timing.closing_mode", "timeout_warning_sent", "minutes_remaining"):
        assert required in prompt, required


def test_pml_tutor_prompt_has_a_valid_private_artifact_schema():
    schema_json = prompt_loader.load_private_artifact_schema_json(PML_PROMPT)
    assert schema_json is not None
    import json as json_
    import jsonschema as jsonschema_
    jsonschema_.Draft202012Validator.check_schema(json_.loads(schema_json))


def test_dialogue_prompt_uses_the_lecture_selected_tutor_prompt():
    package = dict(_CACHING_LECTURE_PACKAGE, config={"title": "Cache Test Lecture", "tutor_prompt_template": PML_PROMPT})
    prompt = bot_engine.build_dialogue_system_prompt(
        lecture_package=package,
        state={"topics_sampled": ["T1"], "turn_count": 0},
        topic_defs=_make_topic_defs_for_caching(),
        lecture_context=_make_lecture_context_for_caching(),
    )
    assert prompt.startswith("You are the tutor")

def test_build_dialogue_context_logs_when_it_truncates(caplog):
    package = {
        "lecture_id": "lecture_big",
        "context_sections": [
            {"key": "slides", "label": "Slides", "content": "s" * 80},
            {"key": "handout", "label": "Handout", "content": "h" * 80},
            {"key": "minutes", "label": "Instructional Minutes", "content": "m" * 80},
        ],
    }

    with caplog.at_level("WARNING"):
        context = bot_engine.build_dialogue_context(package, 120)

    assert len(context) <= 120
    assert "lecture_big" in caplog.text
    assert "Handout cut" in caplog.text
    assert "dropped: Instructional Minutes" in caplog.text


def test_build_dialogue_context_is_silent_when_everything_fits(caplog):
    package = {
        "lecture_id": "lecture_small",
        "context_sections": [{"key": "slides", "label": "Slides", "content": "short"}],
    }

    with caplog.at_level("WARNING"):
        bot_engine.build_dialogue_context(package, 1000)

    assert caplog.text == ""


# ---------------------------------------------------------------------------
# Tagged reply format (scope issue #31, PR E)
# ---------------------------------------------------------------------------

_TAGGED_STATE = (
    '{"updated_state":{"mastery":{"T1":72},"evidence_notes":{"T1":"explained the arrow"}},'
    '"private_artifact":{"self_check":{"assistant_message_matches_move":true}}}'
)


def test_the_pml_prompt_declares_the_current_backend_contract():
    assert prompt_loader.declared_backend_contract(prompt_loader.load_prompt_template(PML_PROMPT)) == prompt_loader.BACKEND_CONTRACT_VERSION
    assert prompt_loader.prompt_contract_problem(PML_PROMPT) is None


def test_the_statistics_prompt_is_refused_until_it_is_regenerated():
    problem = prompt_loader.prompt_contract_problem("tutor_prompt.md")
    assert problem is not None and "declares no backend contract" in problem


def test_a_prompt_for_another_contract_version_is_refused():
    assert prompt_loader.declared_backend_contract("Backend contract: 0.3.0\n\nYou are a tutor.") == "0.3.0"
    assert prompt_loader.declared_backend_contract("You are a tutor.\nBackend contract: 0.6.1\n") is None


def test_the_pml_prompt_declares_its_lecture_package_contract():
    assert prompt_loader.declared_package_contract(prompt_loader.load_prompt_template(PML_PROMPT)) == "pml-brief-2"
    assert prompt_loader.declared_package_contract("Backend contract: 0.6.1\n\nYou are a tutor.") is None
    assert prompt_loader.declared_package_contract("Lecture package contract: x-1\n\nYou are a tutor.") == "x-1"


def test_both_declarations_are_removed_from_the_prompt_text():
    text = "Backend contract: 0.6.1\n\nLecture package contract: pml-brief-1\n\nYou are a tutor."
    assert prompt_loader.strip_contract_declaration(text) == "You are a tutor."


def test_the_contract_declaration_is_removed_before_the_model_sees_the_prompt():
    package = dict(_CACHING_LECTURE_PACKAGE, config={"title": "Cache Test Lecture", "tutor_prompt_template": PML_PROMPT})
    prompt = bot_engine.build_dialogue_system_prompt(
        lecture_package=package,
        state={"topics_sampled": ["T1"], "turn_count": 0},
        topic_defs=_make_topic_defs_for_caching(),
        lecture_context=_make_lecture_context_for_caching(),
    )
    assert "Backend contract:" not in prompt


def test_parse_tagged_reply_keeps_latex_as_written():
    raw = "<assistant_message>\nGiven \\(\\theta\\), the tosses are independent.\n\nWhy?\n</assistant_message>\n" + _TAGGED_STATE
    parsed = bot_engine.parse_tagged_reply(raw)
    assert parsed["assistant_message"] == "Given \\(\\theta\\), the tosses are independent.\n\nWhy?"
    assert parsed["updated_state"]["mastery"] == {"T1": 72}
    assert parsed["private_artifact"]["self_check"]["assistant_message_matches_move"] is True


def test_parse_tagged_reply_accepts_a_json_escaped_closing_tag():
    raw = "<assistant_message>\nWhat does the width mean?<\\/assistant_message>\n" + _TAGGED_STATE
    assert bot_engine.parse_tagged_reply(raw)["assistant_message"] == "What does the width mean?"
    raw = "What does the width mean?<\\/assistant_message>" + _TAGGED_STATE
    assert bot_engine.parse_tagged_reply(raw)["assistant_message"] == "What does the width mean?"


def test_parse_tagged_reply_closes_a_missing_final_brace():
    raw = "<assistant_message>\nWhy?\n</assistant_message>\n" + _TAGGED_STATE[:-1]
    assert bot_engine.parse_tagged_reply(raw)["updated_state"]["mastery"] == {"T1": 72}


def test_parse_tagged_reply_without_tags_splits_at_the_state_object():
    raw = "You used the forward law, \\(p(y)\\).\n\nWhat changes if \\(\\Omega\\) doubles?" + _TAGGED_STATE
    parsed = bot_engine.parse_tagged_reply(raw)
    assert parsed["assistant_message"] == "You used the forward law, \\(p(y)\\).\n\nWhat changes if \\(\\Omega\\) doubles?"
    assert parsed["updated_state"]["evidence_notes"] == {"T1": "explained the arrow"}


def test_parse_tagged_reply_without_a_state_object_keeps_the_message():
    parsed = bot_engine.parse_tagged_reply("Why does \\(\\Omega\\) appear inside \\(\\Sigma_{yy}\\)?")
    assert parsed["assistant_message"] == "Why does \\(\\Omega\\) appear inside \\(\\Sigma_{yy}\\)?"
    assert parsed["updated_state"] == {}
    assert parsed["private_artifact"] is None


def test_parse_tagged_reply_rejects_an_empty_message():
    with pytest.raises(ValueError):
        bot_engine.parse_tagged_reply("<assistant_message>\n</assistant_message>\n" + _TAGGED_STATE)


def test_generate_reply_requests_plain_text_and_parses_tags():
    package = dict(_CACHING_LECTURE_PACKAGE, config={"title": "Cache Test Lecture", "tutor_prompt_template": PML_PROMPT})
    mock_resp = mock.MagicMock()
    mock_resp.choices[0].message.content = "<assistant_message>\nWhy \\(A\\Sigma A^T\\)?\n</assistant_message>\n" + _TAGGED_STATE
    mock_client = mock.MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp
    with mock.patch("openai.OpenAI", return_value=mock_client):
        assistant_message, updated_state, private_artifact = bot_engine.generate_reply(
            lecture_package=package,
            recent_messages=[],
            state={"topics_sampled": ["T1"], "turn_count": 0},
            user_message="Let's start.",
        )
    assert "response_format" not in mock_client.chat.completions.create.call_args.kwargs
    assert assistant_message == "Why \\(A\\Sigma A^T\\)?"
    assert updated_state["mastery"] == {"T1": 72}
    assert private_artifact == {"self_check": {"assistant_message_matches_move": True}}
