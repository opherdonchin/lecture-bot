# 07 — Test plan

All numeric expectations below were verified against a reference implementation
of the calibrated formula (`weights=[55,25,13,7]`, `targets=[90,82,74,62]`,
`grade=floor(Σ weight·min(raw/target,1))`).

## A. `compute_weighted_grade` (now calibrated) — `tests/test_bot_engine.py`

Rewrite the existing `test_compute_weighted_grade_*` group. New expectations:

| Test | Input scores | Expected |
|---|---|---|
| `targets_exact_full_credit` | `[90, 82, 74, 62]` | `100` |
| `teacher_session_reaches_full_credit` | `[90, 82, 78, 74]` | `100` |
| `one_strong_topic` | `[90]` | `55` |
| `two_strong_topics` | `[90, 82]` | `80` |
| `three_strong_topics` | `[90, 82, 74]` | `93` |
| `all_perfect` | `[100, 100, 100, 100]` | `100` |
| `all_zero` | `[0, 0, 0, 0]` | `0` |
| `empty` | `[]` | `0` |
| `raw_above_target_does_not_exceed_weight` | `[95, 90, 80, 70]` | `100` |
| `caps_at_100` | `[100]*8` | `100` (top-4 only) |
| `fewer_than_four_padded_with_zero` | `[90, 82]` | `80` (slots 3,4 contribute 0) |
| `below_target_partial` | `[45, 45, 45, 45]` | `54` |
| `at_lowest_target_band` | `[62, 62, 62, 62]` | `74` |

Add an explicit cross-check test:
- `compute_weighted_grade(scores) == compute_ranked_credit_state(best_mastery)["grade-equivalent"]`
  i.e. `floor(Σ credit_contribution)` equals `compute_weighted_grade` for the
  same scores.

## B. Per-slot credit semantics — `compute_ranked_credit_state`

- `raw_above_target_status`: `best_mastery={"T1":95}` → rank-1 row
  `status == "full_credit_satisfied"`, `credit_completion == 1.0`,
  `credit_contribution == 55`, `raw_mastery == 95` (raw preserved).
- `below_target_status`: `best_mastery={"T1":50}` → rank-1
  `status == "below_target"`, `credit_completion ≈ 0.5556`,
  `grade_delta_to_target == 40`.
- `padding`: `best_mastery={"T1":90}` → rows 2–4 have `topic_id is None`,
  `credit_contribution == 0`, `session_credit_status == "in_progress"`.
- `full_credit_status`: `best_mastery={"T6":90,"T3":82,"T7":78,"T1":74}` →
  `session_credit_status == "full_credit_reached"`, all rows
  `full_credit_satisfied`.
- `ranking_by_raw`: ensure the highest raw score is assigned rank 1 / weight 55.

## C. Grade-impact deltas — `compute_grade_impact_deltas`

- `zero_delta_for_target_satisfied_slot`: a topic whose ranked slot is already at
  or above target returns delta `0` even though raw mastery < 100. E.g.
  `best_mastery={"T1":92,"T2":85,"T3":80,"T4":70}` (all at/over target after
  ranking) → all sampled deltas `0`.
- `zero_delta_at_raw_100`: topic at 100 → delta `0` (projection `None`).
- `positive_delta_below_target`: a below-target topic returns a positive
  calibrated delta equal to the calibrated-grade increase when projected up.
- `delta_never_negative`: projecting can only raise raw mastery; assert all
  deltas ≥ 0.
- `full_credit_all_zero`: when `session_credit_status == "full_credit_reached"`,
  every sampled delta is `0`.

## D. Next-move signal — `grade_relevant_next_move`

- returns the topic with the largest positive delta when one exists;
- returns `None` when all deltas are `0` (full credit or all at 100);
- deterministic tie-break (same input → same output).

## E. Policy snapshot — `grade_policy_snapshot`

- includes `policy_id == "ranked-target-saturation-v1"`,
  `ranked_topic_weights == [55,25,13,7]`,
  `ranked_full_credit_targets == [90,82,74,62]`.
- every recorded grade/report event payload contains this snapshot
  (`_record_grade_event` test).

## F. Persistence / monotone behavior — `tests/test_send_message.py`,
`tests/test_control_actions.py`

- `monotone_current_grade_preserved`: after a high accepted grade, a later
  snapshot computing a lower candidate grade does **not** lower
  `sessions.current_grade` (existing `max(...)` rule).
- `report_uses_authoritative_payload`: `/generate_report` final grade equals the
  authoritative accepted grade (not a fresh lower recompute). Covers
  `09` Q13.
- `send_message_timeout_grade_is_calibrated`: a timeout closure for a
  strong-but-not-perfect session returns the calibrated (higher) grade.

## G. Prompt injection — dialogue prompt build

- `prompt_contains_calibrated_guidance`: `build_dialogue_system_prompt` output's
  `current_tutoring_state` includes `grade_impact_deltas`,
  `session_credit_status`, `grade_relevant_next_move` (and optionally
  `ranked_credit_state`).
- `full_credit_prompt_signals_no_next_move`: for a full-credit `best_mastery`,
  the injected `grade_relevant_next_move` is `null` and
  `session_credit_status == "full_credit_reached"`.
- Cache safety: assert the credit block is in the dynamic suffix, not the
  cache-stable prefix (so prefix is unchanged for the same lecture/prompt).

## H. Prompt/spec snapshot tests (if the repo has them)

- The archive/prompt tests (`tests/test_archive.py`,
  `tests/test_bootstrap_archive.py`, `tests/test_admin_generation.py`) assert
  prompt/spec content hashes or schema. After editing `tutor_prompt.md`,
  `backend_tutor_contract.md`, etc., update any committed snapshots / expected
  SHAs. Inspect for hardcoded prompt text assertions.

## I. Moodle import consistency — `tests/test_moodle_grade_import.py`

- `report_grade_matches_db_grade`: report grade and `sessions.current_grade`
  agree within tolerance under the new policy. Inspect fixtures that hardcode a
  grade number and update.

## J. Backward compatibility

- `old_policy_event_still_parses`: a `grade_events` row with
  `policy_id == "fixed-four-topic-v1"` and no targets is read without error;
  readers treat targets as absent.
- `mixed_policy_session`: a session with an old grade event followed by a new one
  keeps both self-describing snapshots; the monotone accepted grade still wins.

## K. Brittle-test sweep (inspect, then fix)

Search the test suite for hardcoded non-saturated grade numbers and recompute
expectations under the calibrated policy. Known break sites:
`test_compute_weighted_grade_cumulative_perfect_topic_geometry`
(`55/80/93/100` → now `55/80/93/100`? note: those used perfect 100 scores, so
they still pass), `test_compute_weighted_grade_floor`,
`test_compute_weighted_grade_takes_top_4`, `test_compute_weighted_grade_weighted_order`,
`test_compute_weighted_grade_zero_padding` — recompute each. (The all-100 cases
are unchanged; the partial-score cases change.)

> Note on the geometry test: `[:1]→55, [:2]→80, [:3]→93, [:4]→100` used score=100
> per topic, so it still holds under calibration (100 ≥ every target). Only tests
> using sub-target scores need new numbers.
