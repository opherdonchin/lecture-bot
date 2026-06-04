# Planning: calibrated session-credit grading

Planning-only artifacts (no runtime change) for moving the lecture-bot grade
from raw weighted mastery to **calibrated session-credit** grading
(`policy_id = "ranked-target-saturation-v1"`, weights `[55,25,13,7]`, full-credit
targets `[90,82,74,62]`, `grade = floor(Σ weight·min(raw/target,1))`).

Headline effect: the strong 30-minute teacher session with raw mastery
`[90,82,78,74]` moves from **85 → 100**, while raw mastery (0–100) is retained
for diagnosis.

## Read in order

| File | Purpose |
|---|---|
| `00_current_architecture.md` | self-contained description of today's grading system |
| `01_problem_statement.md` | the calibration problem + the four-quantity vocabulary |
| `02_proposed_behavior.md` | target behavior, formula, worked vectors |
| `03_impacted_files_and_components.md` | every impacted file with kind + rationale |
| `04_contract_and_spec_revision_plan.md` | contract/spec/prompt revisions (normative vs explanatory) |
| `05_backend_implementation_plan.md` | helpers, pseudocode, payloads, failure modes |
| `06_logging_and_diagnostics_plan.md` | JSON shapes for grade events, prompt guidance, exports |
| `07_test_plan.md` | concrete tests with verified expected numbers |
| `08_rollout_and_migration_plan.md` | order, no-DDL migration, validation, rollback |
| `09_open_questions_and_risks.md` | decisions needed + risks |
| `10_recommended_implementation_prompt.md` | the prompt to hand an implementer after review |
| `grading_code_inventory.md` | excerpts of the current grading code for reviewers without repo access |

## Key facts established by inspection

- Current formula lives in `app/bot_engine.py` (`_weighted_grade_from_scores`,
  `compute_weighted_grade`); weights `_GRADE_WEIGHTS = [55, 25, 13, 7]`.
- `best_mastery` (raw, monotone per topic) is stored in
  `session_state.state_json`; `current_grade` is monotone in `sessions` and
  echoed into each `grade_events.payload_json`.
- The tutor receives `grade_impact_deltas` (today: raw weighted gains) as its
  opportunity-cost baseline; it never computes the official grade.
- No DB migration is needed — new fields ride inside existing JSON columns and
  each grade event is self-describing via `grade_policy`.
