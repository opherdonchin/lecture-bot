# Decisions Made

This file records implementation decisions that deviate from or exercise judgement within the stated plan.  
All entries follow the format: **what was decided**, **why**, **alternatives considered**.

---

## UI

### Textarea replaces single-line input (not specified in plan)

**What:** Replaced `<input type="text" id="messageInput">` with `<textarea id="messageInput" rows="3">`.  
Added Ctrl+Enter keyboard shortcut to submit without moving hands off keyboard.  
Set `resize: vertical` — lets users expand the box but not break the horizontal layout.

**Why:** The original input scrolled text horizontally, making it hard to review what you typed. A textarea autowraps and is naturally scrollable vertically. This is a UX necessity, not speculative improvement.

**Alternatives:** Could also have added an Enter-to-send shortcut (like a chat app), but Enter in a textarea is the natural newline key. Ctrl+Enter is the established convention for "submit a multiline form".

---

### Grade display rendered as structured DOM elements (not specified in plan)

**What:** Replaced the `lines.join(" | ")` approach with a dedicated `appendGradeMessage(data)` function that renders the grade as a card with a bold header, explanation paragraph, and missing-topics line. Similarly, added `appendReportMessage(data)` that splits the report text on double newlines into `<p>` elements and shows the grade in a header.

**Why:** The pipe-separated single-line format was genuinely unreadable. Structuring it as distinct DOM elements makes the grade scannable and the report paragraph-formatted. No backend changes required.

**Alternatives:** Could have passed an HTML string, but building DOM nodes directly is safer (no XSS risk) and easier to style.

---

## Phase 1: Authoritative payload helper

### `_get_authoritative_grading_payload` searches both `grade` and `report` event types

**What:** The shared helper (`_get_authoritative_grading_payload` in `main.py`) queries both `event_type == "grade"` and `event_type == "report"` events. The previous `/get_grade` fallback searched only `"grade"` events, while `/generate_report` searched both. The inconsistency meant that a high grade set via `/generate_report` would be invisible to a subsequent `/get_grade` call's fallback.

**Why:** The authoritative payload is whichever accepted event carries the best grade, regardless of which endpoint produced it. Searching both event types is required to fulfil this correctly.

**Alternatives:** Could have stored the authoritative payload in a separate table cell on `SessionModel`. Decided against it — querying the event log is already the established pattern and a separate field would duplicate data.

### Most-recent accepted event is used (not a joint max-grade scan)

**What:** The helper returns the most-recently inserted event where `accepted_as_current == True`, rather than scanning all events to find the one with the highest grade.

**Why:** The monotone-grade rule already ensures that any accepted event has a grade ≥ all prior accepted events. The most-recent accepted event is therefore always the one with the highest accepted grade. A separate max scan would be logically redundant.

**Alternatives:** Could have stored the best grade on `SessionModel` and only fetched the payload from the event log. Decided not to — the payload is already in the event log, the query is simple, and adding a separate pointer field would add complexity for no benefit.

---

## Phase 2: Topic sampling

### `sampled_topic_count` wired via `config_module.get_settings()` inside `session_manager`

**What:** `session_manager.py` now imports `app.config` and calls `config_module.get_settings().sampled_topic_count` inside `create_session`.

**Why:** The alternative was to add a `count` parameter to `create_session` and have the callers (in `main.py`) pass it. Both approaches are valid, but importing settings directly is simpler and keeps the session creation fully self-contained. Session creation is already responsible for all other initialisation decisions.

**Alternatives:** Adding `count` to `create_session`'s signature would make the function easier to test in isolation (pass a specific count), but no test currently exercises topic sampling count directly. Decision reversed if tests targeting count are needed.

---

## Phase 2: Grading validation

### Duplicate topic IDs: keep the highest score

**What:** When the model returns multiple entries for the same topic ID, the one with the highest score is retained. This is implemented via a `seen: dict` traversed in order.

