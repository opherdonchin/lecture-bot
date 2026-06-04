# 10 — Recommended implementation prompt (use AFTER this plan is reviewed)

Copy/paste the block below to an implementation agent once the plan in this
directory has been reviewed and approved. Do not run it before review.

---

````markdown
You are working in the `lecture-bot` repository. A reviewed plan exists in
`planning/calibrated_session_credit/` (files `00_*`–`10_*`). Implement it.

Create a branch from `main`:

`feat/calibrated-session-credit-grading`

# Amendments (reviewer-approved — apply these exactly)

1. **Do not force a topic's `grade_impact_delta` to zero** merely because it
   already satisfies its current ranked target. Compute deltas as the actual
   calibrated trial difference: current calibrated grade vs. calibrated grade
   after the projected successful probe, **with full re-ranking**. It is correct
   for a currently target-satisfied topic to have a small positive delta when
   improving it would change the ranking and raise the session grade (e.g. raw
   `[89,82,74,62]` grade 99 → project the rank-2 topic 82→92 → `[92,89,74,62]`
   grade 100 → delta +1). The anti-nitpicking behavior lives in the tutor prompt,
   not in the backend.
2. **Rename** the `ranked_credit_state` field `grade_delta_to_target` to
   `raw_mastery_gap_to_rank_target` — it is a raw mastery gap, not a grade delta.
   Keep `grade_impact_deltas` as the only "grade delta" name.
3. **Deterministic topic-id tie-breaking** must use a real parser
   (`int(topic_id[1:])` for `T<n>`), not string slicing that mis-orders `T10`.

# Policy is a global constant (not per-lecture, yet)

Use `weights=[55,25,13,7]`, `targets=[90,82,74,62]` as **global** module
constants. Parameterize the helpers internally (accept `targets` as an argument
with the global as default) so per-lecture calibration is an easy later drop-in,
but **do not** add lecture-level config in this implementation.

# Goal

Change the student-facing grade from raw weighted mastery to **calibrated
session-credit** grading, policy `ranked-target-saturation-v1`:

- weights `[55, 25, 13, 7]` (unchanged)
- full-credit targets `[90, 82, 74, 62]` (new)
- `grade = floor(Σ weight_i · min(raw_i / target_i, 1.0))` over the top-4 raw
  topic-mastery scores ranked descending, padded with zeros.

Preserve raw topic mastery (0–100) for diagnosis. Do not let the model compute
the authoritative grade. Preserve the monotone non-decreasing `current_grade`
rule and report/grade consistency.

# Implement, in this order

1. `app/bot_engine.py`:
   - `_GRADE_POLICY_ID = "ranked-target-saturation-v1"`,
     `_GRADE_FULL_CREDIT_TARGETS = [90, 82, 74, 62]`.
   - Make grade computation calibrated (`_calibrated_grade_from_scores`; keep
     `compute_weighted_grade` as the public entry, calibrated, with an updated
     docstring).
   - `grade_policy_snapshot()` adds `ranked_full_credit_targets`.
   - Add `compute_ranked_credit_state(best_mastery)` returning per-ranked-slot
     `{topic_id, raw_mastery, rank, target_for_full_credit, credit_completion,
     credit_contribution, raw_mastery_gap_to_rank_target, status}`, plus
     `grade_policy` and `session_credit_status` (`in_progress` |
     `full_credit_reached`).
   - Rework `compute_grade_impact_deltas` to use the calibrated grade as the
     actual trial difference with full re-ranking (never negative; **not** forced
     to 0 for satisfied slots — see Amendment 1).
   - Add `grade_relevant_next_move(sampled_topic_ids, best_mastery) -> str|None`.
   - In `build_dialogue_system_prompt`, inject into `current_tutoring_state`
     (dynamic suffix, cache-safe): calibrated `grade_impact_deltas`,
     `session_credit_status`, `grade_relevant_next_move`, and `ranked_credit_state`.

2. `app/main.py`:
   - Confirm `current_grade = compute_weighted_grade(...)` is now calibrated and
     the monotone `session.current_grade = max(...)` rule still holds.
   - Add `ranked_credit_state` + `session_credit_status` to the grade snapshot
     payload (`_build_grade_snapshot_from_state`).
   - Review hand-written `explanation` strings so they don't imply raw-100 is
     required.

3. `app/bot_engine.generate_report`: instruct the report prompt to treat raw
   topic scores as diagnostic depth and to frame sub-target headroom as optional
   enrichment, not as required work for the grade.

4. Contracts / specs / prompts (keep backend-owned grading vs tutor-owned
   pedagogy separate):
   - `docs/backend_tutor_contract.md` §2/§4: calibrated ΔGrade, saturation rule,
     `session_credit_status`, `grade_relevant_next_move`, `ranked_credit_state`.
   - `docs/grading_policy.md`: add the calibrated session-credit section + the
     four-quantity vocabulary (raw mastery / credit completion / credit
     contribution / student-facing grade); keep the within-topic ladder.
   - `docs/tutor_specification.md`: post-full-credit behavior (optional
     enrichment; no lifecycle-completion claim).
   - `prompts/tutor_prompt.md`: calibrated deltas + full-credit behavior block.
   - `prompts/tutor_generator_prompt.md`: propagate calibrated wording.
   - `prompts/grade_saturation_analysis_prompt.md`,
     `docs/grade_saturation_handoff.md`: redefine saturation as calibrated full
     credit.
   - `prompts/tutor_prompt_private_artifact_schema.json`: optional additive
     enrichment marker; keep backward-compatible.
   - If the live `tutor_prompt.md` is archived, re-archive it and update
     `session_manager._resolve_prompt_document_id` expectations / snapshots.

5. Tests (see `planning/calibrated_session_credit/07_test_plan.md`):
   - Rewrite `tests/test_bot_engine.py` grade cases to the calibrated
     expectations; add credit-state, delta-saturation, next-move, and
     policy-snapshot tests.
   - Fix brittle grade-number assertions across `tests/` (send_message,
     control_actions, admin_*, moodle_grade_import).
   - Add monotone-preservation and report-consistency tests.
   - Update any prompt/spec snapshot or archive-hash tests.

6. Exports: update README/manifest text in
   `scripts/export_session_package.py` and
   `scripts/export_investigation_package.py` to mention the new payload fields
   (no logic change).

# Constraints

- No database migration (new fields ride inside existing JSON columns).
- Do not recompute or rewrite historical grades or old grade events; readers
  branch on `grade_policy.policy_id`.
- Keep raw `best_mastery` semantics unchanged.
- Do not expose target/ranked-slot arithmetic to students.

# Validate

- Run the full test suite (`pytest`) and make it green.
- Recompute the packaged teacher session (`64eb8bc1-…`, raw ≈ `[90,82,78,74]`)
  under the new policy in a scratch script → expect grade **100** (was 85). Do
  not mutate the historical record.
- Manually drive a strong session locally and confirm: calibrated grade,
  per-slot saturation, `full_credit_reached`, `grade_relevant_next_move == null`,
  enrichment-framed report, and a clean Moodle cross-check.

# Report when done

1. branch name
2. files changed (grouped: code / contracts / prompts / tests / docs)
3. test results
4. confirmation the teacher session now grades 100
5. any deviations from the plan and why
````
