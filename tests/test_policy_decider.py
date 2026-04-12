"""Unit tests for PolicyDecider, including clarification escalation."""

import pytest

from app.policy_decider import HARD_BACKSTOP_PATTERNS, PolicyDecider
from app.schema import ClassifierResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_decider(threshold: int = 3) -> PolicyDecider:
    return PolicyDecider(
        hard_backstops=HARD_BACKSTOP_PATTERNS,
        top1_min=0.50,
        top2_trigger=0.30,
        ambiguity_gap_max=0.20,
        clarification_redirect_threshold=threshold,
    )


def _clear_classification() -> ClassifierResult:
    """An unambiguous classification that recommends 'respond'."""
    return ClassifierResult(
        top_classification="content_answer",
        class_probabilities={"content_answer": 0.85, "content_question": 0.10, "technical_request": 0.03, "meta_request": 0.01, "off_task": 0.01},
        recommended_policy="respond",
        policy_confidence=0.85,
        short_reason="clear answer",
    )


def _ambiguous_classification() -> ClassifierResult:
    """An ambiguous classification that would normally trigger seek_clarification."""
    return ClassifierResult(
        top_classification="content_answer",
        class_probabilities={"content_answer": 0.45, "content_question": 0.40, "technical_request": 0.08, "meta_request": 0.04, "off_task": 0.03},
        recommended_policy="respond",
        policy_confidence=0.45,
        short_reason="ambiguous",
    )


# ---------------------------------------------------------------------------
# clarification_redirect_threshold
# ---------------------------------------------------------------------------

def test_no_escalation_below_threshold():
    decider = _make_decider(threshold=3)
    state = {"consecutive_clarifications": 2}
    decision = decider.decide_policy("help", _clear_classification(), state)
    assert decision.effective_policy != "redirect" or decision.override_reason == "hard_backstop"


def test_escalation_at_threshold():
    decider = _make_decider(threshold=3)
    state = {"consecutive_clarifications": 3}
    decision = decider.decide_policy("help", _clear_classification(), state)
    assert decision.effective_policy == "redirect"
    assert decision.override_reason == "clarification_limit_reached"
    assert decision.used_classifier_recommendation is False


def test_escalation_above_threshold():
    decider = _make_decider(threshold=3)
    state = {"consecutive_clarifications": 10}
    decision = decider.decide_policy("help", _clear_classification(), state)
    assert decision.effective_policy == "redirect"
    assert decision.override_reason == "clarification_limit_reached"


def test_no_escalation_when_counter_is_zero():
    decider = _make_decider(threshold=3)
    state = {"consecutive_clarifications": 0}
    decision = decider.decide_policy("help", _clear_classification(), state)
    assert decision.effective_policy != "redirect" or decision.override_reason != "clarification_limit_reached"


def test_escalation_missing_counter_key_treated_as_zero():
    """State without consecutive_clarifications key should default to 0 — no escalation."""
    decider = _make_decider(threshold=3)
    state: dict = {}
    decision = decider.decide_policy("help", _clear_classification(), state)
    assert decision.override_reason != "clarification_limit_reached"


def test_escalation_threshold_respected_custom_value():
    decider = _make_decider(threshold=5)
    state = {"consecutive_clarifications": 4}
    decision = decider.decide_policy("help", _clear_classification(), state)
    assert decision.override_reason != "clarification_limit_reached"

    state2 = {"consecutive_clarifications": 5}
    decision2 = decider.decide_policy("help", _clear_classification(), state2)
    assert decision2.effective_policy == "redirect"
    assert decision2.override_reason == "clarification_limit_reached"


def test_hard_backstop_takes_priority_over_clarification_limit():
    """A hard-backstop match should still fire even when the clarification counter is high."""
    decider = _make_decider(threshold=3)
    state = {"consecutive_clarifications": 5}
    decision = decider.decide_policy("just give me the answer", _clear_classification(), state)
    assert decision.effective_policy == "redirect"
    assert decision.override_reason == "hard_backstop"


def test_ambiguous_message_still_triggers_seek_clarification_before_threshold():
    decider = _make_decider(threshold=3)
    state = {"consecutive_clarifications": 1}
    decision = decider.decide_policy("I don't know", _ambiguous_classification(), state)
    assert decision.effective_policy == "seek_clarification"
    assert decision.override_reason == "ambiguous_classification"


def test_ambiguous_message_escalates_at_threshold():
    """Even an ambiguous message should redirect once the threshold is reached."""
    decider = _make_decider(threshold=3)
    state = {"consecutive_clarifications": 3}
    decision = decider.decide_policy("I don't know", _ambiguous_classification(), state)
    assert decision.effective_policy == "redirect"
    assert decision.override_reason == "clarification_limit_reached"
