# Backend–Tutor Runtime Contract

This contract defines the runtime interface between the backend and the model-backed tutor. It is the authoritative home for transport, schema, validation, persistence, visibility, and ownership mechanics.

The tutor specification governs pedagogy. This runtime contract governs how a tutoring turn is called, what the tutor may return, and which parts of that return become state, messages, logs, grades, or lifecycle effects.

**Contract version: 0.7.0.** A contract version is the development version in which the contract last changed. It stays the same across releases that leave the contract alone. The code states the version it implements (`BACKEND_CONTRACT_VERSION` in `app/prompt_loader.py`).

**What invalidates this contract.** A change to what the backend provides or requires always does, and the contract then gets a new version. A change to a tutor specification or to the prompt generator may: a specification may come to need something the backend doesn't provide, and a generator may change how this contract is specified or what's required of it. A pull request changing either of those says whether it invalidates this contract.

A runtime tutor prompt must declare the contract it was written for on its first line, followed by a blank line:

```text
Backend contract: 0.7.0
```

The backend removes that line before sending the prompt to the model. It refuses to start or continue a session, with HTTP 503 and a logged reason, when the lecture's prompt declares another version or none. Version 0.6.1 introduced the tagged reply format (§3). Version 0.7.0 changed the opening, the order of `sampled_topics`, the grade policy and the meaning of `tutor_comment`.

---

## 1. Ordinary tutoring turns

Ordinary model-backed tutor calls happen during `/send_message`.

The backend owns:

- session creation and the opening message, chosen at random, seeded by the session, from those the lecture package supplies,
- topic sampling; `sampled_topics` arrive in lecture order,
- recent-message selection,
- runtime prompt rendering,
- timing metadata,
- persistence,
- state merge logic,
- grading authority,
- report authority,
- timeout closure and lifecycle control.

The tutor owns only the content of the current tutoring response and tutor-updatable sparse state evidence returned for the current ordinary turn.

---

## 2. Runtime inputs

For each ordinary tutoring turn, the backend injects runtime data into the tutor prompt. The current inputs include:

- `lecture_title`
- `chat_language`
- `sampled_topics`
- `topic_structure_note`
- `current_tutoring_state`
- `session_timing`
- `rubric_text`
- `lecture_context`

`current_tutoring_state` includes backend-computed strategic guidance. `grade_impact_deltas` is a JSON object mapping each sampled topic ID to the integer calibrated ΔGrade the student-facing session credit would gain if the next probe on that topic succeeds. The backend computes this under policy `ranked-target-saturation-v2` as the actual trial difference between the current calibrated grade and the calibrated grade after a projected successful probe, with full re-ranking. The backend does not force a topic's delta to zero merely because it already satisfies its current ranked target; a target-satisfied topic may still have a small positive delta when re-ranking would raise the grade.

The same state may include `session_credit_status` (`"in_progress"` or `"full_credit_reached"`), `grade_relevant_next_move` (the sampled topic ID with the largest positive calibrated delta, or `null`), and `ranked_credit_state` (a per-ranked-slot diagnostic breakdown of raw mastery, full-credit target, credit completion, credit contribution, and raw mastery gap). When `session_credit_status == "full_credit_reached"` and no re-ranking can raise the grade, `grade_relevant_next_move` is `null` and all grade-relevant deltas are zero. The tutor must not recompute or modify these values; what they mean is stated here, and how the tutor uses them is for its specification. The tutor must not infer a required number of completed sampled topics from these deltas or expose ranked-slot arithmetic to the student.

`session_timing` includes `minutes_remaining`, `closing_mode` and `timeout_warning_sent`. The turn on which `closing_mode` is true and `timeout_warning_sent` is false is the session's warning turn: it comes once, and the backend then records that the warning was sent. The backend doesn't write the warning itself; the tutor's reply on that turn carries it, stating `minutes_remaining`.

`chat_language` is the course's chat-language setting, `"english"` or `"any"`, fixed for the instance. Under `"english"` the backend refuses non-English student messages before the tutor is called and replaces non-English tutor replies; under `"any"` it does neither. Final reports are required to be English under both values. The tutor uses `chat_language` only to choose the language of its reply.

The backend provides recent conversation history as prior chat messages and the latest student message as the current user message. These are not duplicated inside the injected runtime JSON.

