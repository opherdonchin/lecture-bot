# 02 — Proposed behavior

## Policy identity

```
policy_id  = "ranked-target-saturation-v1"
weights    = [55, 25, 13, 7]      # unchanged ranked cross-topic weights
targets    = [90, 82, 74, 62]     # NEW: full-credit target per ranked slot
```

## Core formula

Given the set of raw topic-mastery scores for a session:

```python
def compute_calibrated_grade(scores: list[int]) -> int:
    ranked  = sorted(scores, reverse=True)[:4]   # top four by raw mastery
    padded  = (ranked + [0, 0, 0, 0])[:4]        # pad with zeros
    contributions = [
        weight * min(raw / target, 1.0)
        for weight, raw, target in zip(weights, padded, targets)
    ]
    return floor(sum(contributions))             # naturally capped at 100
```

Equivalent per-slot definitions:

```
credit_completion_i   = min(raw_i / target_i, 1.0)     # 0..1
credit_contribution_i = weight_i * credit_completion_i  # 0..weight_i
grade                 = floor( Σ credit_contribution_i ) # 0..100
```

## Behavior specification

- **Ranking**: sort raw topic mastery descending; assign the highest raw score
  to rank 1 (weight 55, target 90), next to rank 2 (25, 82), etc. Ranking is by
  **raw mastery**, matching current behavior. (We deliberately keep the simple
  raw-descending assignment rather than searching for the credit-maximizing
  assignment; see `09_open_questions_and_risks.md` for why this is acceptable.)
- **Padding**: if fewer than four topics have positive mastery, pad the missing
  ranked slots with raw score 0 (→ 0 credit).
- **Caps**:
  - Each slot's `credit_completion` is capped at 1.0.
  - Each slot's `credit_contribution` is therefore capped at its `weight`.
  - The session grade is the floor of the sum, capped at 100 (the weights sum to
    exactly 100, so the cap is automatic).
- **Raw mastery above target**: allowed and preserved. Raw mastery may exceed its
  ranked target and may reach 100. Holding the ranking fixed, once a slot's raw
  mastery ≥ its target, additional raw mastery on that slot does not increase the
  student-facing grade. (Edge case: raising a topic can still lift the grade if it
  *changes the ranking* such that a previously below-target slot becomes
  satisfied — see the re-ranking counterexample under "Calibrated grade deltas".)
  Extra mastery always matters for diagnosis, evidence notes, and reports.
- **Full-credit session state**: when `grade == 100` (every occupied ranked slot
  has reached its target), the session is at **full calibrated credit**.
  Backend strategic guidance reports `session_credit_status =
  "full_credit_reached"` and `grade_relevant_next_move = null`.

## Worked test vectors (verified against a reference implementation)

| Raw scores (top 4 after ranking) | New grade | Note |
|---|---|---|
| `[90, 82, 74, 62]` | **100** | exactly the targets → full credit |
| `[90, 82, 78, 74]` | **100** | the teacher session (was 85) |
| `[90]` | **55** | one strong topic = full rank-1 credit |
| `[90, 82]` | **80** | two strong topics |
| `[90, 82, 74]` | **93** | three strong topics |
| `[100, 100, 100, 100]` | **100** | caps hold |
| `[0, 0, 0, 0]` | **0** | empty |
| raw above target, e.g. `[95, 90, 80, 70]` | **100** | excess raw does not exceed weight |

## Calibrated grade deltas (strategic guidance)

The tutor's move-selection signal changes from "raw weighted grade gain" to
"**calibrated** grade gain":

- For each sampled topic, project its raw mastery to the value it would reach if
  the next probe succeeds (reuse the existing concave projection ladder), then
  compute the **calibrated** grade with that topic improved, holding other
  topics fixed. The delta is `max(0, calibrated_grade(trial) − calibrated_grade(current))`.
- **The delta is always the actual calibrated trial difference. Do NOT force a
  target-satisfied topic's delta to zero.** In most ordinary cases a topic that
  already meets its current ranked target will have delta 0, but if a successful
  probe would change the ranking, the delta can be a small positive number and
  must be reported truthfully.
  - Re-ranking counterexample (verified): current raw `[89, 82, 74, 62]`,
    targets `[90, 82, 74, 62]` → grade **99**. The rank-2 topic (raw 82) already
    satisfies the rank-2 target, but projecting it to 92 makes it the new rank-1
    topic: raw set `[92, 89, 74, 62]` → grade **100**, so its delta is **+1**.
- When all occupied ranked slots are satisfied **and no re-ranking can raise the
  grade** (grade 100), every grade-relevant delta is 0 and the session is
  `full_credit_reached`.

Because a topic's rank depends on the *other* topics' raw scores, the delta
computation must rank-and-evaluate the full calibrated grade for each trial
projection (same structure as today, just with the calibrated grade function).
The anti-nitpicking goal is achieved in the *tutor prompt* (discourage polishing
a satisfied topic unless the backend still reports a positive calibrated delta),
not by zeroing real deltas in the backend.

## Post-full-credit tutor behavior

After `session_credit_status == "full_credit_reached"`:

- The tutor stops treating further probing as compulsory grading work.
- It may offer optional enrichment, answer questions, help with a weak but
  non-grade-critical point, or invite report generation.
- It must **not** claim lifecycle completion ("we're done", "the session is
  over") — lifecycle/timeout closure remains backend-owned.
- It may use language like "you've reached full session credit; we can keep
  exploring if you'd like, or you can generate your report."

## Student-facing explanation and report behavior

- Explanations and reports continue to be written by the LLM with the backend's
  authoritative number injected.
- When raw mastery on some topics is below 100 but the session reached full
  credit, the report must **not** imply the student must keep going for the
  grade. It should say full session credit was reached and may note optional
  areas for deeper mastery (framed as enrichment, not as grade gaps).
- No topic-level "X/100 grade" is shown. If any topic-level figure appears, it is
  labeled *credit completion toward target*.

## Invariants preserved

- Raw `best_mastery` (0–100, monotone per topic) is unchanged in meaning and
  storage.
- `current_grade` remains monotone non-decreasing within a session.
- The grade is computed by Python, never by the model.
- Report/grade consistency (the Moodle cross-check) is preserved because both
  derive from the same authoritative computation.
