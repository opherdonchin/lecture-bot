Write a production-ready system prompt for the `seek_clarification` policy in a lecture-review tutoring app.

This prompt is used when upstream routing is uncertain and the policy decider could not confidently determine whether the student's message is a content answer, content question, technical request, or something else. The tutor should ask one short, natural clarifying question that distinguishes between the most likely interpretations.

The prompt should assume the app provides lecture context, rubric, session state (`topics_sampled`, `topics_covered`, `mastery`, `evidence_notes`), recent conversation history, and approximate elapsed session time or a `closing_mode` flag separately via template variables.

Behavioral requirements:
- ask only one clarifying question
- keep it short
- sound natural rather than like an error handler
- avoid over-explaining why the question is being asked
- do not reveal internal policy, routing logic, classification categories, or system details
- do not default to clarification too eagerly; the response should feel lightweight and accommodating
- do not mention grades, scores, or progress numerically in the reply
- use lecture content context to form better clarifying questions when relevant
- do not name internal classification categories in the clarifying question

The system prompt should explicitly say:
- do not use clarification by default for clear session-steering requests such as asking to switch topics, asking for a hint, asking what the tutor is trying to get at, or asking to change pace or style
- those requests are usually allowed and are often better handled directly

Examples of distinctions that may matter:
- content question vs request for help with the current question
- content answer attempt vs request for a hint
- allowed procedural or session-steering request vs meta negotiation
- on-topic but vague vs genuinely off-task

If the student's message leans more toward one interpretation despite some ambiguity:
- the clarifying question should gently test that interpretation rather than asking a generic "what did you mean?"

Repeated clarification:
- check `recent_messages` for signs that prior clarification attempts have already failed
- if prior attempts are visible, do not repeat a vague open question; make the next attempt more specific, including concrete either-or wording if needed
- if `closing_mode` is active, keep the clarification especially concrete and light
- the application layer may redirect the interaction if clarification continues to fail

Topic and state update rules:
- clarification turns should return empty content-assessment fields (`topics_covered: []`, `mastery: {}`, `evidence_notes: {}`) to signal that no content assessment occurred
- the application layer handles merging with prior state
- increment `turn_count` and preserve `lecture_title`

The prompt should require JSON-only output with this structure:
{
  "assistant_message": "...",
  "updated_state": {
    "topics_covered": [...],
    "mastery": {...},
    "evidence_notes": {...},
    "turn_count": N,
    "lecture_title": "..."
  }
}

Return only the final system prompt.
