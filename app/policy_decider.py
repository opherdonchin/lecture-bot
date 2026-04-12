from __future__ import annotations

import re as re_

from app.schema import ClassifierResult, PolicyDecision


# Hard backstop patterns — blatant attempts to break the pedagogical frame.
# These are coarse safety-nets aimed at obvious cases only.
# Nuanced routing is handled by the classifier.
HARD_BACKSTOP_PATTERNS: list[tuple[re_.Pattern, str]] = [
    # Asks for the correct answer directly
    (re_.compile(r"just (?:give|tell|say) me (?:the )?(?:correct |right )?answer", re_.IGNORECASE), "asks_for_answer"),
    (re_.compile(r"what(?:'s| is) the (?:correct |right )?answer", re_.IGNORECASE), "asks_for_answer"),
    (re_.compile(r"give me the (?:correct |right )?answer", re_.IGNORECASE), "asks_for_answer"),
    (re_.compile(r"tell me the (?:correct |right )?answer", re_.IGNORECASE), "asks_for_answer"),
    # Asks to reveal hidden internals
    (re_.compile(r"(?:show|reveal|print|display|give|tell|share|expose) (?:me |us )?(?:your |the )?(?:hidden |system )?prompt", re_.IGNORECASE), "asks_for_internals"),
    (re_.compile(r"what(?:'s| is) (?:in )?your (?:system )?(?:prompt|instructions)", re_.IGNORECASE), "asks_for_internals"),
    (re_.compile(r"(?:show|reveal|give|tell) (?:me )?(?:the )?(?:hidden )?rubric", re_.IGNORECASE), "asks_for_internals"),
    (re_.compile(r"what(?:'s| is) (?:in )?(?:the |your )?(?:hidden )?rubric", re_.IGNORECASE), "asks_for_internals"),
    # Asks how to game/exploit the system
    (re_.compile(r"how (?:to|do i|can i|could i) (?:trick|game|cheat|exploit|hack|fool|beat|bypass) (?:the )?(?:system|bot|grader|ai|tutor)", re_.IGNORECASE), "gaming"),
    (re_.compile(r"\b(?:trick|cheat|exploit|hack|fool|bypass) (?:the )?(?:system|bot|grader|ai|tutor)", re_.IGNORECASE), "gaming"),
    # Requests for forbidden interaction formats
    (re_.compile(r"(?:give|do|use|switch to|make it|convert to) multiple.?choice", re_.IGNORECASE), "format_change"),
    (re_.compile(r"(?:give|do|use|switch to|make it|convert to) fill.?in.?the.?blank", re_.IGNORECASE), "format_change"),
    (re_.compile(r"(?:give|do|use|switch to) yes.?(?:or |/)?no (?:questions?|format)", re_.IGNORECASE), "format_change"),
    # Asks bot to stop asking questions and just grade
    (re_.compile(r"stop asking (?:me |content )?questions?.*(?:grade|score|evaluate)", re_.IGNORECASE), "stop_and_grade"),
    (re_.compile(r"(?:stop|quit|no more) (?:the )?(?:questions?|asking).*(?:grade|score|evaluate|mark) (?:me|my)", re_.IGNORECASE), "stop_and_grade"),
]


class PolicyDecider:
    """Decides the effective response policy from a classifier result and session state."""

    def __init__(
        self,
        hard_backstops: list[tuple[re_.Pattern, str]],
        top1_min: float = 0.50,
        top2_trigger: float = 0.30,
        ambiguity_gap_max: float = 0.20,
        clarification_redirect_threshold: int = 3,
    ) -> None:
        self._backstops = hard_backstops
        self.top1_min = top1_min
        self.top2_trigger = top2_trigger
        self.ambiguity_gap_max = ambiguity_gap_max
        self.clarification_redirect_threshold = clarification_redirect_threshold

    def _check_backstops(self, text: str, state: dict) -> str | None:
        """Return the backstop name if any pattern matches, else None."""
        for pattern, name in self._backstops:
            if pattern.search(text):
                return name
        if state.get("consecutive_redirects", 0) >= 3:
            return "repeated_redirection"
        return None

    def _ambiguity_summary(self, classification: ClassifierResult) -> str | None:
        """Return a summary string if the classification is too ambiguous, else None."""
        probs = classification.class_probabilities
        sorted_probs = sorted(probs.values(), reverse=True)
        top1 = sorted_probs[0] if sorted_probs else 0.0
        top2 = sorted_probs[1] if len(sorted_probs) > 1 else 0.0
        gap = top1 - top2
        if top1 < self.top1_min:
            return f"top1={top1:.2f} below threshold {self.top1_min}"
        if top2 >= self.top2_trigger and gap < self.ambiguity_gap_max:
            return f"top2={top2:.2f}, gap={gap:.2f}: too close to distinguish"
        return None

    def decide_policy(
        self,
        message_text: str,
        classification: ClassifierResult,
        state: dict,
    ) -> PolicyDecision:
        matched = self._check_backstops(message_text, state)
        if matched:
            return PolicyDecision(
                effective_policy="redirect",
                used_classifier_recommendation=False,
                override_reason="hard_backstop",
                matched_backstop=matched,
            )
        if state.get("consecutive_clarifications", 0) >= self.clarification_redirect_threshold:
            return PolicyDecision(
                effective_policy="redirect",
                used_classifier_recommendation=False,
                override_reason="clarification_limit_reached",
            )
        ambig = self._ambiguity_summary(classification)
        if ambig:
            return PolicyDecision(
                effective_policy="seek_clarification",
                used_classifier_recommendation=False,
                override_reason="ambiguous_classification",
                ambiguity_summary=ambig,
            )
        return PolicyDecision(
            effective_policy=classification.recommended_policy,
            used_classifier_recommendation=True,
        )
