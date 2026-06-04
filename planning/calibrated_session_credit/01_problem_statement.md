# 01 — Problem statement

## The calibration problem

The current student-facing grade is a **raw weighted mastery** sum over the top
four ranked topics:

```
grade = floor( 55·s1/100 + 25·s2/100 + 13·s3/100 + 7·s4/100 )
```

where `s1 ≥ s2 ≥ s3 ≥ s4` are the four highest raw topic-mastery scores.

Because every weight multiplies `raw_score/100` directly, **a topic only
contributes its full weight when its raw mastery is 100.** Raw mastery of 100
means "near-complete, flexible, precise, independent command, possibly extending
beyond the lecture's examples" (`grading_policy.md`, ladder step 8). That is an
unreasonably high bar to require on *every* slot for full session credit.

### Teacher-session example

A full 30-minute serious, expert-level session ended with raw topic mastery
roughly:

```
T6 = 90   (best)
T3 = 82
T7 = 78
T1 = 74
T4 = 68
```

The top four ranked scores are `[90, 82, 78, 74]`. Under the current formula:

```
floor(55·0.90 + 25·0.82 + 13·0.78 + 7·0.74)
  = floor(49.5 + 20.5 + 10.14 + 5.18)
  = floor(85.32) = 85
```

**A strong, knowledgeable, 30-minute session scores 85.** Verified against the
live code (`bot_engine._weighted_grade_from_scores`).

This is pedagogically undesirable. To reach 100 the student would have to push
*every* one of four topics to a raw mastery of 100 — i.e. exhaustively polish
every nuance of four separate topics. That is not what "full session credit"
should mean.

## Desired pedagogical meaning

> A serious, knowledgeable student should be able to reach full session credit
> efficiently — around 15 minutes — through dense, independent, transferable
> answers. Full session credit should **not** require exhaustive coverage,
> perfect phrasing, or polishing every possible nuance.

We want to **preserve raw topic mastery** (0–100) for diagnosis, evidence
tracking, feedback, and reporting, but compute the **student-facing grade**
against calibrated *full-credit targets* that are reachable with strong-but-not-
perfect answers.

## Four distinct quantities (keep these separate)

The current system conflates "raw mastery" with "grade contribution." The new
design must keep four quantities clearly distinct:

| Quantity | Range | Meaning | Owner |
|---|---|---|---|
| **raw topic mastery** | 0–100 | diagnostic depth of understanding for a topic | backend (`best_mastery`) |
| **credit completion** | 0–1 | internal completion toward the ranked target = `min(raw/target, 1)` | backend (derived) |
| **credit contribution** | 0–rank_weight | a topic's contribution to the grade = `weight · completion` | backend (derived) |
| **student-facing grade** | 0–100 | session credit = `floor(Σ contributions)` | backend (`current_grade`) |

Do **not** invent a separate "calibrated topic grade out of 100." If a
topic-level percentage is ever shown, label it explicitly as *credit completion*
(toward that topic's ranked target), never as a topic grade.

## Grade-relevant opportunity cost vs. raw improvement

The tutor currently chooses its next move using `grade_impact_deltas` — the raw
weighted-grade gain from a successful next probe. Under the new model:

- Opportunity-cost / "what to probe next" decisions must be based on the
  **calibrated** grade impact, not raw mastery.
- `grade_impact_deltas` is the **actual calibrated trial difference** (with full
  re-ranking). A topic that already satisfies its current ranked target will
  *usually* have delta 0 — but not always: if improving it would change the
  ranking and raise the session grade, the delta is a real positive number and
  must be reported truthfully. The backend never zeroes a real delta; the
  *tutor prompt* is where polishing already-satisfied topics is discouraged.
- Once the whole session has reached full calibrated credit (grade 100) and no
  re-ranking can raise it, the backend signals
  `session_credit_status = "full_credit_reached"` and
  `grade_relevant_next_move = null`.

## Optional enrichment after full credit

After full credit is reached, the tutor must stop treating further probing as
compulsory grading work. It may still: answer student questions, offer optional
enrichment, help a weak-but-non-grade-critical point, or invite report
generation. It must not claim the session is "complete" in a lifecycle sense
(that remains backend-owned), but it is released from grade-driven probing.
