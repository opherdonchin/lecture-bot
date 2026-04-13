"""Unit tests for the redesigned tutoring helpers in app/bot_engine.py."""
import json as j
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.bot_engine as bot_engine


SAMPLE_RUBRIC = """\
### T1. Reality–Data distinction

- **Description:** Data are finite and imperfect.
- **Importance:** core

---

### T2. Interpretation of probability

- **Description:** Probability statements as degrees of uncertainty.
- **Importance:** core

---

### T3. Measurement quality

- **Description:** Reliability and error.
- **Importance:** important
"""


LECTURE_PACKAGE = {
    "lecture_id": "lecture_01",
    "config": {"title": "Lecture 1: Probabilities"},
    "rubric": SAMPLE_RUBRIC,
    "bot_notes": "Use evidence to update degrees of uncertainty. Prefer the lecture's own wording.",
    "slides": "Likelihood is the plausibility of parameter values given fixed data.",
    "handout": "Evidence is the normalizing factor in Bayes' rule.",
    "notebook": "Grid approximation uses a finite set of candidate parameter values.",
}


TOPIC_DEFS = bot_engine.parse_rubric_topics(SAMPLE_RUBRIC)
ALLOWED_IDS = {topic["topic_id"] for topic in TOPIC_DEFS}


def _state(**overrides):
    base = {
        "topics_sampled": ["T1", "T2", "T3"],
        "topics_covered": [],
        "mastery": {},
        "evidence_notes": {},
        "turn_count": 0,
        "lecture_title": "Lecture 1: Probabilities",
        "timeout_warning_sent": False,
        "current_topic_id": None,
        "current_line_status": "unclear",
        "last_challenge_level": 1,
        "must_not_repeat": [],
        "lecture_native_only": True,
        "last_action": None,
        "last_target_topic_id": None,
        "last_reason_code": None,
        "last_repetition_complaint": False,
        "last_assistant_had_content_question": False,
        "last_top_classification": None,
        "last_recommended_policy": None,
        "last_effective_policy": None,
        "consecutive_redirects": 0,
        "consecutive_meta_requests": 0,
        "consecutive_clarifications": 0,
        "last_policy_override_reason": None,
    }
    base.update(overrides)
    return base


def test_parse_rubric_topics():
    topics = bot_engine.parse_rubric_topics(SAMPLE_RUBRIC)
    assert [t["topic_id"] for t in topics] == ["T1", "T2", "T3"]
    assert [t["importance"] for t in topics] == ["core", "core", "important"]


def test_sample_session_topics_deterministic():
    result1 = bot_engine.sample_session_topics(TOPIC_DEFS, "session-abc", count=2)
    result2 = bot_engine.sample_session_topics(TOPIC_DEFS, "session-abc", count=2)
    assert result1 == result2
    assert len(result1) == 2


def test_build_opening_message_lists_topic_choices(monkeypatch):
    monkeypatch.setattr(bot_engine.config_module, "get_settings", lambda: SimpleNamespace(opening_topic_choice_count=3))
    message = bot_engine.build_opening_message(LECTURE_PACKAGE, sampled_topic_ids=["T1", "T3", "T2"])
    assert "A few good places to start are:" in message
    assert "- Reality–Data distinction" in message
    assert "- Measurement quality" in message
    assert message.endswith("Which would you like to begin with?")


def test_compute_weighted_grade_uses_top_five():
    scores = [
        {"topic_id": "T1", "score": 100},
        {"topic_id": "T2", "score": 90},
        {"topic_id": "T3", "score": 80},
        {"topic_id": "T4", "score": 70},
        {"topic_id": "T5", "score": 60},
        {"topic_id": "T6", "score": 50},
    ]
    assert bot_engine.compute_weighted_grade(scores) == 92


def test_build_dialogue_context_respects_budget():
    context = bot_engine.build_dialogue_context(LECTURE_PACKAGE, max_chars=140)
    assert len(context) <= 140
    assert "## Bot Notes" in context


