# 00 — Current grading architecture

Self-contained description of the lecture-bot grading system as it exists on
`main` at the time this plan was written. A reader with no repo access should be
able to understand the current system from this document alone.

## 1. Stack and shape

- **Backend**: FastAPI app in `app/` (Python). SQLite via SQLAlchemy ORM.
- **Model calls**: OpenAI Chat Completions (`response_format=json_object`) for
  three distinct purposes: ordinary tutoring turns, mastery scoring, and report
  prose.
- **Tutor**: a model-backed Socratic tutor driven by a runtime system prompt
  assembled per turn. The tutor proposes *evidence* (per-topic mastery); the
  backend owns the *grade*.
- **Student UI**: `app/static/chat.js` + `app/templates/chat.html`. Buttons call
  `/get_grade` and `/generate_report`. Grade is shown as `<grade> / 100`.
- **Admin UI**: `app/templates/admin_*.html`, including a Moodle grade-import
  workflow.

## 2. Canonical concepts

- **Topic**: identified by canonical ID `T1`, `T2`, … parsed from the rubric
  markdown headers (`### Tn. <label>`). See
  `bot_engine.parse_rubric_topics` / `resolve_topic_defs` /
  `normalize_topic_defs`.
- **Sampled topics**: a deterministic per-session subset (seeded by
  `session_id`) of topic IDs, size `sampled_topic_count`. Defines the candidate
  opportunity space surfaced to the tutor. See `sample_session_topics`.
- **mastery** (state field): per-turn, tutor-proposed `{topic_id: int 0-100}`.
  Only topics with demonstrated understanding are included.
- **best_mastery** (state field): backend-owned running per-topic maximum across
  the session. This is what feeds the grade.
- **current_grade**: backend-owned student-facing numeric grade 0–100,
  monotonic non-decreasing within a session.

## 3. Key files and functions

### `app/bot_engine.py` — grading mechanics (the core)

- `_GRADE_POLICY_ID = "fixed-four-topic-v1"`
- `_GRADE_WEIGHTS = [55, 25, 13, 7]`
- `grade_policy_snapshot()` → `{"policy_id", "ranked_topic_weights"}`. Stored
  with every grade event.
- `_weighted_grade_from_scores(scores: list[int]) -> int`
  ```python
  ranked = sorted(scores, reverse=True)[:4]
  padded = (ranked + [0,0,0,0])[:4]
  return floor(sum(w * s / 100 for w, s in zip([55,25,13,7], padded)))
  ```
- `_grade_from_scores(dict) -> int`: wraps the above over `dict.values()`.
- `compute_weighted_grade(topic_scores: list[dict]) -> int`: public entry used by
  the backend; pulls `ts["score"]` and calls `_weighted_grade_from_scores`.
- `_SCORE_IF_SUCCESS`: a 7-row projection table mapping a current raw mastery
  band `(lo, hi)` to the raw mastery the topic would reach if the *next probe
  succeeds* (e.g. band `55–71 → 77`, band `100 → None`). This models the
  concave within-topic ladder.
- `compute_grade_impact_deltas(sampled_topic_ids, best_mastery) -> {tid: int}`:
  for each sampled topic, projects the topic to its `_SCORE_IF_SUCCESS` value,
  recomputes the **raw weighted grade**, and returns the integer grade gain.
  Topics already at 100 return delta 0. **This is the "strategic guidance"
  surfaced to the tutor.**
- `sanitize_state_update(...)`: merges the tutor's sparse `updated_state` into a
  sanitized state. `best_mastery` and `current_grade` are preserved from
  `old_state` (backend-owned, read-only to the tutor); `mastery`,
  `evidence_notes`, `current_topic_id`, `tutor_comment` are tutor-updatable.
- `generate_topic_scores(...)`: an **independent LLM grading pass** over the full
  conversation that returns `{topic_scores:[{topic_id,score,rationale}],
  explanation, scored_topics, missing_topics}`. Note: in current `main.py` flow
  this assessor pass is **not** the live path for `/get_grade` /
  `/generate_report` — those derive the grade from `best_mastery` in state (see
  §4). `generate_topic_scores` still exists and is exercised by tests.
- `generate_report(...)`: produces the report prose from a `grading_result`. It
  is explicitly told *"Do not include a grade number — the backend adds it."*

### `app/main.py` — flow + persistence

- `_update_backend_grade_state(db, session, state, lecture_package)`:
  - coerces `mastery` and `best_mastery` from state,
  - if `best_mastery` empty, seeds it from the prior authoritative grade event's
    `topic_scores`,
  - folds current `mastery` into `best_mastery` (per-topic max),
  - drops zero-scored topics,
  - `current_grade = compute_weighted_grade(topic_scores from best_mastery)`,
  - writes `state["best_mastery"]`, `state["current_grade"]`,
  - `session.current_grade = max(existing, current_grade)` (**monotone rule**).
- `_build_grade_snapshot_from_state(...)`: builds the authoritative grade payload
  from `best_mastery`: `topic_scores` (with evidence_notes as rationale),
  `scored_topics`, `missing_topics`, an `explanation` string, and
  `grade = max(state.current_grade, session.current_grade)`. Returns a dict with
  `candidate_grade`, `accepted_as_current: True`, `payload`, etc.
- `_compute_authoritative_grade_snapshot(...)`: calls
  `_update_backend_grade_state` then `_build_grade_snapshot_from_state`.
- `_record_grade_event(db, session_id, event_type, grade, payload)`: inserts a
  `grade_events` row; injects `payload["grade_policy"]` from
  `grade_policy_snapshot()` if absent.
