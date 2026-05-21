# Grade Saturation Fix — Handoff Document

## Context

This project is a lecture tutoring bot at `/srv/lecture-bot`. The tutor uses OpenAI to run
conversations with students, then records mastery evidence that the backend uses to compute
a grade. The grading formula is in `app/bot_engine.py` lines 16 and 467–475:

```python
_GRADE_WEIGHTS = [55, 25, 13, 4, 3]
# Sort all topic mastery scores descending, take top 5 (pad with 0s), apply weights, floor
```

## The problem

The tutor has a grade saturation bug: it treats a strong student answer as a reason to close
a topic and move on, rather than as a reason to ask something harder. In session 64eb8bc1,
a 10-stage analysis confirmed this is an **arbitration failure** — the tutor recognises strong
performance but its stopping criterion is "evidence is adequate at current difficulty," not
"no harder question would yield more." The grade was 78; 85–92 was achievable.

Full analysis: `/srv/lecture-bot/exports/investigation_export_lecture_06_20260521T171829/analysis_outputs/`

## The fix (agreed, not yet implemented)

Add two things to `/srv/lecture-bot/docs/tutor_specification.md`:

### 1. New section C1.2 — after the existing C1.1

Insert after the line:
> "Consolidation is appropriate when no remaining move — breadth or depth — would meaningfully
> improve the characterization. This is the closure threshold, not 'broadly covered.'"

Insert this section:

---

### C1.2 Move selection by expected grade impact

At each turn, before deciding the next move, the tutor computes the expected grade impact of
probing each sampled topic. This is an entirely internal calculation — it does not appear in
`assistant_message` and must not influence tone or word choice in ways that signal topic
priority to the student.

**Grading formula (internal use only):** Sort all sampled topic mastery scores descending.
Take the top five, padding unscored topics with 0. Apply weights [55, 25, 13, 4, 3] to
positions 1–5. Floor the result. Topics ranked 6th or below contribute nothing to the grade
regardless of their scores.

**Calculation — for every sampled topic:**

1. Take the topic's current `best_mastery` score (0 if unscored).
2. Estimate `score_if_success`: the score the student would plausibly reach if the next probe
   on this topic succeeds, using the midpoint of the next calibration tier:
   - Currently 0 (unscored) → 45
   - Currently weak (1–30) → 42
   - Currently developing (31–54) → 62
   - Currently solid (55–71) → 77
   - Currently strong (72–87) → 92
   - Currently robust (88–100) → no meaningful gain (ΔGrade = 0)
3. Replace this topic's score with `score_if_success`, re-sort all topic scores, apply the
   weights, floor.
4. ΔGrade = projected_grade − current_grade.

**Selection rule:** Choose the topic with the highest ΔGrade. If two topics tie, prefer the
unscored one (breadth tiebreak). If all ΔGrade values are 0 or negligible, consolidate.

Once the topic is selected, determine the appropriate C2 mode: a basic probe if the topic is
unscored, an escalated probe if it is already at strong or robust evidence, or the
pedagogically appropriate probe type for intermediate evidence. The calculation drove the
choice; pedagogy drives the delivery.

---

### 2. New C5 self-verification item 10

Append to the existing C5 list (after item 9):

> 10. The intended `assistant_message` does not mention topic weighting, predicted grade
>     impact, or grading policy, even implicitly. If it does, rewrite before outputting.

## Steps to complete

1. Edit `docs/tutor_specification.md` — add C1.2 and C5.10 as above.
2. Insert a new archive record for the revised spec (new version_key, not in-place edit).
   Previous practice: use a date-based version_key like `2026-05-21_v2` or similar.
3. Run the generator: feed the revised spec + both contracts through
   `prompts/tutor_generator_prompt.md` to produce a new runtime prompt and artifact schema.
   The generator prompt explains how to do this.
4. Insert new archive records for the generated tutor_prompt and tutor_artifact_schema.
5. Activate the new tutor_prompt. IMPORTANT: also update active flags on the linked
   tutor_spec and tutor_artifact_schema records — this was missed last time and caused
   silent stale-document bugs.
6. Restart the student service: `sudo systemctl restart lecture-bot.service`
7. Run a test session. Verify in `dialogue_turn_audits` that `challenge_level` > 1 appears
   on at least one turn for a student who answers well, and that grade exceeds 78 for a
   strong student.

## Other pending items (separate from this fix)

- The 30-minute session timeout change (already in `app/config.py`) needs a service restart.
- The 250 MB upload limit change (already in `app/admin_main.py`) needs admin service restart:
  `sudo systemctl restart lecture-bot-admin.service`
- The JSONDecodeError permanent fix (use `json.JSONDecoder().raw_decode(raw)` instead of
  `json.loads(raw)` in `app/bot_engine.py` around line 233) is proposed but not yet applied.

## Key files

- `docs/tutor_specification.md` — edit target
- `docs/backend_tutor_contract.md` — reference (mastery fields, grading semantics)
- `prompts/tutor_generator_prompt.md` — generator prompt (run this to produce runtime prompt)
- `prompts/tutor_prompt.md` — current active runtime prompt (will be replaced)
- `prompts/tutor_prompt_private_artifact_schema.json` — current artifact schema (will be replaced)
- `app/bot_engine.py` lines 16, 467–475 — source of truth for the grading formula
- `data/lecture_bot.db` — SQLite database; archive_documents table holds all versioned docs
- `exports/investigation_export_lecture_06_20260521T171829/analysis_outputs/` — full analysis