def test_sanitize_state_update_preserves_backend_owned_fields():
    old_state = _state(
        current_topic_id="T1",
        current_line_status="productive",
        last_challenge_level=4,
        must_not_repeat=["avoid the old definition check"],
        lecture_native_only=True,
        last_action="escalate",
        last_target_topic_id="T1",
        last_reason_code="needs_transfer_check",
        last_repetition_complaint=True,
        last_assistant_had_content_question=True,
        topics_covered=["T1"],
        mastery={"T1": 55},
        evidence_notes={"T1": "criterion answer already shown"},
        turn_count=2,
    )
    llm_state = {
        "current_topic_id": "T2",
        "current_line_status": "low_yield",
        "last_challenge_level": 8,
        "must_not_repeat": [" ask the same thing again ", "ask the same thing again"],
        "topics_covered": ["T2", "bad"],
        "mastery": {"T2": 140},
        "evidence_notes": {"T2": "fresh transfer shown", "bad": 3},
    }

    result = bot_engine.sanitize_state_update(old_state, llm_state, ALLOWED_IDS)

    assert result["current_topic_id"] == "T2"
    assert result["current_line_status"] == "low_yield"
    assert result["last_challenge_level"] == 7
    assert result["must_not_repeat"] == ["ask the same thing again"]
    assert result["topics_covered"] == ["T1", "T2"]
    assert result["mastery"]["T2"] == 100
    assert result["evidence_notes"]["T2"] == "fresh transfer shown"
    assert result["lecture_native_only"] is True
    assert result["last_action"] == "escalate"
    assert result["turn_count"] == 3


