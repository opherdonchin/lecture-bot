# Backend–Tutor Runtime Contract

This contract defines the runtime interface between the backend and the model-backed tutor. It is the authoritative home for transport, schema, validation, persistence, visibility, and ownership mechanics.

The tutor specification governs pedagogy. This runtime contract governs how a tutoring turn is called, what the tutor may return, and which parts of that return become state, messages, logs, grades, or lifecycle effects.

---

## 1. Ordinary tutoring turns

Ordinary model-backed tutor calls happen during `/send_message`.

The backend owns:

- session creation and opening message behavior,
- topic sampling,
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
- `sampled_topics`
- `topic_structure_note`
- `current_tutoring_state`
- `session_timing`
- `rubric_text`
- `lecture_context`

`current_tutoring_state` includes a backend-computed `grade_impact_deltas` field: a JSON object mapping each sampled topic ID to the integer ΔGrade the tutor would gain if the next probe on that topic succeeds. The backend computes this using the same grading formula and calibration tiers used by `compute_weighted_grade`. The tutor reads these values for move selection and must not recompute or modify them.

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

When no session private artifact schema exists, the tutor should return JSON in this top-level shape:

```json
{
  "assistant_message": "string",
  "updated_state": {}
}
```

When `private_artifact_schema_json` exists for the session, the tutor must return JSON in this top-level shape:

```json
{
  "assistant_message": "string",
  "updated_state": {},
  "private_artifact": {}
}
```

Output semantics:

- `assistant_message` is the student-facing reply for the current turn.
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
- The repair attempt must ask for the full response JSON for the same student turn, including a top-level `private_artifact` conforming to the injected schema.
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
