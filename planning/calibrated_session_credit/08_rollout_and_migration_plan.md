# 08 — Rollout and migration plan

## Branch strategy

- This planning branch: `plan/calibrated-session-credit-grading` (artifacts
  only, no runtime change).
- Implementation branch (later, after review): e.g.
  `feat/calibrated-session-credit-grading`, created from `main`, applying
  `10_recommended_implementation_prompt.md`.

## Implementation order (low-risk → higher-risk)

1. **Mechanics, pure functions** (`bot_engine.py`): constants, calibrated
   `compute_weighted_grade`, `grade_policy_snapshot`, `compute_ranked_credit_state`,
   calibrated `compute_grade_impact_deltas`, `grade_relevant_next_move`. Land with
   unit tests (sections A–E of `07`). No behavior reaches users until wired.
2. **Prompt injection** (`build_dialogue_system_prompt`): add calibrated guidance
   + `session_credit_status` + next-move to `current_tutoring_state`. Tests
   (section G).
3. **Payloads / events** (`main.py`): credit block in snapshot payload; confirm
   monotone rule; verify report/grade consistency (section F).
4. **Contracts/specs/prompts**: `backend_tutor_contract.md`, `grading_policy.md`,
   `tutor_specification.md`, `tutor_prompt.md`, generator prompt, analysis
   prompts. Update any prompt/spec snapshot tests (section H).
5. **Report wording** (`generate_report`): enrichment framing.
6. **Test sweep**: fix brittle grade-number assertions across the suite
   (section K). Run full `pytest`.
7. **Docs/exports text**: export README/manifest notes (section 7 of `06`).

## Database migration

**No DDL migration required.**
- `sessions.current_grade` stays `float`.
- New fields ride inside `grade_events.payload_json` (already free-form JSON)
  and inside `session_state.state_json` (already free-form JSON).
- `grade_policy_snapshot` makes each event self-describing via `policy_id`.

## Handling existing sessions

- **Do not recompute** historical `sessions.current_grade`. Old sessions keep
  their raw-weighted grade under `policy_id = "fixed-four-topic-v1"`. Rationale:
  grades may already be exported/submitted to Moodle; silently raising them would
  break report/Moodle consistency and student expectations.
- Active in-flight sessions: the next grade event after deploy will use the new
  policy; because of the monotone `max(...)` rule, grades can only rise, which is
  acceptable mid-session. (Document this in the change note; see `09` Q14.)

## Handling old grade events

- Left as-is. Readers branch on `grade_policy.policy_id`; targets/credit-state are
  optional fields, absent on old events. No backfill.

## Manual validation steps

1. Start a fresh session locally; drive a strong-but-not-perfect session; call
   `/get_grade`; confirm the grade is calibrated (higher than the old formula
   would give) and `session_credit_status` appears in the recorded event payload.
2. Push one topic above its target; confirm its `grade_impact_deltas` entry is 0
   and `grade_relevant_next_move` moves to another topic.
3. Reach full credit on four topics; confirm `session_credit_status ==
   "full_credit_reached"`, all deltas 0, `grade_relevant_next_move == null`, and
   the tutor offers enrichment/report rather than compulsory probing.
4. `/generate_report`; confirm report framing does not demand more work for the
   grade and that `report_json.final_grade` matches the accepted grade.
5. Run the Moodle import cross-check on a finished session; confirm no
   grade-mismatch warnings.

## Replaying / inspecting the teacher session

- The packaged session `64eb8bc1-…` (under
  `exports/investigation_export_lecture_06_*/sessions/`) has raw mastery roughly
  `[90,82,78,74]`. Recompute its grade under the new policy with the reference
  function → expect **100** (was 85). Use this as the headline acceptance check.
  Do not mutate the historical record; compute in a scratch script.

## What to check in the next export

- New `grade_events` carry `grade_policy.ranked_full_credit_targets`,
  `ranked_credit_state`, and `session_credit_status`.
- Dialogue audits' `state_before` carry calibrated `grade_impact_deltas`,
  `session_credit_status`, `grade_relevant_next_move`.
- Old events remain parseable alongside new ones.

## Rollback

- Pure-Python policy: rollback = revert the implementation branch. Because no
  schema changed and old events are self-describing, reverting restores the old
  formula for new events without data cleanup. Grades already raised under the
  new policy and submitted would need manual review (note in `09` Q15).
