from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("relative_path", "required_phrases"),
    [
        (
            "prompts/generation/provide_technical_support_system_prompt_generator.md",
            [
                "a bounded working-memory synopsis",
                "answer the student's session-steering request directly before deciding whether to ask anything else",
                "when recent context suggests an obvious next natural topic, prefer proposing that topic directly rather than offering a menu",
                "use a menu of topic options mainly when there is no clear natural continuation",
            ],
        ),
        (
            "prompts/generation/classifier_system_prompt_generator.md",
            [
                "a bounded working-memory synopsis such as `student_goal_now`",
                "low-ownership turns such as parroting, vague agreement, authority-based answers",
                "often recommend `provide_content_support` rather than ordinary `respond`",
                "recent_parroting_streak",
                "current_line_status",
            ],
        ),
        (
            "prompts/generation/respond_system_prompt_generator.md",
            [
                "never ask two actual questions in one turn",
                "prefer moving on over squeezing for stronger mastery",
                "use the working-memory synopsis as the primary carried memory of the exchange",
                "`student_goal_now`",
                "`do_not_repeat`",
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
                "never ask two actual questions in one turn",
                "prefer moving on over squeezing for stronger mastery",
                "use the working-memory synopsis as the primary carried memory of the exchange",
                "`student_goal_now`",
                "`do_not_repeat`",
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
                "a compact working-memory synopsis such as `student_goal_now`",
                "Use the working-memory synopsis when present",
                "recent_parroting_streak",
                "current_line_status",
                "Low-ownership turns such as parroting, vague agreement, authority-based answers",
                "often recommend `provide_content_support` rather than ordinary `respond`",
            ],
        ),
        (
            "prompts/generated/provide_technical_support_prompt.md",
            [
                "Student goal now: {student_goal_now}",
                "Answer the student's session-steering question directly before you decide whether to ask anything else.",
                "One thing at a time. Never ask two questions in one turn, even if they are short or closely related.",
                "When recent context suggests an obvious next natural topic, prefer proposing that topic directly rather than offering a menu.",
                "Use a menu of topic options mainly when there is no clear natural continuation",
            ],
        ),
        (
            "prompts/generated/respond_prompt.md",
            [
                "Student goal now: {student_goal_now}",
                "Use the working-memory synopsis as your primary carried memory of the exchange.",
                "Do not repeat: {do_not_repeat}",
                "Current topic mastery estimate: {current_topic_mastery}",
                "Progress focus: {progress_focus}",
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
                "Student goal now: {student_goal_now}",
                "Use the working-memory synopsis as your primary carried memory of the exchange.",
                "Do not repeat: {do_not_repeat}",
                "Current topic mastery estimate: {current_topic_mastery}",
                "Progress focus: {progress_focus}",
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
