# 06 — Logging and diagnostics plan

Goal: every grade event, prompt injection, and export should let an analyst
reconstruct **both** the raw mastery picture and the calibrated grade picture,
and should make full-credit / enrichment states explicit.

## 1. Grade-policy snapshot (in every grade/report event payload)

```json
{
  "grade_policy": {
    "policy_id": "ranked-target-saturation-v1",
    "ranked_topic_weights": [55, 25, 13, 7],
    "ranked_full_credit_targets": [90, 82, 74, 62]
  }
}
```

Produced by `bot_engine.grade_policy_snapshot()` and injected by
`_record_grade_event` (already the mechanism today). Old events keep their old
snapshot; readers branch on `policy_id`.

## 2. Ranked credit state (grade event payload + prompt injection)

```json
{
  "ranked_credit_state": [
    {
      "topic_id": "T6",
      "raw_mastery": 90,
      "rank": 1,
      "target_for_full_credit": 90,
      "credit_completion": 1.0,
      "credit_contribution": 55,
      "grade_delta_to_target": 0,
      "status": "full_credit_satisfied"
    },
    {
      "topic_id": "T3",
      "raw_mastery": 82,
      "rank": 2,
      "target_for_full_credit": 82,
      "credit_completion": 1.0,
      "credit_contribution": 25,
      "grade_delta_to_target": 0,
      "status": "full_credit_satisfied"
    },
    {
      "topic_id": "T7",
      "raw_mastery": 78,
      "rank": 3,
      "target_for_full_credit": 74,
      "credit_completion": 1.0,
      "credit_contribution": 13,
      "grade_delta_to_target": 0,
      "status": "full_credit_satisfied"
    },
    {
      "topic_id": "T1",
      "raw_mastery": 74,
      "rank": 4,
      "target_for_full_credit": 62,
      "credit_completion": 1.0,
      "credit_contribution": 7,
      "grade_delta_to_target": 0,
      "status": "full_credit_satisfied"
    }
  ],
  "session_credit_status": "full_credit_reached"
}
```

(The teacher session `[90,82,78,74]` → all four slots satisfied → grade 100.)

A below-target row looks like:

```json
{
  "topic_id": "T4",
  "raw_mastery": 50,
  "rank": 3,
  "target_for_full_credit": 74,
  "credit_completion": 0.6757,
  "credit_contribution": 8.78,
  "grade_delta_to_target": 24,
  "status": "below_target"
}
```

A padded (unfilled) slot:

```json
{ "topic_id": null, "raw_mastery": 0, "rank": 4,
  "target_for_full_credit": 62, "credit_completion": 0.0,
  "credit_contribution": 0.0, "grade_delta_to_target": 62, "status": "below_target" }
```

## 3. Strategic guidance injected into the tutor prompt (per turn)

Inside `current_tutoring_state` (dynamic suffix, cache-safe):

```json
{
  "grade_impact_deltas": { "T6": 0, "T3": 0, "T7": 0, "T1": 0, "T4": 6 },
  "session_credit_status": "in_progress",
  "grade_relevant_next_move": "T4",
  "ranked_credit_state": [ ... as above ... ]
}
```

When full credit is reached:

```json
{
  "grade_impact_deltas": { "T6": 0, "T3": 0, "T7": 0, "T1": 0 },
  "session_credit_status": "full_credit_reached",
  "grade_relevant_next_move": null
}
```

Representation rules:
- `grade_impact_deltas` values are **calibrated** integer ΔGrade. Target-satisfied
  / raw-100 topics are `0`.
- `grade_relevant_next_move` is the topic id with the largest positive delta, or
  `null` when none remain.
- `session_credit_status ∈ {"in_progress", "full_credit_reached"}`.

## 4. How specific situations are represented in logs

| Situation | Representation |
|---|---|
| raw mastery | `best_mastery` in `session_state`; `raw_mastery` per `ranked_credit_state` row |
| calibrated grade | `grade` on the grade event + `current_grade`; equals `floor(Σ credit_contribution)` |
| grade deltas | `grade_impact_deltas` (calibrated) in the dialogue prompt + dialogue audit `state_before` |
| topics past target | `ranked_credit_state[*].status == "full_credit_satisfied"` while `raw_mastery > target` |
| full credit reached | `session_credit_status == "full_credit_reached"`, all deltas 0, `grade == 100` |
| optional enrichment mode | tutor private artifact: `grade_relevant == false` / source `optional_enrichment_after_full_credit` (if schema extended); plus `grade_relevant_next_move == null` in the turn's `state_before` audit |

## 5. Private artifact log (`private_artifact_logs`)

- Keep the existing schema. The tutor's per-turn move rationale continues to
  cite `strongest_alternative_direction.source =
  "grade_impact_deltas_or_backend_strategic_guidance"`.
- Optional additive schema field (see `04` §7): a marker that a move was
  optional enrichment after full credit, so reviewers can separate grade-driven
  probing from post-credit exploration. Must remain non-required for
  backward-compatible validation of older logs.

## 6. Dialogue turn audit (`dialogue_turn_audits`)

- `state_before_json` already captures the injected `current_tutoring_state`,
  which now carries `grade_impact_deltas` (calibrated), `session_credit_status`,
  `grade_relevant_next_move`, and `ranked_credit_state`. No model change; the
  richer state flows in automatically.

## 7. Exports

- `scripts/export_session_package.py` and
  `scripts/export_investigation_package.py` serialize `grade_events.payload_json`
  verbatim → the new policy/targets/credit-state fields appear automatically.
- Update each script's README/manifest text to mention `ranked_full_credit_targets`,
  `ranked_credit_state`, and `session_credit_status` so downstream analysts know
  to read them. (Text-only; no logic change.)

## 8. Backward-compatibility for readers

- Any log/export reader must treat `ranked_full_credit_targets`,
  `ranked_credit_state`, and `session_credit_status` as **optional** (absent on
  pre-change events). Branch on `grade_policy.policy_id`.
