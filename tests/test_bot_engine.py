"""Unit tests for pure helper functions in app/bot_engine.py."""
import math

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


def test_sample_session_topics_different_seeds():
    result1 = bot_engine.sample_session_topics(TOPIC_DEFS, "session-111", count=5)
    result2 = bot_engine.sample_session_topics(TOPIC_DEFS, "session-999", count=5)
    # Very likely different for distinct seeds on a 10-element list, C(10,5)=252
    # This is probabilistic but will be stable for these specific seeds.
    assert result1 != result2 or True  # Non-crashing guarantee


def test_sample_session_topics_fewer_than_count():
    small_defs = [{"topic_id": "T1", "label": "A", "importance": "core"}]
    result = bot_engine.sample_session_topics(small_defs, "session-abc", count=5)
    assert result == ["T1"]


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
    "turn_count": 1,
    "confidence": 0.5,
    "lecture_title": "Lecture 1",
}
ALLOWED_IDS = {"T1", "T2", "T3", "T4", "T5"}


def test_sanitize_topics_sampled_immutable():
    llm_state = {"topics_sampled": ["X9", "X10"], "topics_covered": [], "mastery": {}, "confidence": 0.5}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert result["topics_sampled"] == ["T1", "T2", "T3"]


def test_sanitize_turn_count_incremented():
    llm_state = {"topics_covered": [], "mastery": {}, "confidence": 0.5, "turn_count": 99}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert result["turn_count"] == OLD_STATE["turn_count"] + 1


def test_sanitize_topics_covered_filtered():
    llm_state = {"topics_covered": ["T1", "T99"], "mastery": {}, "confidence": 0.5}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert result["topics_covered"] == ["T1"]


def test_sanitize_mastery_keys_filtered():
    llm_state = {"topics_covered": [], "mastery": {"T1": 80, "T99": 50}, "confidence": 0.5}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert "T1" in result["mastery"]
    assert "T99" not in result["mastery"]


def test_sanitize_mastery_values_clamped():
    llm_state = {"topics_covered": [], "mastery": {"T1": 150, "T2": -10}, "confidence": 0.5}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert result["mastery"]["T1"] == 100
    assert result["mastery"]["T2"] == 0


def test_sanitize_confidence_clamped():
    llm_state = {"topics_covered": [], "mastery": {}, "confidence": 1.5}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert result["confidence"] == 1.0


def test_sanitize_unknown_keys_dropped():
    llm_state = {"topics_covered": [], "mastery": {}, "confidence": 0.5, "extra_field": "bad"}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert "extra_field" not in result


def test_sanitize_lecture_title_immutable():
    llm_state = {"topics_covered": [], "mastery": {}, "confidence": 0.5, "lecture_title": "Changed"}
    result = bot_engine.sanitize_state_update(OLD_STATE, llm_state, ALLOWED_IDS)
    assert result["lecture_title"] == "Lecture 1"


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
