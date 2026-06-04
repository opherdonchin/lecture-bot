# 04 — Contract and specification revision plan

Guiding principle, preserved throughout: **the backend owns grading mechanics;
the tutor owns pedagogical behavior.** The calibrated targets, the
`min(raw/target,1)` rule, saturation, and `session_credit_status` are all
backend-owned. The tutor only *reads* the resulting strategic guidance and
decides how to teach.

For each document below: the current assumption that must change, the proposed
change, whether it is **normative** (changes required behavior) or
**explanatory** (clarifies without changing required behavior), and why it is
required for consistency.

---

## 1. `docs/backend_tutor_contract.md` (runtime contract)

### §2 — `grade_impact_deltas` definition
- **Current assumption (must change)**: "a JSON object mapping each sampled topic
  ID to the integer ΔGrade the tutor would gain if the next probe on that topic
  succeeds. The backend computes this using the same fixed ranked-topic grading
  formula and calibration tiers used by `compute_weighted_grade`."
- **Proposed change (normative)**: redefine ΔGrade as the **calibrated**
  student-facing grade gain under policy `ranked-target-saturation-v1`,
  computed as the actual trial difference (current calibrated grade vs.
  calibrated grade after a projected successful probe, with full re-ranking).
  Add:
  > A topic that already satisfies its current ranked target usually has a
  > grade-relevant delta of 0, but the delta is always the true calibrated trial
  > difference and may be a small positive number when a successful probe would
  > change the ranking and raise the session grade. The backend does not zero
  > real deltas. The backend also supplies `session_credit_status`
  > (`"in_progress"` | `"full_credit_reached"`) and `grade_relevant_next_move`
  > (a topic id or `null`). When `session_credit_status == "full_credit_reached"`
  > and no re-ranking can raise the grade, all deltas are 0 and
  > `grade_relevant_next_move` is `null`.
- **Recommended tutor-facing wording** (for `tutor_prompt.md` /
  `tutor_specification.md`): "A topic already satisfying its current ranked
  credit target should usually not be polished unless the backend still reports
  positive calibrated grade impact or there is a clear pedagogical reason."
- **Why**: the tutor's opportunity-cost baseline must be a truthful calibrated
  signal. Discouraging nitpicking belongs in the prompt; the backend must not
  hide a real positive grade delta that exists because of re-ranking.

### §2 — new strategic-guidance fields
- **Proposed addition (normative)**: document the optional
  `ranked_credit_state` array and the `session_credit_status` /
  `grade_relevant_next_move` fields as backend-computed inputs (shapes in
  `06_logging_and_diagnostics_plan.md`). State they are read-only to the tutor.

### §4 — state ownership
- **Current**: lists `best_mastery`, `current_grade`, `grade_impact_deltas` as
  backend-owned read-only.
- **Proposed change (normative, additive)**: add `session_credit_status`,
  `ranked_credit_state`, `grade_relevant_next_move` to the backend-owned list.
  `best_mastery` semantics unchanged (still raw 0–100, monotone per topic).

---

## 2. `docs/grading_policy.md` (grading working note)

- **Current assumption (must change)**: the cross-topic table's "Max cumulative"
  column and the framing imply a slot contributes its full weight only at raw
  mastery 100.
- **Proposed change (normative for the policy, explanatory for the tutor)**:
  - Add a new top section "Calibrated session-credit grading
    (`ranked-target-saturation-v1`)" defining `weights = [55,25,13,7]`,
    `targets = [90,82,74,62]`, and `grade = floor(Σ weight·min(raw/target,1))`.
  - Introduce the four-quantity vocabulary (raw mastery / credit completion /
    credit contribution / student-facing grade).
  - State explicitly that raw mastery is retained 0–100 for diagnosis and may
    exceed targets, and that the within-topic concave ladder still governs raw
    mastery and the projection used for grade deltas.
  - Mark the old raw-weighted interpretation as superseded for the
    student-facing grade (kept only as historical context).
- **Why**: this is the canonical calibration note; leaving it raw-weighted would
  contradict the implementation and confuse future prompt work.

---

## 3. `docs/tutor_specification.md` (pedagogy spec)

- **Current assumption (clarify)**: backend strategic guidance is treated as the
  opportunity-cost baseline; the tutor never claims grade saturation or
  completion.
