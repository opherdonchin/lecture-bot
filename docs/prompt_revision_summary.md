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
