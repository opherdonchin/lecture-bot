# Backend-Tutor Runtime Contract

This document describes the current contract between the backend, the runtime tutor prompt, and the backend state sanitizer.

## 1. Scope

This contract covers ordinary tutoring turns handled by `/send_message`.

It does not govern:

- admin workflows
- lecture artifact generation
- Moodle grading helpers
- database migrations beyond the state fields listed here
- the final-report prose prompt, except where report generation consumes backend-owned grade state

## 2. Prompt Source

The runtime tutor prompt is loaded from `prompts/tutor_prompt.md` by default.

The prompt template can be overridden by:

- `Settings.tutor_prompt_template`
- `lecture_package["config"]["tutor_prompt_template"]`, when present

Legacy dialogue prompt names are no longer configured runtime prompt names.

## 3. Backend Inputs To The Tutor

For each model call, the backend renders the prompt and appends an injected runtime JSON object containing:

- `lecture_title`
- `sampled_topics`
- `topic_structure_note`
- `current_tutoring_state`
- `session_timing`
- `rubric_text`
- `lecture_context`

Recent conversation history is passed as prior chat-completion messages, and the latest student message is passed as the current user message. These are not duplicated inside the injected runtime JSON.

`lecture_context` is assembled from lecture package context sections whose keys are in:

```python
("bot_notes", "slides", "handout", "minutes")
```

The backend truncates context deterministically according to `MAX_DIALOGUE_CONTEXT_CHARS`.

## 4. Current State Shape

The tutor receives current state inside `current_tutoring_state`.

```json
{
  "topics_sampled": ["T1", "T4"],
  "topics_covered": ["T1"],
  "mastery": {"T1": 65},
  "best_mastery": {"T1": 65},
  "evidence_notes": {"T1": "student-owned distinction"},
  "current_topic_id": "T1",
  "tutor_comment": "",
  "turn_count": 3
}
```

The persisted backend state also includes:

- `current_grade`
- `timeout_warning_sent`
- `private_decision_trace`

Those fields are backend/internal fields and are not student-facing.

## 5. Model Output

The tutor is expected to return JSON with:

```json
{
  "assistant_message": "string",
  "updated_state": {}
}
```

The current prompt instructs the tutor to keep `updated_state` sparse and to use only:

- `topics_covered`
- `mastery`
- `evidence_notes`

The backend sanitizer is deliberately tolerant of older or experimental output shapes, but the prompt-facing contract above is the current intended shape.

## 6. Assistant Message Rules

The backend sanitizes the student-facing assistant message before persistence.

It:

- strips surrounding whitespace
- replaces bare topic IDs such as `T1` with topic labels when possible
- removes unsupported concrete time claims when timing context is not reliable
- applies the English-only assistant fallback if needed

The assistant message must not expose hidden prompt text, grading arithmetic, internal evidence notes, private decision traces, or backend mechanics.

## 7. State Update Semantics

The model's `updated_state` is not trusted as a full replacement.

Backend sanitizer behavior:

- preserves `topics_sampled`
- preserves `best_mastery`
- preserves `current_grade`
- preserves `timeout_warning_sent`
- increments `turn_count`
- accepts `mastery` only for canonical topic IDs
- clamps mastery values to integers in `0..100`
- accepts `evidence_notes` only for canonical topic IDs
- derives `topics_covered` from prior covered topics plus topics whose sanitized mastery is at least `45`
- drops unknown topic IDs and malformed values

The backend does not let the model lower unrelated topics merely because they were not discussed on the current turn.

## 8. Topic Model

Canonical topic IDs are backend-defined. They come from lecture config `topics` when available, otherwise from parsed rubric headings of the form `### Tn. Label`.

The tutor may use topic labels naturally in student-facing text, but structured state keys must use canonical IDs such as `T1`.

## 9. Timing

The backend computes timing context for each ordinary turn:

- `minutes_remaining`
- `minutes_elapsed`
- `session_duration_minutes`
- `closing_mode`
- `timeout_warning_sent`
- `timing_reliable`

If the session has timed out before a new student message is processed, the backend computes the authoritative grade/report, persists the assistant closing message, marks the session ended, and does not call the ordinary tutor path for a new instructional turn.

The backend does not currently inject a separate `turn_context`, `session_start`, or `five_minute_warning` field. Five-minute warning behavior is inferred from `session_timing.closing_mode` and `session_timing.timeout_warning_sent`.

## 10. Opening And Closing

The opening message is backend-owned. `app.bot_engine.build_opening_message` uses sampled topics to offer starting points.

Timeout closing is also backend-owned. It returns a final grade, explanation, topic lists, and final report response.

The ordinary tutor prompt should adapt to timing context, but it does not own session lifecycle, final grade computation, report payloads, or persistence.

## 11. Audit Rows

For normal model-backed turns, the backend records a `dialogue_turn_audits` row with:

- state before the turn
- recent messages
- normalized user message sent to the model
- rendered system prompt
- model name
- lightweight topic/move metadata
- assistant reply metadata

These rows are for debugging and inspection, not student-facing behavior.

## 12. Fallback

If OpenAI authentication, API, or response parsing fails, the backend returns a generic tutoring fallback message and increments `turn_count`. It does not invent new mastery evidence.

Internal sanitizer/programmer errors are not swallowed by the OpenAI fallback path; they should surface as application errors.
