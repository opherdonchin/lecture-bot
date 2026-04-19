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

## Backend Alignment For The New Trace Format

- Updated [app/bot_engine.py](/home/opher/Repositories/lecture-bot/app/bot_engine.py:424) so the backend now accepts the new stepwise `decision_trace` schema required by the prompt.
- The backend now stores stepwise trace fields such as:
  - `step_1_student_model`
  - `step_2_evidence_target`
  - `step_3_move_candidates`
  - `step_4_choice`
  - `step_5_reply_draft`
  - `step_6_reply_check`
  - `step_7_revision`
  - `step_8_final_move`
- Kept backward compatibility by upgrading older compact traces into the new stored stepwise shape instead of dropping them.
- Updated regression tests in:
  - [tests/test_bot_engine.py](/home/opher/Repositories/lecture-bot/tests/test_bot_engine.py:396)
  - [tests/test_send_message.py](/home/opher/Repositories/lecture-bot/tests/test_send_message.py:1)

Why:

- The prompt and backend had drifted apart.
- After restart, fresh sessions were still showing `private_decision_trace: null` because the backend sanitizer only recognized the old compact trace fields.

## Follow-up On Audit Rows And English Detection

- Added live `dialogue_turn_audits` writes through [app/main.py](/home/opher/Repositories/lecture-bot/app/main.py:83) and [app/models.py](/home/opher/Repositories/lecture-bot/app/models.py:1).
- Each normal tutor turn now records:
  - pre-turn state
  - recent messages
  - normalized user message shown to the model
  - rendered system prompt
  - lightweight topic/turn metadata
- Loosened English-only detection in [app/language_policy.py](/home/opher/Repositories/lecture-bot/app/language_policy.py:39) so short ASCII technical noun phrases are less likely to be falsely rejected.
- Added regression tests in:
  - [tests/test_bot_engine.py](/home/opher/Repositories/lecture-bot/tests/test_bot_engine.py:570)
  - [tests/test_send_message.py](/home/opher/Repositories/lecture-bot/tests/test_send_message.py:337)

Why:

- You wanted real audit rows for turn-level inspection rather than relying only on reconstructed context.
- The previous English-only threshold was too strict for scientific English phrases and created bad false positives in real sessions.

## Follow-up On Move Binding

- Strengthened [prompts/dialogue_system_prompt.md](/home/opher/Repositories/lecture-bot/prompts/dialogue_system_prompt.md:1) with a dedicated `Move binding` section.
- The runtime prompt now explicitly requires:
  - `step_5_reply_draft` must concretely instantiate `step_4_choice.chosen_move`
  - `assistant_message` must implement the same move family as the chosen move
  - `step_8_final_move` must describe the move actually realized by `assistant_message`
  - if faithful realization is not possible, the tutor must change the move rather than keep the move and emit a different question
- Mirrored those requirements in [prompts/tutor_generation_prompt.md](/home/opher/Repositories/lecture-bot/prompts/tutor_generation_prompt.md:1).
- Added prompt-level regression checks in [tests/test_bot_engine.py](/home/opher/Repositories/lecture-bot/tests/test_bot_engine.py:644).

Why:

- Replay tests on the exact bad MLE turn showed that mild prompt wording did not fix the problem.
- Stronger binding language did materially improve the emitted reply:
  - from generic repeated `What does MLE maximize?`
  - to explicit contrastive questions that actually matched the chosen move family.

## Follow-up On Final-Minutes Awareness

- Updated [app/main.py](/home/opher/Repositories/lecture-bot/app/main.py:161) so the runtime timing context now includes:
  - `minutes_elapsed`
  - `minutes_remaining`
  - `session_duration_minutes`
- Strengthened [prompts/dialogue_system_prompt.md](/home/opher/Repositories/lecture-bot/prompts/dialogue_system_prompt.md:465) so the tutor now:
  - uses elapsed/remaining/total duration when timing is reliable
  - briefly tells the student when the session has entered its final few minutes
  - pivots to one concrete final goal instead of acting like there is unlimited time
  - avoids repeating the warning after it has already been given once
- Mirrored that requirement in [prompts/tutor_generation_prompt.md](/home/opher/Repositories/lecture-bot/prompts/tutor_generation_prompt.md:254).
- Added regression checks in [tests/test_bot_engine.py](/home/opher/Repositories/lecture-bot/tests/test_bot_engine.py:644).

Why:

- In session `c6ac5b60-b9c0-4311-aebe-a6a77bdc4ac9`, the backend was already passing reliable timing data, but the prompt no longer instructed the tutor to actually warn the student when the session first entered the last five minutes.
- Adding session duration context gives the tutor better temporal grounding and makes the final stretch feel less abrupt.

## Follow-up On Timing In Grade And Report Outputs

- Extended [app/schema.py](/home/opher/Repositories/lecture-bot/app/schema.py:1) so both current-grade responses and final-report JSON now include:
  - `minutes_elapsed`
  - `minutes_remaining`
  - `session_duration_minutes`
- Added a shared timing helper in [app/main.py](/home/opher/Repositories/lecture-bot/app/main.py:249) and used it for:
  - `/get_grade`
  - `/generate_report`
  - timeout-triggered final reports
- Added regression tests in:
  - [tests/test_control_actions.py](/home/opher/Repositories/lecture-bot/tests/test_control_actions.py:169)
  - [tests/test_send_message.py](/home/opher/Repositories/lecture-bot/tests/test_send_message.py:224)

Why:

- You wanted elapsed and remaining session time visible in the current-grade and final-report outputs, not only inside the tutor prompt context.

## Follow-up On Topic Control

- Reworked [prompts/dialogue_system_prompt.md](/home/opher/Repositories/lecture-bot/prompts/dialogue_system_prompt.md:1) so the private `decision_trace` now begins with an explicit topic-control stage before student modeling and move choice.
- The trace now records:
  - current topic option
  - alternative topic option
  - separate grade/pedagogical/engagement values for each
  - a weighted current-versus-alternative comparison
  - the chosen topic for the turn
- Moved the student model and evidence target later in the sequence so they are explicitly written inside the chosen topic rather than implicitly inheriting the previous one.
- Updated [prompts/tutor_generation_prompt.md](/home/opher/Repositories/lecture-bot/prompts/tutor_generation_prompt.md:1) to require the same topic-control logic.
- Extended [app/bot_engine.py](/home/opher/Repositories/lecture-bot/app/bot_engine.py:430) to sanitize and store the richer trace shape, while still upgrading older stepwise and legacy traces into the new format.
- Updated [app/main.py](/home/opher/Repositories/lecture-bot/app/main.py:344) so audit metadata now prefers the chosen-topic trace step when extracting the turn’s target topic.
- Updated regression coverage in:
  - [tests/test_bot_engine.py](/home/opher/Repositories/lecture-bot/tests/test_bot_engine.py:396)
  - [tests/test_send_message.py](/home/opher/Repositories/lecture-bot/tests/test_send_message.py:1)

Why:

- We wanted topic choice to be as inspectable as reply construction.
- The previous trace made it too easy for the tutor to stay on the current topic by default and only expose move-level reasoning.
- Explicit current-versus-alternative topic comparison should make “stay or switch” decisions much easier to debug when a line gets over-polished.