- `_get_authoritative_grading_payload(...)`: returns the most-recent
  `accepted_as_current` payload across `grade`+`report` events (supports the
  monotone/consistency behavior).
- `_generate_authoritative_report_result(...)`: builds `grading_result` from the
  snapshot, calls `bot_engine.generate_report`, records a `report` event with a
  `report_payload`.

### `app/session_manager.py`

- `build_initial_state(...)`: initial state shape (`best_mastery: {}`,
  `current_grade: 0.0`, `mastery: {}`, `evidence_notes: {}`, etc.).
- `load_state` / `save_state`: JSON (de)serialization of `session_state.state_json`.

### `app/models.py`

- `SessionModel.current_grade: float | None`.
- `GradeEventModel`: `id, session_id, event_type ("grade"|"report"),
  grade: float, timestamp, payload_json`.
- `SessionStateModel.state_json`: the full tutoring state JSON.
- `DialogueTurnAuditModel`, `PrivateArtifactLogModel`: diagnostic logs.

### `app/schema.py`

- `GradeResponse{grade, explanation, scored_topics, missing_topics, timing…}`.
- `ReportResponse{report_text, report_json}`,
  `ReportJson{…, final_grade, …}`.
- `SendMessageResponse{…, final_grade, final_grade_explanation,
  final_scored_topics, final_missing_topics, final_report}` (timeout closure).

## 4. Data flow

### `/send_message`
1. Load session + state. Build runtime prompt via
   `bot_engine.build_dialogue_system_prompt`, which injects
   `current_tutoring_state` **including** `grade_impact_deltas` (from
   `compute_grade_impact_deltas`).
2. Call the tutor; sanitize `updated_state` (tutor proposes `mastery`,
   `evidence_notes`, …).
3. `_update_backend_grade_state` folds mastery → best_mastery, recomputes
   `current_grade`, updates monotone `session.current_grade`.
4. On timeout, build the authoritative grade snapshot, record a `grade` event,
   generate the report, record a `report` event, and return the closure payload.

### `/get_grade`
1. Load state. `_compute_authoritative_grade_snapshot` (updates best_mastery and
   grade from state).
2. Record a `grade` event with the snapshot payload.
3. Return `GradeResponse` (grade, explanation, scored/missing topics, timing).

### `/generate_report`
1. Load state. `_compute_authoritative_grade_snapshot`.
2. `_generate_authoritative_report_result` → `bot_engine.generate_report` →
   record `report` event → return `ReportResponse`.

## 5. How raw topic mastery is created and stored

- The tutor returns per-turn `mastery` (sparse, evidence-only).
- `sanitize_state_update` clamps and filters it.
- `_update_backend_grade_state` accumulates the per-topic **maximum** into
  `best_mastery` (monotone per topic). `best_mastery` lives in
  `session_state.state_json`. Raw mastery 0–100 is preserved.

## 6. How current grade is computed and persisted

- Grade = `floor(Σ weight_i · rank_i_score / 100)` over the top-4 ranked
  `best_mastery` scores. Stored in `state["current_grade"]` and, monotone,
  `sessions.current_grade`. Re-emitted into every grade/report event `payload`
  and `grade_events.grade`.

## 7. How reports use grading payloads

- The report is generated from `grading_result` (final_grade, topic_scores,
  explanation, scored/missing topics). The LLM writes prose only; the backend
  supplies the authoritative number. `report_json.final_grade` carries the
  number. The Moodle import workflow (`app/moodle_grade_import.py`) later
  cross-checks the report grade against `sessions.current_grade` within a
  tolerance.

## 8. How diagnostic artifacts are produced

- **Private artifact log** (`private_artifact_logs`): per-turn JSON the tutor
  emits, validated against the session-fixed
  `tutor_prompt_private_artifact_schema.json`. It records the tutor's move
  rationale, including a `strongest_alternative_direction.source` enum value
  `"grade_impact_deltas_or_backend_strategic_guidance"`.
- **Dialogue turn audit** (`dialogue_turn_audits`): per-turn snapshot of
  `state_before`, rendered prompt, target topic, tokens, etc.
- **Grade events** (`grade_events`): each carries the full grade `payload`
  including `topic_scores`, `explanation`, and `grade_policy` snapshot.
- Export scripts (`scripts/export_session_package.py`,
  `scripts/export_investigation_package.py`) bundle sessions, messages, audits,
  state, and **grade_events with parsed payloads** for offline analysis.

## 9. How tutor prompt / spec / contracts relate to grading

- `docs/grading_policy.md`: the working calibration note — weights `[55,25,13,7]`,
  within-topic concave mastery ladder, "backend computes the grade, tutor
  assesses mastery."
- `docs/backend_tutor_contract.md` §2 + §4: normative runtime contract. Declares
  `grade_impact_deltas` as a backend-computed input ("ΔGrade if the next probe on
  that topic succeeds"), and lists `best_mastery`, `current_grade`,
  `grade_impact_deltas` as backend-owned, read-only fields.
- `docs/tutor_specification.md` + `tutor_specification_contract.md`: pedagogy.
  The tutor treats `grade_impact_deltas` / backend strategic guidance as the
  **opportunity-cost baseline** for move selection, must not compute official
  grades, and must not claim "grade saturation"/completion.
- `prompts/tutor_prompt.md`: the live runtime prompt. Restates the above:
  reads `grade_impact_deltas`, never recomputes them, never claims completion.
- `prompts/tutor_prompt_private_artifact_schema.json`: the per-turn private
  artifact schema (move rationale, strongest alternative, self-check).