def test_classify_message_passes_compact_excerpt(monkeypatch):
    captured = {}

    def _fake_create(**kwargs):
        captured["payload"] = j.loads(kwargs["messages"][1]["content"])
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=j.dumps(
                            {
                                "top_classification": "technical_request",
                                "class_probabilities": {
                                    "content_answer": 0.10,
                                    "content_question": 0.05,
                                    "technical_request": 0.80,
                                    "meta_request": 0.03,
                                    "off_task": 0.02,
                                },
                                "recommended_policy": "provide_technical_support",
                                "policy_confidence": 0.80,
                                "short_reason": "The student is steering the session.",
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
    state = _state(
        current_topic_id="T1",
        current_line_status="low_yield",
        last_challenge_level=5,
        last_action="repair",
        last_target_topic_id="T2",
        last_reason_code="current_line_low_yield",
        last_repetition_complaint=True,
        must_not_repeat=["do not ask the same definition check"],
    )

    result = bot_engine._classify_message(
        settings,
        "Ask me something harder that will actually get points.",
        [{"role": "assistant", "content": "Can you define likelihood again?"}],
        state,
    )

    assert result.recommended_policy == "provide_technical_support"
    excerpt = captured["payload"]["state"]
    assert excerpt["current_topic_id"] == "T1"
    assert excerpt["current_line_status"] == "low_yield"
    assert excerpt["last_challenge_level"] == 5
    assert excerpt["last_action"] == "repair"
    assert excerpt["must_not_repeat"] == ["do not ask the same definition check"]
    assert excerpt["lecture_native_only"] is True


def test_action_hint_switches_when_line_is_low_yield_and_high_value_topic_is_open():
    state = _state(
        current_topic_id="T1",
        current_line_status="low_yield",
        topics_covered=["T1"],
        mastery={"T1": 65},
        last_challenge_level=4,
    )

    hint = bot_engine._compute_action_hint(
        state,
        LECTURE_PACKAGE,
        [{"role": "assistant", "content": "Can you define likelihood again?"}],
        "Okay.",
    )

    assert hint["recommended_action"] == "switch"
    assert hint["target_topic_id"] in {"T2", "T3"}
    assert hint["reason_code"] == "current_line_low_yield"


def test_action_hint_escalates_for_harder_question_request():
    state = _state(
        current_topic_id="T1",
        current_line_status="productive",
        mastery={"T1": 48},
        last_challenge_level=3,
    )

    hint = bot_engine._compute_action_hint(
        state,
        LECTURE_PACKAGE,
        [{"role": "assistant", "content": "What is likelihood?"}],
        "That's too easy. Ask me something harder that gets points.",
    )

    assert hint["recommended_action"] == "escalate"
    assert hint["challenge_level"] >= 5
    assert "do not fall back to a recognition-only check" in hint["must_not_repeat"]


def test_action_hint_repairs_or_switches_after_repetition_complaint():
    state = _state(
        current_topic_id="T1",
        current_line_status="productive",
        mastery={"T1": 20},
        last_challenge_level=2,
    )

    hint = bot_engine._compute_action_hint(
        state,
        LECTURE_PACKAGE,
        [{"role": "assistant", "content": "Can you define this again?"}],
        "You're repeating yourself. What exactly was missing?",
    )

    assert hint["recommended_action"] in {"repair", "switch"}
    assert "do not ask the same question again" in hint["must_not_repeat"]


def test_action_hint_switch_request_changes_target_topic():
    state = _state(
        current_topic_id="T1",
        current_line_status="productive",
        topics_covered=["T1"],
        mastery={"T1": 80},
    )

    hint = bot_engine._compute_action_hint(
        state,
        LECTURE_PACKAGE,
        [{"role": "assistant", "content": "Can you apply that idea?"}],
        "Let's switch topics.",
    )

    assert hint["recommended_action"] == "switch"
    assert hint["target_topic_id"] in {"T2", "T3"}
    assert hint["reason_code"] == "student_requested_switch"


def test_professor_can_max_out_path_exposes_other_high_value_topics():
    state = _state(
        current_topic_id="T1",
        current_line_status="ready_to_wrap",
        topics_covered=["T1"],
        mastery={"T1": 92},
        last_challenge_level=6,
    )

    hint = bot_engine._compute_action_hint(
        state,
        LECTURE_PACKAGE,
        [{"role": "assistant", "content": "What practical meaning would that have?"}],
        "Ready for the next topic.",
    )

    assert hint["recommended_action"] == "switch"
    assert hint["target_topic_id"] in {"T2", "T3"}
    assert hint["reason_code"] == "high_weight_open_topic"


def test_build_system_prompt_uses_unified_tutor_prompt(tmp_path, monkeypatch):
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    (prompt_dir / "tutor_prompt.md").write_text("Mode: {tutor_mode}\nAction: {recommended_action}\nContext: {context}", encoding="utf-8")

    settings = SimpleNamespace(
        prompt_dir=prompt_dir,
        max_dialogue_context_chars=500,
    )
    monkeypatch.setattr(bot_engine.config_module, "get_settings", lambda: settings)

    prompt = bot_engine._build_system_prompt(
        settings,
        "provide_technical_support",
        LECTURE_PACKAGE,
        _state(current_topic_id="T1", current_line_status="productive", last_challenge_level=4),
        [{"role": "assistant", "content": "Old question"}],
        "technical_request",
        {
            "recommended_action": "escalate",
            "target_topic_id": "T1",
            "challenge_level": 5,
            "reason_code": "student_requested_harder",
            "secondary_reason_code": None,
            "must_not_repeat": ["do not ask the old definition again"],
            "source_scope_note": "Use lecture-native terminology only.",
        },
    )

    assert "Mode: technical_request" in prompt
    assert "Action: escalate" in prompt
    assert "Likelihood is the plausibility" in prompt


def test_finalize_assistant_message_removes_move_narration():
    message, _ = bot_engine._finalize_assistant_message(
        "The next move is to test transfer. Can you apply likelihood to a fresh case?",
        LECTURE_PACKAGE,
    )
    assert "The next move is" not in message
    assert message == "Can you apply likelihood to a fresh case?"


def test_finalize_assistant_message_rewrites_external_jargon_when_not_in_lecture():
    lecture_package = dict(LECTURE_PACKAGE)
    lecture_package["handout"] = "Evidence appears in Bayes' rule."
    message, changed = bot_engine._finalize_assistant_message(
        "The posterior kernel is prior times likelihood. What does that tell you?",
        lecture_package,
    )
    assert changed is True
    assert "posterior kernel" not in message.lower()
    assert "prior × likelihood before normalization" in message


def test_contains_substantive_content_question_ignores_procedural_questions():
    assert bot_engine._contains_substantive_content_question("Would you like to switch topics?") is False
    assert bot_engine._contains_substantive_content_question("How would measurement error affect reliability?") is True
