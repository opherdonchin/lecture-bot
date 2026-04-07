# Error Handling Policy

This document defines the error-handling approach for lecture-bot.

---

## Guiding principles

- User-facing behavior should feel coherent and intentional.
- Internal bugs must not silently masquerade as normal tutoring behavior.
- Fallback is allowed only where a degraded experience is preferable to a hard failure.
- Logs must contain enough context to diagnose any failure without re-running.
- Do not add defensive checks for impossible or already-validated conditions.

---

## Error classes

### 1. User / input errors

**Examples:** missing required field, invalid session_id format, empty message body.

| Dimension | Policy |
|---|---|
| HTTP status | 422 (Pydantic validation) or 400 |
| User experience | Clear error message returned in response body |
| Fallback | Not applicable |
| State mutation | None |
| Logging | Not logged (expected client-side error) |

---

### 2. Missing resource errors

**Examples:** `session_id` not found in DB, `lecture_id` not found on disk.

| Dimension | Policy |
|---|---|
| HTTP status | 404 |
| User experience | "Session not found" / "Lecture not found" |
| Fallback | Not applicable |
| State mutation | None |
| Logging | Not logged (expected operational condition) |

---

### 3. Session-lifecycle errors

**Examples:** message sent to an already-ended session, session timed out.

| Dimension | Policy |
|---|---|
| HTTP status | 400 |
| User experience | "Session has ended" / "Session has timed out" |
| Fallback | Not applicable — client must start a new session |
| State mutation | Timeout sets `ended_at` before raising |
| Logging | Not logged |

---

### 4. OpenAI authentication / configuration errors

**Examples:** missing API key, invalid API key, account suspended.

| Dimension | Policy |
|---|---|
| HTTP status | 200 (dialogue fallback) or 200 (grade returns 0) |
| User experience | Dialogue: generic tutoring fallback message. Grade/report: fallback text. |
| Fallback | Allowed — session continues in degraded mode |
| State mutation | Dialogue: turn_count incremented in fallback state. Grade: no grade update. |
| Logging | `log.exception(...)` with message identifying the call site |
| Notes | Caught as `openai.AuthenticationError` for differentiated logging |

---

### 5. Transient vendor / network errors

**Examples:** connection timeout, rate limit, temporary server error from OpenAI.

| Dimension | Policy |
|---|---|
| HTTP status | 200 (with fallback) |
| User experience | Same as auth errors — degraded fallback |
| Fallback | Allowed |
| State mutation | Same as auth errors |
| Logging | `log.exception(...)` — distinguishable from auth error in log output |
| Notes | `max_retries=0` on all OpenAI clients — no retry backoff |

---

### 6. Malformed model output

**Examples:** model returns invalid JSON, missing required key, wrong type.

| Dimension | Policy |
|---|---|
| HTTP status | 200 (with fallback) |
| User experience | Dialogue: generic tutoring fallback. Grade: 0 or prior grade retained. |
| Fallback | Allowed |
| State mutation | Dialogue: turn_count incremented. Grade: no update on empty parse. |
| Logging | `log.exception(...)` |
| Notes | Validation/sanitisation is the primary defence; fallback only for complete parse failure |

---

### 7. Internal programmer errors / invariant violations

**Examples:** missing session state row, unexpected None where impossible, logic bugs.

| Dimension | Policy |
|---|---|
| HTTP status | 500 (unhandled, propagated to FastAPI default handler) |
| User experience | Generic 500 response — not masked |
| Fallback | Not allowed — these indicate bugs, not expected runtime failures |
| State mutation | None (transaction not committed) |
| Logging | Python default traceback via FastAPI |
| Notes | Do not catch `Exception` broadly to mask these. The `ValueError` raised by `session_manager.load_state` when state is missing is an invariant violation and should propagate as 500. |

---

## Implementation notes

### OpenAI call sites (`bot_engine.py`)

Three call sites exist: `generate_reply`, `generate_topic_scores`, `generate_report`.

Each wraps the OpenAI call with three structured catches:

```python
except openai_.AuthenticationError:
    _log.exception("<function> failed: authentication error")
    <fallback>
except openai_.APIError:
    # Rate limits, timeouts, connection errors from the OpenAI API.
    _log.exception("<function> failed: OpenAI API error")
    <fallback>
except Exception:
    # Catches malformed JSON, missing model output keys, and other
    # unexpected response-parsing failures.
    _log.exception("<function> failed")
    <fallback>
```

`openai_.AuthenticationError` is caught first for a clearly labelled log entry.
`openai_.APIError` covers remaining vendor errors (rate limits, timeouts, connection issues).
`except Exception` is retained and justified for the API call and response-parsing lines only —
it catches malformed model output (`JSONDecodeError`, unexpected key structure, etc.).

**Crucially, our own code is placed outside the try block.**
In `generate_reply`, `sanitize_state_update(...)` is called after the except clauses.
In `generate_topic_scores`, the validation/deduplication loop is after the except clauses.
Bugs in that code propagate as 500, not silently masked as apparent tutoring fallback behaviour.

### Grade fallback

When `generate_topic_scores` returns empty scores (any failure), `compute_weighted_grade([])` returns 0.
If 0 ≤ stored_grade, the new candidate is not accepted and the stored grade is unchanged.
The user sees their previously accepted grade — correct behaviour.

### Dialogue fallback

`_FALLBACK_DIALOGUE_MESSAGE` is a neutral tutoring prompt that invites the
student to continue. It is deliberate and appropriate as a degraded state.
The turn_count is still incremented in the fallback state.
