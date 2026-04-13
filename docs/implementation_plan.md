# LLM Integration Plan v2

## 1. Goal

Replace the current stub behavior with real OpenAI-backed behavior for:

* dialogue turns in `/send_message`
* grading in `/get_grade`
* final report generation in `/generate_report`

without changing:

* endpoint shapes
* frontend structure
* session lifecycle
* overall database schema
* RPC-style flow

Also fold in the missing timeout check while touching `main.py`, since the spec already requires it and `/send_message` is the endpoint being changed.

---

## 2. Core corrections to v1

This version makes the following changes explicit:

1. `topics_sampled` is created once at `start_session` by backend code and is immutable thereafter.
2. Topic grading is done per touched topic on a 0-100 scale; Python converts those topic scores into the student-facing weighted grade.
3. The weighted grade is computed in Python, never trusted from the model.
4. The stored `current_grade` means **best demonstrated grade so far**, not merely the latest estimate.
5. Explanations and reports must be based on the grading payload associated with the accepted best grade, not on a lower later attempt.
6. `/generate_report` uses one internally consistent grading result within the request.
7. Topic identifiers are canonical backend-defined IDs, not model-invented strings.
8. Context size is bounded deterministically.
9. OpenAI API failures are handled explicitly, not only malformed JSON.
10. The top-level weighted-best-5 grade formula stays fixed at `55 / 25 / 13 / 4 / 3`.
11. Within-topic mastery semantics become faster early and slower late, as described in `docs/policy_routing_spec.md` and `docs/session_calibration.md`.
12. Dialogue behavior is guided by heuristics and a move inventory rather than a rigid move ladder.

---

## 3. File-level plan

Primary files to edit:

* `app/main.py`
* `app/bot_engine.py`
* `app/session_manager.py`
* `app/config.py`
* `app/schema.py`

Tests to update/add:

* `tests/test_send_message.py`
* `tests/test_control_actions.py`
* `tests/test_start_session.py`
* optional: `tests/test_bot_engine.py`

### Design choice about schemas

Stop adding new request/response models inline in `main.py`.
Move the endpoint schemas that already exist in `main.py` into `app/schema.py`, and add the control-action schemas there as well.

This is a small cleanup, not a redesign.

---

## 4. Bot engine contract

`app/bot_engine.py` should expose these public functions:

```python
def build_opening_message(
    *,
    lecture_package: dict,
    sampled_topic_ids: list[str],
) -> str: ...

def generate_reply(
    *,
    lecture_package: dict,
    recent_messages: list[dict],
    state: dict,
    user_message: str,
    session_elapsed_minutes: float,
    closing_mode: bool,
) -> tuple[str, dict]: ...

def generate_topic_scores(
    *,
    lecture_package: dict,
    messages: list[dict],
    state: dict,
) -> dict: ...

def generate_report(
    *,
    lecture_package: dict,
    messages: list[dict],
    state: dict,
    grading_result: dict,
    session_id: str,
    student_id: str,
    timestamp_iso: str,
) -> dict: ...
```

### Internal pure helpers in `bot_engine.py`

```python
def parse_rubric_topics(rubric_markdown: str) -> list[dict]: ...
def sample_session_topics(topic_defs: list[dict], session_id: str, count: int = 5) -> list[str]: ...
def build_dialogue_context(lecture_package: dict, max_chars: int) -> str: ...
def compute_weighted_grade(topic_scores: list[dict]) -> int: ...
def sanitize_state_update(old_state: dict, llm_state: dict, allowed_topic_ids: set[str]) -> dict: ...
def serialize_messages(rows) -> list[dict]: ...
def is_closing_mode(session_elapsed_minutes: float, threshold_minutes: int = 25) -> bool: ...
```

Grading math belongs in `bot_engine.py` as a pure helper, because it is part of the bot contract but should remain testable and database-free.

---

## 5. Canonical topic representation

### 5.1 Topic IDs

Canonical topic IDs come from backend parsing of the rubric, using the rubric headings already present in the form `T1`, `T2`, etc.

Each parsed topic definition should include at least:

```python
{
    "topic_id": "T1",
    "label": "Reality-Data-Model distinction",
    "importance": "core",
}
```

The model must always refer to topics by `topic_id` only.
The backend may separately keep a `topic_id -> label` mapping for explanations or reports.

### 5.2 Session topic sampling

At `start_session`:

1. parse the rubric into canonical topics
2. sample a fixed subset of session focus topics in backend code
3. write those IDs into `state["topics_sampled"]`

