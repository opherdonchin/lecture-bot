# 03 — Impacted files and components

Legend for **Kind**: code · contract · prompt · spec · test · doc · schema ·
logging · migration · UI.

Each entry lists path, current responsibility, proposed change, and rationale.
"Inspect / probably no change" entries are included deliberately.

## Backend code

### `app/bot_engine.py` — **code, logging** (primary change site)
- **Current**: defines `_GRADE_POLICY_ID`, `_GRADE_WEIGHTS`,
  `_weighted_grade_from_scores`, `_grade_from_scores`, `compute_weighted_grade`,
  `_SCORE_IF_SUCCESS`, `compute_grade_impact_deltas`, `grade_policy_snapshot`.
- **Change**:
  - Add `_GRADE_FULL_CREDIT_TARGETS = [90, 82, 74, 62]`; change
    `_GRADE_POLICY_ID` to `"ranked-target-saturation-v1"`.
  - Replace the raw weighted sum in `_weighted_grade_from_scores` with the
    calibrated `min(raw/target, 1.0)` sum (or add a new
    `_calibrated_grade_from_scores` and route `compute_weighted_grade` to it —
    see `05_backend_implementation_plan.md` for naming).
  - Extend `grade_policy_snapshot()` to include `ranked_full_credit_targets`.
  - Rework `compute_grade_impact_deltas` to compute **calibrated** deltas as the
    true trial difference with full re-ranking (not forced to `0` for satisfied
    slots — a satisfied slot can show a positive delta when re-ranking raises the
    grade); add a structured strategic-guidance builder that also reports
    `credit_completion`, `credit_contribution`,
    `raw_mastery_gap_to_rank_target`, and `status` per ranked topic plus a
    top-level `session_credit_status`.
- **Why**: this is where the grade and the strategic guidance are computed.

### `app/main.py` — **code**
- **Current**: `_update_backend_grade_state`, `_build_grade_snapshot_from_state`,
  `_compute_authoritative_grade_snapshot`, `_record_grade_event`,
  `build_dialogue_system_prompt` consumer, get_grade/generate_report/send_message.
- **Change**:
  - `current_grade = compute_weighted_grade(...)` automatically becomes
    calibrated once `bot_engine` changes; verify the monotone update still holds.
  - Have the grade snapshot payload carry the new `grade_policy` (with targets)
    and an optional `ranked_credit_state` / `session_credit_status` block for
    diagnostics (see `06_logging_and_diagnostics_plan.md`).
  - Confirm `_build_grade_snapshot_from_state` `explanation` wording does not
    imply raw-mastery-to-100 is required for credit.
- **Why**: it owns persistence, the snapshot payload, and report inputs.

### `app/bot_engine.build_dialogue_system_prompt` (within `bot_engine.py`) — **code, logging**
- **Current**: injects `grade_impact_deltas` into `current_tutoring_state`.
- **Change**: inject the new calibrated strategic-guidance object (keep a
  `grade_impact_deltas` key for backward-compatible prompt wording, but values
  become calibrated; add `session_credit_status`, `ranked_credit_state`,
  `grade_relevant_next_move`). Decide whether to keep the legacy key name or add
  a new `grade_strategic_guidance` field (see open questions).
- **Why**: this is the per-turn tutor input surface.

### `app/session_manager.py` — **code, inspect**
- **Current**: `build_initial_state` sets `current_grade: 0.0`, `best_mastery: {}`.
- **Change**: probably none. Optionally seed a `session_credit_status:
  "in_progress"` if we decide to persist it in state (recommended: derive, don't
  persist). Inspect only.

### `app/models.py` — **schema/migration, inspect**
- **Current**: `SessionModel.current_grade: float`; `GradeEventModel.payload_json`
  is free-form JSON text.
- **Change**: **no DDL change needed.** New fields ride inside `payload_json`.
  `current_grade` stays a float. (See `08_rollout_and_migration_plan.md`.)

### `app/schema.py` — **schema/API, inspect → small change**
- **Current**: `GradeResponse`, `ReportResponse`, `ReportJson`,
  `SendMessageResponse`.
- **Change**: optional additive fields, all with safe defaults — e.g.
  `GradeResponse.session_credit_status: str | None = None`. Do not break
  existing clients. May be deferred to a later UI phase.

### `app/moodle_grade_import.py` — **code, inspect**
- **Current**: cross-checks report grade vs `sessions.current_grade` within
  tolerance.
- **Change**: none functionally — both sides use the new authoritative grade.
  Verify the tolerance comparison still holds for floored integer grades.

