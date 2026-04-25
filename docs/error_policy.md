# Error Handling Policy

This document describes the current error-handling approach for lecture-bot.

## 1. Principles

- Expected user/client mistakes should produce clear 4xx responses.
- Missing runtime resources should produce clear 404 responses.
- OpenAI failures may fall back when a degraded user experience is better than ending the session.
- Backend invariants and programmer errors should not be disguised as normal tutoring behavior.
- Logs should identify the failing OpenAI call site.
- Fallback paths should not invent assessment evidence.

## 2. User And Input Errors

Examples:

- missing required request fields
- empty messages
- invalid Pydantic request shapes
- sending a message to an ended session

Policy:

- HTTP status: `422` from Pydantic or explicit `400`
- no model call
- no speculative state update
- no special logging for ordinary client mistakes

## 3. Missing Resources

Examples:

- unknown `session_id`
- unknown `lecture_id`
- missing lecture package files

Policy:

- HTTP status: `404`
- clear response detail such as `"Session not found"` or lecture-loader error text
- no fallback model behavior

## 4. Language Policy

Student messages are checked before the tutor model is called.

If the text is rejected as non-English:

- the original user message is persisted
- the English-only assistant refusal is persisted
- current state is preserved
- no tutor model call is made
- the session remains active

Assistant messages returned from OpenAI are also passed through English-only fallback handling before being shown.

## 5. Timeout Policy

When `/send_message` detects that a session has exceeded `SESSION_TIMEOUT_MINUTES`:

- the backend computes the authoritative grade snapshot from current state
- the backend records a grade event
- the backend generates or falls back to a final report
- the backend persists a closing assistant message
- `ended_at` is set
- the response includes `session_active=false`, final grade fields, and final report data

The ordinary tutor model is not used to decide timeout lifecycle behavior.

## 6. OpenAI Dialogue Failures

`app.bot_engine.generate_reply` catches:

- `openai_.AuthenticationError`
- `openai_.APIError`
- response parsing/shape errors inside the API/parsing block

Policy:

- HTTP status remains `200`
- user sees `_FALLBACK_DIALOGUE_MESSAGE`
- prior assessment evidence is preserved
- `turn_count` is incremented
- no new mastery/evidence is invented
- failure is logged with `log.exception(...)`

The sanitizer runs outside the OpenAI try/except block. Bugs in sanitizer logic should surface instead of being masked as model fallback.

## 7. Current Grade Failures

Current-grade computation is backend-owned.

The `/get_grade` endpoint:

- loads state
- updates `best_mastery` from sanitized `mastery`
- computes weighted grade in Python
- records an accepted grade event
- returns timing fields with the grade response

It does not call `generate_topic_scores` in the current endpoint path.

Expected missing resources still produce 404. Internal state/database invariants should surface as application errors.

## 8. Report Failures

`/generate_report` uses the authoritative backend grade snapshot, then calls the OpenAI report writer for prose.

If OpenAI auth/API/parsing fails in `generate_report`:

- the authoritative backend grade is preserved
- report JSON is still returned
- report text falls back to local deterministic prose
- the failure is logged

The report model does not own the numeric grade.

## 9. Legacy Grading Helper

`app.bot_engine.generate_topic_scores` still exists as a helper, but current `/get_grade` and `/generate_report` behavior no longer depends on it.

If that helper is used by future code, it should be treated as an OpenAI-backed assessor with the same fallback expectations:

- OpenAI failures produce empty topic scores
- validation runs outside the API/parsing fallback where possible
- Python remains responsible for final weighted-grade arithmetic

## 10. Internal Errors

Examples:

- missing `session_state` row for an existing session
- impossible database state
- programmer errors in sanitizer or grade computation

Policy:

- do not broadly catch and hide these as successful tutoring
- let FastAPI return an application error
- fix the invariant or bug directly
