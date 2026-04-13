from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("relative_path", "required_phrases"),
    [
        (
            "prompts/generation/classifier_system_prompt_generator.md",
            [
                "low-ownership turns such as parroting, vague agreement, authority-based answers",
                "often recommend `provide_content_support` rather than ordinary `respond`",
                "recent_parroting_streak",
                "current_line_status",
            ],
        ),
        (
            "prompts/generation/respond_system_prompt_generator.md",
            [
                "treat restoration of student ownership as a legitimate tutoring goal",
                "if the student has already received a substantive explanation on this point",
                "in one turn, usually do at most one informative move",
                'do not say "Exactly" or equivalent unless the student really captured the key point',
                "current_line_status` should be one of `productive`, `stalled`, `over_scaffolded`, or `unclear`",
            ],
        ),
        (
            "prompts/generation/provide_content_support_system_prompt_generator.md",
            [
                "treat restoration of student ownership as a legitimate tutoring goal",
                "repeated low-agency turns are evidence that the tutor should stop rescuing the line with more content",
                "in one turn, usually do at most one informative move",
                'do not say "Exactly" or equivalent unless the student really captured the key point',
                "current_line_status` should be one of `productive`, `stalled`, `over_scaffolded`, or `unclear`",
            ],
        ),
        (
            "prompts/generated/classifier_system_prompt.md",
            [
                "recent_parroting_streak",
                "current_line_status",
                "Low-ownership turns such as parroting, vague agreement, authority-based answers",
                "often recommend `provide_content_support` rather than ordinary `respond`",
            ],
        ),
        (
            "prompts/generated/respond_prompt.md",
            [
                "## Ownership restoration",
                "If the student has already received a substantive explanation on this point",
                "In one turn, usually do at most one informative move",
                "Do not say “Exactly” or equivalent unless the student's answer genuinely captures the key point.",
                "Current line status: {current_line_status}",
            ],
        ),
        (
            "prompts/generated/provide_content_support_prompt.md",
            [
                "## Ownership restoration",
                "If the student has already received a substantive explanation on this point",
                "In one turn, usually do at most one informative move",
                "Do not say “Exactly” or equivalent unless the student's answer genuinely captures the key point.",
                "Current line status: {current_line_status}",
            ],
        ),
    ],
)
def test_prompt_guardrails_present(relative_path: str, required_phrases: list[str]) -> None:
    text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    for phrase in required_phrases:
        assert phrase in text
