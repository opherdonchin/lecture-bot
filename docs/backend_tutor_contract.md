# Backend–Tutor Runtime Contract

## 1. Purpose and scope

This contract defines the runtime interface between the lecture-bot backend and the runtime tutor prompt.

It specifies:

* what the backend must provide to the tutor at inference time,
* what the tutor may return,
* which parts of session state are backend-owned and which are tutor-updatable,
* how state updates are interpreted and merged,
* and how lifecycle conditions such as session start and time warnings are represented.

This contract is **structural, not pedagogical**.
Pedagogical identity, priorities, interaction modes, and evaluation philosophy are governed by the tutor specification.
Runtime I/O shape, field ownership, validation, and merge semantics are governed by this contract.

The prompt generator must satisfy **both**:

1. the tutor specification contract, and
2. this backend–tutor runtime contract.

---

## 2. Scope boundaries

This contract applies to the **dialogue tutoring path**: the prompt that produces the tutor’s next conversational turn and any tutor-generated assessment update associated with that turn.

This contract does **not** govern:

* classifier prompts,
* policy-routing prompts,
* grading prompts for `/get_grade`,
* report-writing prompts for `/generate_report`,
* database schemas except insofar as they constrain runtime state semantics,
* frontend UI behavior except where UI actions are surfaced as runtime events.

Those may require separate contracts.

---

## 3. Governing roles

### 3.1 Specification authority

The tutor specification is the governing source of truth for:

* pedagogical purpose,
* identity and stance,
* priorities,
* attention dimensions,
* interaction modes,
* evaluation philosophy,
* success condition.

### 3.2 Backend authority

The backend is the governing source of truth for:

* runtime input variables,
* canonical topic identifiers,
* topic sampling,
* session lifecycle,
* timeout and warning events,
* output shape,
* state ownership,
* validation and merge rules,
* persistence,
* grade computation,
* report generation workflow.

### 3.3 Prompt role

The runtime tutor prompt translates the pedagogical specification into behavior **within** the interface defined by this contract.
It must not invent runtime fields, assume unstated lifecycle semantics, or take ownership of backend-owned state.

---

## 4. Runtime call model

Each tutor call is a single synchronous turn-level inference.
The backend provides a runtime input bundle.
The tutor returns exactly one user-visible reply plus a structured state update.

The backend may call the tutor in different lifecycle contexts, including ordinary student turns and special runtime events.
The same runtime contract applies in all cases unless an explicit subsection below says otherwise.

---

## 5. Runtime inputs

At each tutor call, the backend must provide the tutor with the following logical inputs.
The serialization format is a backend implementation detail; the semantic fields below are the contract.

### 5.1 Required inputs

* `lecture_title: string`
* `rubric: string`
* `lecture_context: string`
* `current_state: object`
* `conversation_history: list[message]`
* `turn_context: object`

Where a `message` has the shape:

```json
{
  "role": "user" | "assistant",
  "content": "string"
}
```

And `turn_context` has the minimum shape:

```json
{
  "turn_kind": "student_turn" | "session_start" | "five_minute_warning",
  "student_message": "string | null"
}
```

### 5.2 Conditional runtime metadata

The backend may additionally provide:

```json
{
  "session_duration_minutes": 15,
  "minutes_remaining": 4,
  "warning_reason": "five_minute_warning"
}
```

These values are optional unless the tutor specification or backend behavior depends on them for a given turn.

### 5.3 Input semantics

* `lecture_title` is the authoritative lecture title for the session.
* `rubric` describes what the lecture covers and what understanding looks like.
* `lecture_context` provides content grounding. It may be full text, concatenated text, curated text, or truncated text according to backend policy.
* `current_state` is the authoritative running model of the student available to the tutor at runtime.
* `conversation_history` is conversational context, not the authoritative state.
* `turn_context.student_message` is the student’s latest message when `turn_kind == "student_turn"`.
* For `session_start`, `student_message` may be `null` or empty.
* For `five_minute_warning`, `student_message` may be absent, empty, or accompanied by a student message depending on backend design.

### 5.4 Non-inference rule

The tutor must not invent values for omitted runtime metadata.
In particular:

* if `minutes_remaining` is absent, the tutor must not imply that it knows how much time is left;
* if `turn_kind` is not a warning event, the tutor must not fabricate a time-warning state;
* if `student_message` is absent on a lifecycle turn, the tutor must not pretend the student asked a content question.

---

## 6. Canonical topic model

### 6.1 Canonical topic IDs

The backend defines the canonical topic universe for a lecture.
Topics are identified by backend-approved canonical topic IDs such as `T1`, `T2`, and so on.

The tutor may refer to topics in structured state updates **only** by canonical topic ID.
It must not invent new IDs, labels, aliases, or free-text topic names as structured keys.

### 6.2 Topic sampling

The backend owns topic sampling.
If session-specific focus topics are used, they are selected by backend logic and provided in `current_state.topics_sampled`.
The tutor may use them to guide attention, opening moves, and breadth decisions, but must not modify them.