- **Proposed change (mostly explanatory, one normative addition)**:
  - Clarify that strategic guidance is now **calibrated** grade impact.
  - **Normative addition**: define post-full-credit behavior. When backend
    guidance reports no grade-relevant next move, the tutor is released from
    compulsory grade-driven probing and may offer optional enrichment, answer
    questions, help a weak non-grade-critical point, or invite report
    generation — **without** claiming lifecycle completion (still backend-owned).
  - Keep the existing rule that the tutor must not independently declare
    "grade saturation" — but note that *acting on backend-reported full credit*
    is permitted and is not a self-claim.
- **Why**: without this, a tutor reaching full credit would either keep probing
  pointlessly or risk a forbidden completion claim.

---

## 4. `docs/tutor_specification_contract.md` (spec contract)

- **Current**: defines how generated specs must preserve evaluative shape (the
  mastery scale).
- **Proposed change (inspect; explanatory note only)**: confirm the mastery
  scale (raw 0–100) is unchanged, so the generator's preservation rule still
  holds. Add a one-line note that grade calibration is backend-owned and outside
  the spec's evaluative shape. No normative change expected.

---

## 5. `prompts/tutor_prompt.md` (runtime tutor prompt)

- **Current assumption (must change)**: "grade_impact_deltas … the integer ΔGrade
  the tutor would gain if the next probe on that topic succeeds."
- **Proposed change (normative)**:
  - Reword to "calibrated ΔGrade (student-facing session credit)."
  - Add a short block: when backend guidance reports `session_credit_status =
    full_credit_reached` or `grade_relevant_next_move = null`, stop treating
    further probing as required for the grade; optional enrichment, questions, or
    report generation are appropriate; do not claim the session is complete.
  - Keep: do not recompute deltas, do not expose ranked-slot/target arithmetic,
    do not claim official grade or completion.
- **Why**: the live prompt must match the contract and spec.

---

## 6. `prompts/tutor_generator_prompt.md` (prompt generator)

- **Current**: generates runtime tutor prompts from spec + contracts.
- **Proposed change (normative-by-propagation)**: update any embedded
  description of grade deltas / saturation so regenerated prompts inherit the
  calibrated wording and the full-credit behavior block. Ensure it still routes
  grading mechanics to the backend.
- **Why**: prevents the next regeneration from reintroducing raw-weighted wording.

---

## 7. `prompts/tutor_prompt_private_artifact_schema.json` (per-turn artifact)

- **Current**: `strongest_alternative_direction.source` enum includes
  `"grade_impact_deltas_or_backend_strategic_guidance"`.
- **Proposed change (additive, optional)**: keep the enum value (it still names
  the same input). Optionally add an enrichment indicator so post-full-credit
  optional moves are auditable (e.g. a boolean `grade_relevant` on the move, or a
  new `source` value `"optional_enrichment_after_full_credit"`). Keep
  backward-compatible (don't make new fields required for old sessions' logs).
- **Why**: lets diagnostics distinguish grade-driven probing from optional
  enrichment after full credit.

---

## 8. Analysis prompts/handoffs (`grade_saturation_analysis_prompt.md`,
`docs/grade_saturation_handoff.md`)

- **Proposed change (explanatory)**: redefine "grade saturation" as **calibrated
  full credit** (grade 100 under the new policy), so offline analysis of sessions
  (including the packaged teacher session) interprets saturation consistently.

---

## Consistency matrix (who states what)

| Concept | Owner doc (normative) | Restated in |
|---|---|---|
| weights `[55,25,13,7]`, targets `[90,82,74,62]`, formula | `grading_policy.md` | `backend_tutor_contract.md` §2 |
| calibrated ΔGrade (true trial diff; not zeroed for satisfied slots) | `backend_tutor_contract.md` §2 | `tutor_prompt.md`, `tutor_specification.md` |
| `session_credit_status` / `grade_relevant_next_move` | `backend_tutor_contract.md` §2/§4 | `tutor_prompt.md`, `tutor_specification.md` |
| post-full-credit tutor behavior | `tutor_specification.md` | `tutor_prompt.md` |
| raw mastery retained for diagnosis | `grading_policy.md` | `backend_tutor_contract.md` §4 |