### `app/admin_sessions.py` — **code/UI, inspect**
- **Current**: filters/sorts on `current_grade`, shows `grade_events` count.
- **Change**: none required. Numbers shift upward; no schema change.

## Contracts, specs, prompts

### `docs/backend_tutor_contract.md` — **contract** (normative change)
- §2 describes `grade_impact_deltas` as "ΔGrade if the next probe succeeds … same
  fixed ranked-topic grading formula." Must change to describe **calibrated**
  ΔGrade as the true calibrated trial difference (with full re-ranking; not
  forced to 0 for satisfied slots), and the new `session_credit_status` /
  `grade_relevant_next_move` semantics.
- §4 backend-owned field list stays (`best_mastery`, `current_grade`,
  `grade_impact_deltas`); add the new strategic-guidance fields as backend-owned.

### `docs/grading_policy.md` — **doc** (normative working note)
- The whole cross-topic table and "Max cumulative" column assume raw-to-100.
  Add a calibrated session-credit section: targets `[90,82,74,62]`, the
  `min(raw/target,1)` rule, the four-quantity vocabulary, and that raw mastery is
  retained for diagnosis. Keep the within-topic ladder (it still governs raw
  mastery and the projection used for deltas).

### `docs/tutor_specification.md` — **spec** (mostly explanatory)
- Add post-full-credit behavior (optional enrichment, not lifecycle completion).
- Clarify that "backend strategic guidance" is now calibrated and that a
  `grade_relevant_next_move == null` means no compulsory grading work remains.
- Keep the no-completion-claim rule.

### `docs/tutor_specification_contract.md` — **contract, inspect**
- Verify nothing hardcodes raw-weighted assumptions. Likely no change beyond a
  note that evaluative shape (mastery scale) is unchanged.

### `prompts/tutor_prompt.md` — **prompt** (normative)
- Update the `grade_impact_deltas` description to "calibrated grade impact."
- Add the full-credit / optional-enrichment behavior block.
- Reaffirm: do not recompute, do not expose target arithmetic, do not claim
  completion.

### `prompts/tutor_prompt_private_artifact_schema.json` — **schema/prompt, inspect → small change**
- The `strongest_alternative_direction.source` enum value
  `"grade_impact_deltas_or_backend_strategic_guidance"` still applies. Optionally
  add an enrichment-mode signal (e.g. allow a move-type that reflects
  post-full-credit optional work). Keep changes additive and backward-compatible.

### `prompts/tutor_generator_prompt.md` — **prompt, inspect**
- The generator emits runtime tutor prompts from the spec/contracts. Verify it
  carries forward the calibrated wording. Likely needs the same delta-wording
  update so regenerated prompts stay consistent.

### `prompts/grade_saturation_analysis_prompt.md`, `docs/grade_saturation_handoff.md` — **doc, inspect**
- Analysis prompts that reason about grade saturation. Update references so they
  interpret saturation as **calibrated full credit**, not raw-100.

## Tests

### `tests/test_bot_engine.py` — **test** (will break, intentional)
- Many `test_compute_weighted_grade_*` assert raw-weighted values (e.g.
  `[:1] → 55`, `[:2] → 80`, `[:3] → 93`, `floor` cases, top-4). The 100-cases
  still pass; the partial cases change. Rewrite to the calibrated expectations in
  `07_test_plan.md`.

### `tests/test_send_message.py`, `tests/test_control_actions.py`,
`tests/test_admin_sessions.py`, `tests/test_admin_app.py`,
`tests/test_admin_generation.py`, `tests/test_moodle_grade_import.py` — **test, inspect**
- Any test asserting a concrete grade number for a non-saturated session may
  shift. Inspect and update expected grades; keep structural assertions.

## Export / analysis / downstream

### `scripts/export_session_package.py`, `scripts/export_investigation_package.py` — **code, inspect**
- They serialize `grade_events.payload_json` verbatim and `current_grade`. They
  will automatically carry the new policy + targets + credit state. No change
  needed beyond optionally documenting the new payload fields in their README
  text.

### `scripts/list_sessions.py`, `scripts/grade_moodle.py`,
`scripts/prepare_moodle_grade_import.py` — **code, inspect**
- Read grades/payloads. Inspect for any hardcoded weight/threshold assumptions
  (none expected). Probably no change.

## UI

### `app/static/chat.js`, `app/templates/chat.html` — **UI, inspect**
- Show `grade / 100` and the report. No change required to function; a later
  optional phase could surface "full session credit reached." Not required for
  correctness.

### `app/static/style.css`, `app/static/admin.css` — **UI, inspect**
- `grade-*` CSS classes only. No change.