---

## 7. Current state schema

The backend stores a full session state.
The tutor receives that state as `current_state`.

The authoritative runtime state has this logical shape:

```json
{
  "topics_sampled": ["T1", "T4", "T7"],
  "topics_covered": ["T1", "T4"],
  "mastery": {
    "T1": 65,
    "T4": 25
  },
  "evidence_notes": {
    "T1": "stated criterion and distinction in own words",
    "T4": "relevant but still vague"
  },
  "turn_count": 6,
  "lecture_title": "Lecture 1: Probabilities"
}
```

### 7.1 Backend-owned fields

The following fields are backend-owned:

* `topics_sampled`
* `turn_count`
* `lecture_title`

The tutor must treat them as read-only.

### 7.2 Tutor-updatable fields

The following fields are tutor-updatable through the structured output defined below:

* `topics_covered`
* `mastery`
* `evidence_notes`

These are not full-replacement fields in tutor output.
They are updated through sparse per-turn deltas.

### 7.3 Field meanings

* `topics_sampled`: backend-selected session focus topics.
* `topics_covered`: topics the student has meaningfully engaged during the session, including weak or partial engagement when it is localizable to a topic.
* `mastery`: current per-topic mastery estimate on the scale defined by the tutor specification.
* `evidence_notes`: brief per-topic summary of the strongest current evidence.
* `turn_count`: number of tutor turns already completed or being tracked by backend policy.
* `lecture_title`: authoritative lecture title carried with state.

---

## 8. Tutor output contract

The tutor must return **JSON only** in exactly this top-level shape:

```json
{
  "assistant_message": "string",
  "updated_state": {}
}
```

No prose, markdown fences, or extra top-level keys are permitted.

### 8.1 `assistant_message`

`assistant_message` is the user-visible reply for the current turn.
It must be a plain string.
It should be a single focused tutor contribution appropriate to the tutor specification and current turn context.

### 8.2 `updated_state`

`updated_state` is a **sparse state delta**, not a full state replacement.
It may contain only tutor-updatable fields.

Allowed shape:

```json
{
  "topics_covered": ["T1"],
  "mastery": {
    "T1": 65
  },
  "evidence_notes": {
    "T1": "student-generated criterion with distinction from nearby confusion"
  }
}
```

Allowed keys in `updated_state` are exactly:

* `topics_covered`
* `mastery`
* `evidence_notes`

The tutor must not return backend-owned fields inside `updated_state`.
In particular, it must not return:

* `topics_sampled`
* `turn_count`
* `lecture_title`
* grade fields
* report fields
* timing fields
* classifier or routing fields

### 8.3 Empty update behavior

If the current turn yields no reliable new content-assessment evidence, the tutor should return an empty or effectively empty delta, for example:

```json
{
  "assistant_message": "...",
  "updated_state": {}
}
```

or

```json
{
  "assistant_message": "...",
  "updated_state": {
    "topics_covered": [],
    "mastery": {},
    "evidence_notes": {}
  }
}
```

Such emptiness means **no new assessment evidence on this turn**, not deletion of prior evidence.

---

## 9. State update semantics

### 9.1 Delta semantics

The tutor’s `updated_state` describes only what the current turn adds or changes.
It does not restate the full session state.

### 9.2 `topics_covered`

`topics_covered` in the delta should contain only topics that the tutor can localize meaningfully from the current turn.
Mention alone is not sufficient.

A topic may appear in the delta if the student:

* genuinely engaged that topic,
* revealed confusion that is clearly about that topic,
* or produced evidence that materially updates the tutor’s understanding of that topic.

### 9.3 `mastery`

`mastery` updates must be:

* keyed only by canonical topic IDs,
* numeric if the specification defines a numeric mastery scale,
* conservative,
* driven by actual turn evidence,
* and omitted for untouched topics.

The tutor must not assign low scores to topics merely because they were not discussed on the current turn.

### 9.4 `evidence_notes`

`evidence_notes` should be brief, topic-local summaries of the strongest current evidence.
They are internal state, not student-facing text.
They should be updated only when the current turn materially changes the tutor’s evidential picture of that topic.

### 9.5 Sparse-update discipline

The tutor should not update many topics on thin evidence.
When evidence is narrow, the update should be narrow.
When evidence is ambiguous, the tutor should prefer no structured assessment update over speculative updates.

### 9.6 Assisted-performance caution

When the student’s apparent success depends heavily on tutor scaffolding, `mastery` and `evidence_notes` must reflect that the evidence is assisted rather than independent.
The tutor specification governs the pedagogical interpretation of this caution; this contract requires that the structured update preserve the distinction.

---

## 10. Backend merge and validation rules

The backend is responsible for validating and merging the tutor’s state delta into stored session state.

### 10.1 Validation

The backend must:

* reject or ignore unknown top-level output keys,
* reject or ignore unknown `updated_state` keys,
* ignore non-canonical topic IDs,
* clamp or sanitize mastery values according to backend policy,
* preserve backend-owned fields regardless of tutor output,
* handle malformed JSON with fallback behavior.