Sampling should be deterministic per session, for example by seeding from `session_id`, so behavior is reproducible in tests.

### 5.3 Meaning of `topics_sampled`

`topics_sampled` means "preferred focus topics for this session," not "the only topics that can ever appear."

The dialogue engine should preferentially guide toward these topics.
Grading should score the topics actually touched, not pretend to score untouched topics.

### 5.4 Immutability rule

`topics_sampled` is backend-owned and immutable after session creation.
If the dialogue model returns a modified `topics_sampled`, the backend ignores it.

---

## 6. Session state contract

State shape:

```json
{
  "topics_sampled": ["T1", "T4", "T7", "T8", "T10"],
  "topics_covered": ["T1", "T4"],
  "mastery": {
    "T1": 60,
    "T4": 35
  },
  "evidence_notes": {
    "T1": "stated criterion but not yet verified with transfer",
    "T4": "vague label only"
  },
  "turn_count": 2,
  "lecture_title": "Lecture 1: Probabilities"
}
```

> **Note (step-1 migration):** The `confidence` field has been removed.
> See `docs/policy_routing_spec.md` for the updated state contract, mastery scale, and evidence_notes.

### Meaning of fields

* `topics_sampled`: immutable backend-selected focus topics
* `topics_covered`: topics the student meaningfully engaged (including partial or confused evidence)
* `mastery`: provisional per-topic 0-100 scores, keyed by canonical topic ID (see mastery scale in policy_routing_spec.md)
* `evidence_notes`: per-topic brief internal tags summarizing the strongest evidence seen so far
* `turn_count`: integer
* `lecture_title`: string

Backend-owned prompt context should also include:

* sampled topic labels, not just topic IDs
* approximate elapsed session minutes
* a `closing_mode` flag once the session is nearing a natural finish

These are prompt inputs, not model-owned state fields.

### Validation rules

The backend sanitizes any model-returned state:

* `topics_sampled` must remain unchanged
* `topics_covered` must be a subset of known topic IDs
* `mastery` keys must be known topic IDs
* `mastery` values must be integers 0-100
* `turn_count` must become `old_turn_count + 1`
* `evidence_notes` keys must be known topic IDs; values must be strings
* unknown top-level keys are dropped

### Merge semantics for non-content turns

When the LLM returns empty content-assessment fields (`topics_covered: []`, `mastery: {}`, `evidence_notes: {}`), the backend must preserve the prior state for those fields rather than replacing them with empty values. When the LLM returns non-empty content fields, the backend merges: union for `topics_covered`, key-level update for `mastery` and `evidence_notes`.

> **Note (step-1 migration):** `sanitize_state_update` currently replaces rather than merges, and does not handle `evidence_notes` at all. Both must be fixed during code integration.

The session state is not the source of truth for final grading. It is a running interaction scaffold only.

---

## 7. Model choice and configuration

Add to `app/config.py`:

```python
openai_model: str = "gpt-4.1-mini"
recent_message_limit: int = 10
max_dialogue_context_chars: int = 120000
max_grading_context_chars: int = 180000
sampled_topic_count: int = 5
opening_topic_choice_count: int = 3
closing_mode_minutes: int = 25
target_session_finish_minutes: int = 30
```

The model should be configurable through settings, but there should still be a concrete default in code.

---

## 8. Context budget strategy

The v1 plan was too naive about prompt size.

### 8.1 Dialogue context

Dialogue should receive:

* full rubric
* bounded lecture context
* current state
* recent messages
* current user message
* sampled topic labels
* approximate elapsed session minutes / `closing_mode`

### 8.2 Grading and report context

Grading/report should receive:

* full rubric
* full message history
* bounded lecture context
* current state

### 8.3 Deterministic truncation rule

`build_dialogue_context()` should concatenate these sections in priority order:

1. `bot_notes`
2. `slides`
3. `handout`
4. `notebook`

with explicit section labels.

Then apply a deterministic character cap.
If truncation is needed:

1. trim `notebook` first
2. then trim `handout`
3. keep `slides` and `bot_notes` as long as possible
4. never truncate the rubric

No hidden summarization step is introduced in v1.

---

## 9. Dialogue path

The dialogue path should preserve the fixed top-level grade formula while making the tutor more flexible and engaging inside a topic.

### 9.0 Dialogue behavior requirements

The tutoring prompt stack should use decision heuristics rather than a fixed move sequence.

At a minimum, the tutor should be able to choose among moves such as:

* open probe
* narrowing question
* contrastive question
* request for example
* request for counterexample or near-miss
* request for practical interpretation
* request for transfer or application
* ask the student to diagnose an earlier mistake
* ask the student to compare two plausible claims
* ask for a one-sentence takeaway
* small hint
* partial target or partial answer
* compact explanation
* explicit naming of the target concept
* rephrase in plainer language
* offer a choice of topics
* topic switch
* challenge increase
* challenge decrease
* short recap before a fresh check
* closing or wrap-up move

The bot engine should avoid overusing one move type or repeating low-yield moves.

Challenge-adjustment heuristics should be explicit:

* increase challenge when the student shows criterion-level understanding, makes sharp distinctions, self-corrects, succeeds on a fresh application, asks to go deeper, or signals that the questioning is too easy
* decrease challenge when the student cannot locate the target, gives several vague replies, asks what the tutor is trying to get at, seems disengaged because the interaction is opaque, or when recent moves have been low-yield
* treat boredom as ambiguous: it can mean "too easy" or "too opaque"

Information-giving heuristics should also be explicit:

* the tutor may sometimes name the target concept, give a compact distinction, or provide a partial answer when another probe is unlikely to help
* the goal is to restart productive thinking, not to dump the answer
* after giving information, prefer a fresh check in a different form when staying on the topic

Topic-switch heuristics should also be explicit:

* consider switching when the student asks to switch, boredom or frustration is explicit or strongly implied, recent moves were low-yield, enough evidence has already been banked on the current topic, another sampled topic is likely to re-engage the student better, or the session is in closing mode
* staying is often better when the student is making real progress or one qualitatively different move is still likely to work
* switching does not erase already banked evidence

## 9.1 Prompt contract

The dialogue call must return JSON only:

```json
{
  "assistant_message": "short pedagogical reply with one focused next question",
  "updated_state": {
    "topics_covered": ["T1", "T4"],
    "mastery": {"T1": 60, "T4": 35},
    "evidence_notes": {"T1": "criterion stated", "T4": "vague label only"},
    "turn_count": 2,
    "lecture_title": "Lecture 1: Probabilities"
  }
}
```

The prompt must explicitly instruct the model:

* do not change `topics_sampled`
* do not invent new topic IDs
* keep the reply short
* ask at most one next question
* update topics_covered, mastery, and evidence_notes for meaningfully engaged topics
* do not update multiple topics on thin evidence
* answer "what are you trying to get at?" directly in one short sentence when asked, then continue productively
* allow topic switching, pace adjustment, and other allowed session-steering requests to change tutor behavior
* use decision heuristics rather than a rigid move ladder
* return JSON only

The prompt should also receive enough context to support:

* a brief opening choice among 2-3 sampled lecture topics
* direct handling of allowed session-steering requests
* closing mode after about 25 minutes

### 9.2 Fallback dialogue behavior

If the OpenAI call fails or the JSON is malformed:

* increment `turn_count` locally
* preserve the previous state otherwise
* return a generic fallback such as:

  * "I'm having trouble updating the tutoring state cleanly. Let's keep going with one focused question: what idea from this lecture seems most important to you, and why?"

This must not be lecture-specific.

The fallback should still sound conversational rather than like a hard reset.

---

## 10. Grading path

## 10.1 Grading philosophy

The model grades only the topics that have been touched or evidenced in the conversation.
For each touched topic, it returns a 0-100 mastery score based on the rubric and a short rationale.

Python then converts those touched-topic scores into the student-facing weighted grade.

The fixed weighting stays `55 / 25 / 13 / 4 / 3`.
Only the within-topic calibration changes in this pass.

This means:

* the model does not compute the final weighted total
* the model does not return the student-facing grade as source of truth
* the weighted grade is reproducible and testable

## 10.2 Grading output schema

```json
{
  "topic_scores": [
    {
      "topic_id": "T1",
      "score": 85,
      "rationale": "The student clearly distinguished reality, data, and models."
    },
    {
      "topic_id": "T4",
      "score": 40,
      "rationale": "The student recognized noise but did not separate bias from random error."
    }
  ],
  "explanation": "Strongest on foundational conceptual distinctions; weaker on data imperfection and probability structure.",
  "missing_topics": ["T8", "T10"]
}
```

Prompt instruction must explicitly say:

* do not compute or include a final numeric grade
* return only per-topic scores and commentary
* use canonical `topic_id`s only

## 10.3 Weighted grade computation

`compute_weighted_grade()` should:

1. sort returned topic scores descending by `score`
2. take the top 5
3. if fewer than 5 topics were scored, pad the remaining slots with zeroes
4. apply weights `[55, 25, 13, 4, 3]`
5. compute `floor(sum(weight_i * score_i / 100))`

This makes missing evidence count as zero rather than silently shrinking the denominator.

## 10.4 Grade persistence

After each successful grading attempt:

* compute `candidate_grade`
* compare it to `session.current_grade` (default `0.0` if null)
* accept it as current only if `candidate_grade > session.current_grade`
* if accepted, update `session.current_grade`
* insert `GradeEventModel(event_type="grade", ...)`
* store the full grading payload in `payload_json`, including:

  * `candidate_grade`
  * `accepted_as_current`
  * the per-topic scores
  * explanation
  * missing topics

This makes `current_grade` monotone non-decreasing across the session.

---

## 11. Report path

## 11.1 Report input

`generate_report()` should receive the authoritative accepted `grading_result` dict, containing at least:

* `final_grade`
* `topic_scores`
* `explanation`
* `missing_topics`
* `accepted_as_current`

The report prompt should see all of that.

The report text should naturally mention:

* the student's strongest topic so far
* the next best topic to improve
* whether the student would likely benefit more from deepening covered topics or moving to uncovered ones

If the current request produced a lower candidate grade than the stored best grade, the report should still use the stored accepted grading payload rather than the lower candidate payload.

## 11.2 Report output schema

The model only generates:

```json
{
  "report_text": "..."
}
```

The backend assembles:

```json
{
  "report_text": "...",
  "report_json": {
    "session_id": "...",
    "student_id": "...",
    "timestamp": "...",
    "final_grade": 68
  }
}
```

The model does not generate session metadata.

## 11.3 Grade consistency rule

Within `/generate_report`, the report must use the same accepted grading result that is persisted and whose numeric grade is returned in `report_json`.
There must be no second independent grade computation in the same request.

`/get_grade` and `/generate_report` may each compute a fresh candidate grade from the then-current conversation history.
However, the authoritative grade shown to the student is always the best accepted grade so far:

* if the new candidate grade is higher, it becomes the new current grade and its payload becomes authoritative
* if the new candidate grade is lower or equal, the stored current grade and its previously accepted payload remain authoritative

This keeps the student-facing grade monotone and keeps the explanation/report aligned with the authoritative grade.

## 11.4 Report persistence

Insert `GradeEventModel(event_type="report", ...)` with the report payload.

---

## 12. Endpoint flow changes

## 12.1 `/start_session`

Change `session_manager.build_initial_state()` to accept either:

* parsed topic definitions + sampled topics, or
* the lecture package plus a parsed/sampled helper result

New flow:

1. load lecture package
2. create session row and obtain `session_id`
3. parse rubric topics
4. sample session topics deterministically using `session_id`
5. create initial state with `topics_sampled` populated
6. generate an opening message that briefly offers 2-3 sampled topics and invites the student to choose
7. persist opening message
8. commit

## 12.2 `/send_message`

New flow:

1. load session
2. enforce timeout before generating a reply
3. load state
4. reload lecture package
5. fetch recent messages in chronological order using configured limit
6. compute approximate elapsed session minutes and `closing_mode`
7. call `generate_reply(...)`
8. allow the tutor to adapt to session-steering requests such as hint requests, pace changes, and topic switches
9. append user message
10. append assistant message
11. save sanitized state
12. commit

## 12.3 `/get_grade`

New flow:

1. load session
2. load state
3. reload lecture package
4. fetch full message history
5. call `generate_topic_scores(...)`
6. compute weighted candidate grade in Python
7. compare candidate grade to stored `current_grade`
8. if candidate grade is higher, update `current_grade` and mark this grading payload as accepted
9. if candidate grade is lower or equal, keep stored `current_grade` and keep the previously accepted grading payload authoritative
10. insert grade event for this grading attempt
11. commit
12. return `GradeResponse` based on the authoritative accepted grading payload

## 12.4 `/generate_report`

New flow:

1. load session
2. load state
3. reload lecture package
4. fetch full message history
5. call `generate_topic_scores(...)`
6. compute weighted candidate grade in Python
7. compare candidate grade to stored `current_grade`
8. determine the authoritative accepted grading result:

   * if the candidate grade is higher, it becomes authoritative
   * otherwise the previously accepted grading payload remains authoritative