### 2.1 Optional private artifact schema input

The backend may also inject:

- `private_artifact_schema_json`

Semantics:

- It may be absent for a session.
- If present for a session, it is fixed for the duration of that session.
- If present, the backend injects it on each ordinary tutoring turn.
- The active generated schema is snapshotted onto the session record at session creation.
- Prompt history, schema history, schema registries, schema versions, and profile registries are not part of this contract.

---

## 3. Runtime output

The tutor replies in the **tagged format**: the student-facing message as plain text between an `<assistant_message>` line and an `</assistant_message>` line, then one JSON object. When no session private artifact schema exists:

```text
<assistant_message>
Given \(\theta\), the tosses are independent. Why does the posterior narrow as N grows?
</assistant_message>
{"updated_state": {}}
```

When `private_artifact_schema_json` exists for the session:

```text
<assistant_message>
...
</assistant_message>
{"private_artifact": {}, "updated_state": {}}
```

The message carries LaTeX in its ordinary form, with single backslashes. The chat renders mathematics only between `\( ... \)` inline and `\[ ... \]` for display; it does not render `$...$`. The JSON object should contain no LaTeX or backslashes. The backend does not request a JSON response mode.

**Why the message is outside JSON:** inside a JSON string every backslash must be escaped, and the model sometimes writes a garbled escape instead (`\u0018` for `\u2018`, `\b` for the start of `\beta`). The student then sees a control character in place of a symbol ([scope issue #31, PR E](https://github.com/opherdonchin/lecture-bot/issues/31#user-content-pr-e)).

**Order of the JSON object:** `private_artifact` comes before `updated_state`, so that the tutor has written its private judgment of the turn before it sets any score.

**Format reminder:** tutor messages in the recent history appear as plain text, without the tags or the JSON object, and the model sometimes copies that and stops after the message. So the backend adds a short system message after the student's latest message, restating the reply format.

**Turn reminder:** a prompt may end with a section headed exactly `## Turn reminder`, holding the few rules its specification keeps in view on every turn. The backend sends that section's text in the same system message, so the tutor reads it last on each turn. On the warning turn, the same message also says that this is the warning turn and gives `minutes_remaining`.

**Tolerant parsing:** the backend parses the reply as follows.
- If the tags are missing, the message is the text before the JSON object.
- A closing tag written JSON-style (`<\/assistant_message>`) is accepted.
- Up to three missing closing braces are supplied.
- If there is no JSON object, the message is kept with an empty `updated_state` and no `private_artifact`.

An empty message is a parsing failure, which produces the fallback reply.

Output semantics:

- The tagged message (`assistant_message`) is the student-facing reply for the current turn.
- `updated_state` is a sparse tutoring-state delta only.
- `private_artifact` is required on each ordinary tutoring turn when the session has `private_artifact_schema_json`.
- `private_artifact` must conform to the session schema.
- `private_artifact` is private and backend-facing only.
- `private_artifact` is not student-facing.
- `private_artifact` is not tutoring state.
- `private_artifact` is not grading state.
- `private_artifact` is not lifecycle state.

The tutor must not place private-artifact content inside `assistant_message` or `updated_state`.

---

## 4. State ownership

`updated_state` is a sparse delta. It is not a full replacement for session state.

Backend-owned and read-only state includes:

- `topics_sampled`
- `best_mastery`
- `current_grade`
- `timeout_warning_sent`
- `turn_count`
- `grade_impact_deltas`
- `session_credit_status`
- `ranked_credit_state`
- `grade_relevant_next_move`

Tutor-updatable tutoring fields include:

- `mastery`
- `evidence_notes`
- `current_topic_id`
- `tutor_comment`

The backend derives or sanitizes:

- `topics_covered`
- canonical topic ID filtering
- mastery clamping
- turn count
- best mastery
- current grade

### 4.2 mastery field format

`mastery` must be a JSON object mapping canonical topic IDs to integer scores in the range 0–100.

```json
{"T5": 75, "T3": 60}
```

- Keys must be canonical topic IDs supplied by the backend (e.g., `"T1"`, `"T2"`). Unknown or invented keys are dropped.
- Values must be integers (or values coercible to integer). Non-numeric values are silently dropped.
- Values are clamped to the range 0–100.
- Only topics where the student has demonstrated clear understanding should be included. Topics with no evidence should be omitted, not set to 0.
- The backend takes the per-turn maximum across the session to produce `best_mastery`, which feeds the final grade. The tutor must not attempt to reproduce this accumulation.

Calibration guidance (tutor-facing, for inclusion in generated runtime prompts):

| Qualitative level | Integer range |
|---|---|
| no evidence | omit |
| weak evidence | 15–25 |
| developing evidence | 35–50 |
| solid evidence | 55–70 |
| strong evidence | 72–85 |
| robust evidence | 88–100 |

### 4.3 evidence_notes field format

`evidence_notes` must be a JSON object mapping canonical topic IDs to short plain-text strings describing observed evidence for that topic. Values that are not strings are coerced to strings.

The tutor must not return backend-owned fields as proposed updates. The backend ignores unknown or disallowed state keys.

### 4.4 tutor_comment field format

`tutor_comment` is free text that the tutor writes for its own use. The backend returns it unchanged in `current_tutoring_state` on the next turn and doesn't otherwise read it. Students never see it. A value replaces the previous one whole, and omitting the field keeps the previous one. The backend sets no length limit on it. Like the rest of the JSON object, it should contain no LaTeX or backslashes.

### 4.1 Private artifact separation

Private artifacts and tutoring state are separate concerns.

- `private_artifact` must not appear inside `updated_state`.
- `private_artifact` must not be merged into tutoring state.
- `private_artifact` must not be stored in `session_state`.
- `private_artifact` must not be stored in `messages`.
- `private_artifact` must not be used as grading persistence.
- Grading logic must read tutoring state and grade/report events, not private-artifact logs.

---

## 5. Session-fixed schema persistence

The session record may contain nullable `private_artifact_schema_json`.

Semantics:

- `null` means the session has no private artifacts.
- Non-null means the value is the fixed schema for that session.
- The field is written once at session creation.
- The field is not mutated later in the session.

At session creation, the backend:

1. determines the active tutor prompt template,
2. determines the active generated private artifact schema,
3. snapshots the schema into `sessions.private_artifact_schema_json`,
4. leaves the session field null if no schema exists for the active tutor prompt.

For now, the backend treats the currently active generated tutor prompt and generated schema as the source of truth at session start.

---

## 6. Per-turn private artifact log

Private artifacts are persisted per turn in a separate log table. The table stores a small stable shape:

- `id`
- `session_id`
- `turn_index`
- `artifact_json`
- `validation_error`
- `created_at`

`artifact_json` stores the returned per-turn private artifact as JSON text. `validation_error` is null when validation succeeds and otherwise stores a short validation error string.

The backend does not decompose private artifact internals into relational columns.

---

## 7. Validation

Validation is intentionally simple:

- The backend validates that `private_artifact_schema_json` is valid JSON when it is loaded and when a turn uses it.
- The backend validates that returned `private_artifact` is valid JSON by parsing the tutor's JSON response.
- The backend validates returned `private_artifact` against the fixed session schema when the schema exists.

Validation failure rules:

- If the session schema exists and `private_artifact` is missing, treat the model output as a contract failure.
- If the artifact is malformed or invalid against the schema, treat the model output as a contract failure.
- The backend must make one bounded repair attempt before accepting the turn.
- The repair attempt must ask for the whole tagged reply for the same student turn again, with a `private_artifact` in its JSON object conforming to the injected schema.
- If repair succeeds, persist the repaired assistant message, repaired state delta, and valid private artifact.
- If repair fails, enter controlled fallback mode for the tutoring turn, record a validation failure, and avoid accepting the invalid model reply as the student-facing reply.
- Validation failure after repair must not crash the tutoring turn by itself.
- Validation failure after repair must be logged explicitly in the private-artifact log.
- Artifact validation failure must not corrupt tutoring state persistence.

---

## 8. Non-goals

This contract does not introduce:

- prompt history storage,
- prompt versioning,
- schema versioning,
- named schema or profile registries,
- admin browsing UI for private artifacts,
- analytics over private artifacts,
- per-turn schema changes,
- private artifacts inside tutoring state,
- assessor-pass architecture.