**Why:** The most charitable interpretation of the student's responses is preferred. If the model attempted to score a topic multiple times (e.g., once provisionally and once after more context), taking the maximum prevents under-reporting student performance due to a model inconsistency.

**Alternatives:** Could take the first occurrence, the last, or the average. First/last are arbitrary. Average would smooth out inconsistencies but could hide genuine high performance. Max is the most student-beneficial choice and aligns with the "best demonstrated grade" policy.

---

## Phase 3: Error handling

### `import openai as openai_` moved to module level

**What:** Previously each OpenAI call site did `import openai as openai_` inside the `try` block. Moved to the module-level import section.

**Why:** There is no reason to defer the import — it costs nothing at import time. Moving it to module level makes the code cleaner and allows referencing `openai_.AuthenticationError` in except clauses outside of the try block.

**Alternatives:** Keeping it inside the function would also allow catching `openai_.AuthenticationError`, but only within the try block — less readable. Module-level import is conventional.

### `openai_.AuthenticationError` named as first except clause

**What:** Each OpenAI call site now catches `openai_.AuthenticationError` before the broad `except Exception`. Both log and fall back.

**Why:** Auth failures are operationally distinct from transient failures (rate limits, network issues). They almost always indicate a configuration problem rather than a temporary condition. Naming them explicitly makes the log output immediately actionable ("OpenAI authentication error" vs. a bare AttributeError trace).

**Alternatives:** Could have added separate catches for `RateLimitError`, `APITimeoutError`, etc. Decided against it — each additional clause would log and fall back identically. The differentiation value doesn't justify the verbosity. `AuthenticationError` is the one that most benefits from a distinct, visible label.

### One fallback point per function (refactored from duplicated fallback in each except)

**What:** The fallback return in `generate_reply` is now after both except clauses, not duplicated inside each. If either exception fires, execution falls through to the same fallback code.

**Why:** Eliminates duplication. The fallback is identical for both error types — there is no reason to have different fallback behaviour for auth vs. transient failures.

---

## Phase 4: Tests

### Tests mocked to avoid real OpenAI calls

**What:** Several tests (`test_turn_count_persists`, `test_messages_persisted`, `test_start_session_topics_sampled_immutable_after_creation`, `test_get_grade_returns_grade_structure`, `test_generate_report_returns_report_structure`, `test_generate_report_uses_authoritative_grade`, `test_generate_report_grade_monotone_nondecreasing`) were calling `/send_message`, `/get_grade`, or `/generate_report` without mocking OpenAI. With a working API key these tests become slow (5–30s each).

**Why:** Unit and integration tests should not rely on external services. Each of these tests is asserting a structural property (turn_count increments, grades are monotone, etc.) that is fully deterministic given mocked inputs. Making real API calls for these assertions is unnecessary, fragile, and slow.

**Alternatives:** Leave the tests as-is and document the slow suite. Rejected — slow tests impede development feedback loops and will silently break if the API key expires.

### `_mock_openai_dialogue` and `_mock_openai_report` helpers added to tests

**What:** Added two local helpers to the test files. `_mock_openai_dialogue` returns a valid JSON response that satisfies the dialogue parsing. `_mock_openai_report` returns a valid report JSON response.

**Why:** DRY within the test files. Multiple tests need the same mock setup.

### `test_sample_session_topics_different_seeds` replaced with variability test

**What:** The previous test used `assert result1 != result2 or True` which is always True.

**Why:** The `or True` made the assertion trivially vacuous. The replacement tests 20 fixed seeds and asserts the resulting sample set has cardinality > 1, which is a meaningful probabilistic invariant while remaining fully deterministic.

### `test_get_grade_uses_report_event_payload_when_authoritative` added

**What:** New test that verifies `_get_authoritative_grading_payload` finds a prior accepted payload from a `report` event when `/get_grade` is called subsequently with a lower candidate.

**Why:** This was the specific hole in the previous `/get_grade` logic (it searched only `grade` events). The test directly exercises the bug that was fixed.
