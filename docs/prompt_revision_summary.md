# Prompt Revision Summary

## What Changed

- Reworked the tutor runtime contract in [app/bot_engine.py](/home/opher/Repositories/lecture-bot/app/bot_engine.py:111) and [prompts/dialogue_system_prompt.md](/home/opher/Repositories/lecture-bot/prompts/dialogue_system_prompt.md:1):
  - added a private `decision_trace`
  - centered the tutor on eliciting the strongest student-owned evidence with the least revealing productive move
  - made each turn seek exactly one new content contribution
  - added guardrails against bare topic-ID leakage, vague one-sentence prompts, and unreliable time claims

- Rewrote the tutor-generation prompt in [prompts/tutor_generation_prompt.md](/home/opher/Repositories/lecture-bot/prompts/tutor_generation_prompt.md:1) so it now targets:
  - compact hidden turn procedure
  - candidate-move comparison
  - bracketed grading awareness
  - richer move-family guidance

- Tightened runtime context assembly in [app/bot_engine.py](/home/opher/Repositories/lecture-bot/app/bot_engine.py:258) and [lectures/config.json](/home/opher/Repositories/lecture-bot/lectures/config.json:1):
  - removed raw notebook from runtime tutor inputs
  - kept runtime context focused on slides, handout, minutes, and optional bot notes
  - reduced dialogue/grading context budgets in [app/config.py](/home/opher/Repositories/lecture-bot/app/config.py:13)

- Aligned session state and backend behavior in [app/session_manager.py](/home/opher/Repositories/lecture-bot/app/session_manager.py:10) and [app/main.py](/home/opher/Repositories/lecture-bot/app/main.py:146):
  - removed stale `confidence` and persisted `lecture_title` fields from session state
  - stored private decision traces server-side only
  - derived `topics_covered` from meaningful mastery footholds instead of raw model claims
  - stopped backend-appending vague timeout warnings after the tutor reply

- Tightened the minutes and rubric generation pipeline in [prompts/minutes_generation_prompt.md](/home/opher/Repositories/lecture-bot/prompts/minutes_generation_prompt.md:1) and [prompts/master_rubric_generation_prompt.md](/home/opher/Repositories/lecture-bot/prompts/master_rubric_generation_prompt.md:1):
  - minutes are now selective teaching notes instead of a long lecture reconstruction
  - rubric generation now treats minutes as selective notes and aims for broader 5-8 topic granularity

- Aligned exports with runtime behavior in [scripts/export_session_package.py](/home/opher/Repositories/lecture-bot/scripts/export_session_package.py:1):
  - export prompt rendering now reuses the same runtime prompt builder as the live app
  - notebook is no longer exported as part of the runtime lecture package

## Why

- The old prompt and runtime context were carrying too much internal grading machinery and too much raw context.
- The tutor needed a clearer internal decision process without becoming a brittle scripted ladder.
- Notebook content is still useful upstream for artifact generation, but it was too heavy for the live runtime tutor context.
- The previous contract allowed drift:
  - duplicated sampled topics
  - weakly justified `topics_covered`
  - stale state fields
  - export/runtime prompt mismatch

## Validation

- Automated:
  - `pixi run pytest -q`
  - result: `99 passed`

- Hand-crafted sanity checks:
  - verified runtime prompt omits notebook context
  - verified runtime prompt contains one-contribution and no-bare-topic-ID guardrails
  - verified sampled topic IDs are deduplicated before prompt injection
  - verified student-facing message sanitization replaces bare topic IDs
  - verified runtime lecture loader defaults now expose only `slides`, `handout`, and `minutes`
  - verified runtime exports no longer include notebook

## Important Unresolved Decisions

- Existing checked-in lecture rubrics still contain some older "banked" language because they are generated artifacts; the generation pipeline is updated, but old rubric outputs were not regenerated in this pass.
- `topics_covered` is now derived from a meaningful mastery foothold threshold. If the repo later needs a softer notion of "touched but not yet solid," that should be a separate field rather than overloading `topics_covered`.
- The multipart-question guardrail is prompt-enforced rather than validator-enforced. That was a deliberate choice to avoid brittle surface heuristics.

## Follow-up Adjustment

- Removed the experimental backend-side low-reveal message shaping from [app/bot_engine.py](/home/opher/Repositories/lecture-bot/app/bot_engine.py:390).
- Moved reveal-discipline back into the tutor prompt itself:
  - [prompts/dialogue_system_prompt.md](/home/opher/Repositories/lecture-bot/prompts/dialogue_system_prompt.md:1)
  - [prompts/tutor_generation_prompt.md](/home/opher/Repositories/lecture-bot/prompts/tutor_generation_prompt.md:1)

Why:

- The backend should stay simple.
- The tutor itself should draft, critique, and revise its own reply for productivity and minimal revealingness.
- The deeper problem was prompt permissiveness, not a lack of backend text surgery.

## English-Only Policy

- Added a backend English-only interaction policy using [app/language_policy.py](/home/opher/Repositories/lecture-bot/app/language_policy.py:1).
- Student messages are now checked before tutoring in [app/main.py](/home/opher/Repositories/lecture-bot/app/main.py:83):
  - non-English input gets an English refusal reply
  - the tutor model is not called
- Assistant text returned to the student is forced through English-only fallback handling in [app/bot_engine.py](/home/opher/Repositories/lecture-bot/app/bot_engine.py:390).
- Added `langdetect` to the project dependencies in [pixi.toml](/home/opher/Repositories/lecture-bot/pixi.toml:1).

Tradeoff:

- The detector strongly rejects clearly non-English scripts and longer detected non-English text.
- It intentionally allows short ASCII snippets so normal short English tutor turns like "Why sample" or "Next question" do not get rejected by accident.

## Follow-up On Decision Trace And Move Ordering

- Reworked the tutor prompt in [prompts/dialogue_system_prompt.md](/home/opher/Repositories/lecture-bot/prompts/dialogue_system_prompt.md:1) so the private `decision_trace` is now explicitly stepwise instead of a compressed retrospective summary.
- The runtime prompt now requires these sequential trace fields:
  - `step_1_student_model`
  - `step_2_evidence_target`
  - `step_3_move_candidates`
  - `step_4_choice`
  - `step_5_reply_draft`
  - `step_6_reply_check`
  - `step_7_revision`
  - `step_8_final_move`
- Clarified that later steps must use earlier steps and that the tutor should not collapse the trace into a neat after-the-fact summary.
- Added an explicit default move preference order:
  1. `contrastive_prompt`
  2. `narrowing_question`
  3. `partial_frame`
  4. `hint`
  5. `topic_switch`
  6. `concise_reformulation`
  7. `compact_explanation`
- Sharpened the move heuristics so they say more clearly when a move is genuinely useful and when it is only tidying wording, repeating a prior demand, or revealing too much.
- Mirrored those requirements in [prompts/tutor_generation_prompt.md](/home/opher/Repositories/lecture-bot/prompts/tutor_generation_prompt.md:1).
- Added prompt-level regression checks in [tests/test_bot_engine.py](/home/opher/Repositories/lecture-bot/tests/test_bot_engine.py:640).

Why:

- The earlier trace format made debugging too lossy because it summarized results instead of showing the staged decision process.
- The move list still looked too much like an unordered catalogue, which left room for shallow or implicit move preference.
