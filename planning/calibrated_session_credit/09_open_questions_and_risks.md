# 09 — Open questions and risks

## Open questions (need a human/instructor decision)

**Q1. Is `[90, 82, 74, 62]` the right calibration?**
These targets make the teacher session (`[90,82,78,74]`) land exactly at 100.
They are reverse-ordered (lower ranks need less), which makes breadth cheaper.
Is full credit at *four strong topics* the intended bar, or should rank-1 require
less than 90? Recommend confirming with one or two more real sessions before
locking.

**Q2. Should targets be configurable per lecture?**
Currently weights are global constants. Targets could live in `lecture_config`
like `tutor_prompt_template` does. Pro: per-lecture difficulty tuning. Con: more
surface area, harder cross-lecture comparison, more migration. Recommend
**global constant first**, design the helper to accept targets as a parameter so
per-lecture config is a later drop-in.

**Q3. Should students see "full credit reached"?**
The tutor can say it conversationally, and a UI badge is possible. Risk: students
stop early and miss enrichment, or game toward four topics only. Recommend tutor
may mention it; defer any explicit UI badge to a separate decision.

**Q4. Should reports mention raw mastery below 100?**
If yes, frame strictly as optional enrichment ("you could go deeper on X"),
never as a grade gap. Decision: include as optional enrichment only, or omit
entirely? Recommend optional-enrichment framing.

**Q5. Should the tutor keep asking optional enrichment questions after full
credit?**
Or go fully student-led (only answer what's asked)? Recommend: offer, don't
push; let the student opt in. Encode in `tutor_specification.md`.

**Q6. Does this change instructor expectations for Moodle submission?**
Grades will rise for strong sessions. Confirm the instructor wants the higher
distribution and that any rubric/marks mapping in Moodle still makes sense.

**Q7. Should analytics distinguish raw mastery from grade credit?**
Strongly recommend yes — `ranked_credit_state` already separates them. Confirm
downstream dashboards/scripts read credit vs raw correctly.

**Q8. Ranking method: raw-descending vs credit-maximizing assignment?**
We assign highest raw score → highest weight (matches current code). This is not
always the assignment that maximizes calibrated grade. Worked example: raw
`A=95, B=80`, targets `90, 82`. Raw-descending: `min(95/90)·55 + min(80/82)·25 =
55 + 24.39 = 79`. Swapped: `min(95/82)·25 + min(80/90)·55 = 25 + 48.9 = 73.9`.
Here raw-descending is also the max. In general, because both weights and
targets are descending, assigning the strongest topic to the strongest
weight/easiest-relative target is near-optimal, and ties are rare. Recommend
keeping raw-descending for simplicity and monotonicity; note the edge case.

## Risks

**R1. Brittle tests.** Many tests assert raw-weighted grade numbers for
non-saturated sessions. These will fail and must be recomputed (see `07` K).
Mitigation: the test sweep is an explicit implementation step; the all-100 cases
are unchanged.

**R2. Prompt/spec snapshot tests.** Editing contracts/prompts may break
hash/snapshot assertions and the archive identity check
(`session_manager._resolve_prompt_document_id`). Mitigation: re-archive the
updated prompt and update expected SHAs; verify the active-doc / sha match.

**R3. Mid-session policy switch.** A session graded under both policies will see
grades only rise (monotone `max`), which is benign, but the session's grade
events mix `policy_id`s. Mitigation: self-describing snapshots; document it.

**R4. Already-submitted grades.** If any session's old (lower) grade was already
submitted to Moodle, do not retroactively change it. Mitigation: no historical
recompute; new policy applies to new grade events only.

**R5. Report wording drift.** The LLM report could still imply "you must improve
X." Mitigation: explicit report-prompt instruction + a manual validation step.

**R6. Tutor over-stops at full credit.** If the prompt over-emphasizes "no
grade-relevant move," the tutor might disengage prematurely. Mitigation: keep the
no-lifecycle-completion rule; frame as "released from compulsory probing, still
available for enrichment."

**R7. Calibrated deltas hide breadth incentives.** Once four topics are near
target, opening a fifth topic yields 0 grade delta, so the tutor won't chase it.
That is intended (efficiency), but confirm it matches pedagogy (we don't want to
*discourage* a curious student — enrichment language covers this).

**R8. Floating-point in payloads.** `credit_completion`/`credit_contribution` are
floats; round in payloads to keep JSON stable and comparisons clean. Grade itself
is an int via `floor`.

**R9. Moodle tolerance.** The import cross-check compares report grade vs
`current_grade` within a tolerance; both now derive from the same calibrated
computation, so they should match exactly — but verify the float/int formatting
path doesn't introduce a sub-tolerance mismatch.