9. persist `current_grade` only if improved
10. call `generate_report(...)` with that exact authoritative grading result
11. insert report event
12. commit
13. return `ReportResponse`

---

## 13. Timeout enforcement

Add timeout enforcement to `/send_message` while editing the endpoint.

Rule:

* if `now - session.started_at` exceeds `session_timeout_minutes`, reject with HTTP 400 and a clear message such as `"Session has timed out"`

No rolling timeout is introduced in v1 unless the spec is changed.
This is a simple elapsed-from-start timeout.

---

## 14. Error handling

The following failure classes must be caught and handled cleanly:

* malformed JSON from the model
* missing API key / auth error
* rate-limit errors
* transient OpenAI server/network errors

### Dialogue failure

Return fallback assistant text and preserve state except for local turn increment.

### Grading failure

Return a safe response using stored `current_grade` if available, otherwise `0.0`, with an explicit fallback explanation.
Do not write junk grade events.

### Report failure

Return a valid `ReportResponse` with backend-generated report text and valid `report_json`.

The request should not crash with an unhandled vendor exception.

---

## 15. Testing plan

### 15.1 `/start_session`

Add tests that verify:

* `topics_sampled` is populated at session start
* `topics_sampled` contains canonical topic IDs
* `topics_sampled` is deterministic for the session
* the opening message offers 2-3 sampled topics rather than a generic broad opener

### 15.2 `/send_message`

Monkeypatch `bot_engine.generate_reply()` and assert:

* response contains mocked reply
* user and assistant messages persist
* sanitized state persists
* timeout is enforced
* approximate elapsed time / `closing_mode` is passed into the reply path

### 15.3 `/get_grade`

Monkeypatch `generate_topic_scores()` and assert:

* weighted grade is computed in Python
* fewer-than-5 topic results are padded with zeroes
* `current_grade` updates only on improvement
* a lower later candidate does not reduce `current_grade`
* the authoritative response uses the accepted best-grade payload
* a `grade` event is inserted

### 15.4 `/generate_report`

Monkeypatch `generate_topic_scores()` and `generate_report()` and assert:

* report uses the authoritative accepted grade, not merely the latest candidate
* `report_json.final_grade` matches persisted `current_grade`
* if a lower candidate is produced later, the report still uses the previously accepted higher-grade payload
* a `report` event is inserted
* the report text guidance includes strongest topic, next best topic to improve, and whether to deepen covered topics or move to uncovered ones

### 15.5 Unit tests

Add pure tests for:

* rubric topic parsing
* deterministic topic sampling
* weighted grade computation
* state sanitization
* closing-mode threshold logic

---

## 16. Implementation order

### Step 1

Move schemas into `app/schema.py` and add the new control-action schemas there.

### Step 2

Add rubric parsing, topic sampling, state sanitization, weighted-grade helpers, and context builders in `bot_engine.py`.

### Step 3

Update `start_session` and `session_manager` so `topics_sampled` is populated at session creation.

### Step 4

Wire `/send_message` to the real dialogue path, including timeout handling.

### Step 5

Wire `/get_grade` to `generate_topic_scores()` plus Python weighted-grade computation.

### Step 6

Wire `/generate_report` to the same grading result plus report generation.

### Step 7

Add tests and fallback-path tests.

### Step 8

Run manual verification.

---

## 17. What not to do

Do not:

* let the model own `topics_sampled`
* let the model compute the authoritative final grade
* add a prompt framework
* add agent tooling
* move database work into `bot_engine.py`
* store full lecture text in session state
* hardcode lecture-specific fallback questions
* leave grading/report calls able to disagree within a single request
* reintroduce a rigid tutoring move ladder
* treat topic number as an input to within-topic scoring
* add a punitive hard stop at 25 or 30 minutes

---

## 18. Minimal success criteria

The implementation is successful when:

* `topics_sampled` is initialized at session start and remains stable
* `/send_message` uses a real OpenAI call and returns short pedagogical replies
* the opening message offers a natural topic choice among sampled topics
* the tutoring prompts use heuristics rather than a rigid move ladder
* `/get_grade` returns a real grade derived from Python weighting over per-topic mastery scores
* the stored `current_grade` behaves as best demonstrated grade so far and never decreases
* explanations and reports stay aligned with the authoritative accepted grading payload
* `/generate_report` returns a coherent report using the same authoritative grading result it reports
* closing mode begins softly around 25 minutes and still counts the student's final message
* timeout is enforced
* OpenAI failures do not crash the app
* tests pass without calling the real API
* the code remains simple and inspectable