### 10.2 Merge semantics

The backend must treat `updated_state` as a delta using these semantics:

* `topics_covered`: union merge with existing state
* `mastery`: key-level update merge
* `evidence_notes`: key-level update merge
* empty delta: preserve prior state unchanged

### 10.3 Derived-field ownership

The backend, not the tutor, is responsible for:

* incrementing `turn_count`,
* preserving `lecture_title`,
* preserving `topics_sampled`,
* persisting state,
* and deciding what to do on malformed or invalid tutor output.

---

## 11. Lifecycle events

### 11.1 Session start

The contract supports a `session_start` turn kind.
If the backend routes session start through the tutor prompt, it must provide:

* `turn_kind = "session_start"`,
* `topics_sampled` in `current_state`,
* and the lecture/rubric/context inputs needed for a pedagogically grounded opening.

If the backend does **not** route session start through the tutor prompt and instead uses a backend-owned opening message, then the backend assumes responsibility for making that opening behavior conform to the tutor specification.

### 11.2 Five-minute warning

The contract supports a `five_minute_warning` turn kind.
A time warning must be triggered by the backend, not improvised by the tutor.
If this warning is active, the backend should provide the relevant timing metadata needed for the tutor to respond appropriately.

### 11.3 Ordinary student turn

For `student_turn`, the backend should provide the latest student message and the relevant recent conversation history.

### 11.4 Closing behavior

If the backend later wants an explicit closing-turn behavior, it should add a dedicated lifecycle event rather than relying on the tutor to infer closure from silence or timing alone.

---

## 12. Time handling

If the backend provides time information such as `minutes_remaining`, the tutor may use it.
If the student asks how much time is left and the backend has provided a reliable value, the tutor may answer directly.

If the backend does not provide time information, the tutor must not fabricate it.

The tutor may adapt ambition, scope, and pacing based on provided time metadata, but time handling itself remains backend-owned.

---

## 13. Rubric and lecture-context handling

The backend provides `rubric` and `lecture_context` as grounding inputs.

The tutor should use them to:

* understand what the lecture covers,
* choose depth and breadth appropriately,
* and keep the interaction aligned with the lecture.

The tutor must not treat the rubric as a hidden scorecard to expose directly to the student unless the tutor specification explicitly requires that.

The backend may truncate or curate lecture context.
Therefore the tutor must treat `lecture_context` as authoritative for the runtime call but not assume it is the entire lecture corpus.

---

## 14. Non-dialogue actions

The following are backend-owned and outside the ordinary tutor-turn contract:

* current-grade computation,
* final-report generation,
* session restart,
* timeout enforcement,
* persistence of transcripts and grade events.

The ordinary tutor prompt must not attempt to compute the authoritative current grade, final report payload, or backend control flow.

If the product later supports in-chat procedural answers about these actions, those should be handled either by:

* backend logic, or
* separate prompt contracts for procedural or technical-support turns.

---

## 15. Error and fallback expectations

If the tutor output is malformed, incomplete, or invalid under this contract, the backend must remain in control.

Minimum backend fallback responsibilities:

* provide a safe fallback assistant message,
* preserve prior tutor-owned state except for backend-derived counters as appropriate,
* avoid inventing structured assessment evidence,
* and continue the session unless a separate backend policy requires termination.

The tutor prompt should therefore be written to minimize malformed output risk, but correctness is enforced by backend validation rather than trust.

---

## 16. Conformance checklist

A backend–tutor pair conforms to this contract if all of the following hold:

* The backend provides the required runtime inputs.
* The tutor returns JSON only in the required top-level shape.
* `updated_state` is treated as a sparse delta rather than a full replacement.
* The tutor does not attempt to modify backend-owned fields.
* The tutor uses only canonical topic IDs in structured state.
* The backend validates topic IDs and ignores invalid structured updates.
* The backend merges tutor-owned fields with the stated merge semantics.
* The backend, not the tutor, owns `topics_sampled`, `turn_count`, and `lecture_title`.
* Time warnings are backend-triggered rather than tutor-fabricated.
* Session-start behavior is either routed through the tutor prompt with explicit lifecycle context or implemented by the backend in a way that is specification-conformant.
* Ordinary tutor turns do not compute authoritative grades or reports.

---

## 17. Immediate implications for the current repo

To align the current implementation with this contract, the following changes are implied:

1. `updated_state` should be treated as a sparse delta, not a full replacement.
2. `evidence_notes` should become part of runtime state.
3. `confidence` should be removed from the tutor-turn contract unless deliberately retained by a separate specification decision.
4. `turn_count` should be backend-owned only.
5. `lecture_title` and `topics_sampled` should remain backend-owned only.
6. Session-start and five-minute-warning behavior should be represented explicitly by backend lifecycle events if they are to be governed by the tutor prompt.

These are implementation consequences, not optional stylistic preferences.
