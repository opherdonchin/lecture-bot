from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_unified_tutor_prompt_contains_core_anti_loop_rules() -> None:
    text = _read("prompts/generated/tutor_prompt.md")
    required_phrases = [
        "Never narrate your plan.",
        "Forbidden phrasings include:",
        "answer the steering request directly in one short sentence, then return immediately to content",
        "Treat repetition complaints as a real signal",
        "Once the student has shown criterion-level understanding or succeeded on a fresh application, do not ask another low-level check",
        "Choose the move most likely to improve the student's grade per unit time.",
        "If the student asks for harder questions or for questions that get points, do not return to level 1.",
        "Use lecture-native terminology only.",
        "Do not import outside textbook terminology.",
    ]
    for phrase in required_phrases:
        assert phrase in text


def test_unified_tutor_prompt_uses_compact_action_hint_fields() -> None:
    text = _read("prompts/generated/tutor_prompt.md")
    required_phrases = [
        "Mode hint: {tutor_mode}",
        "Current topic focus: {current_topic_id}",
        "Current line status: {current_line_status}",
        "Last challenge level: {last_challenge_level}",
        "Action hint:",
        "- recommended_action: {recommended_action}",
        "- target_topic_id: {target_topic_id}",
        "- challenge_level: {challenge_level}",
        "- reason_code: {reason_code}",
        "- action_must_not_repeat: {action_must_not_repeat}",
    ]
    for phrase in required_phrases:
        assert phrase in text


def test_classifier_prompt_has_compact_routing_guidance() -> None:
    text = _read("prompts/generated/classifier_system_prompt.md")
    required_phrases = [
        "The `state` field is intentionally compact.",
        "`current_topic_id`",
        "`current_line_status`",
        "`last_challenge_level`",
        "`must_not_repeat`",
        "If a short dismissive or deferential reply such as \"whatever\"",
        "If the student says they already understand, that often functions as a pace-or-direction signal",
        "If the message mixes a short content fragment with \"I'm not sure what you're getting at\"",
    ]
    for phrase in required_phrases:
        assert phrase in text


def test_old_non_redirect_prompts_are_not_used_by_runtime_mapping() -> None:
    text = _read("app/bot_engine.py")
    assert '"respond": "tutor_prompt.md"' in text
    assert '"provide_content_support": "tutor_prompt.md"' in text
    assert '"provide_technical_support": "tutor_prompt.md"' in text
    assert '"seek_clarification": "tutor_prompt.md"' in text
    assert '"redirect": "redirect_prompt.md"' in text
