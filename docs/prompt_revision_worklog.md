# Prompt Revision Worklog

## Step 1 - Architecture Inspection

### What I inspected

- Tutor runtime prompt assembly in `app/bot_engine.py`
- Session/runtime flow and grading state updates in `app/main.py`
- Session state initialization in `app/session_manager.py`
- Lecture package loading in `app/lecture_loader.py`
- Admin lecture processing and package-building flow in `app/admin_workflow.py`
- Prompt templates in `prompts/dialogue_system_prompt.md`, `prompts/tutor_generation_prompt.md`, `prompts/minutes_generation_prompt.md`, and `prompts/master_rubric_generation_prompt.md`
- Export/package script in `scripts/export_session_package.py`
- Lecture defaults in `lectures/config.json`

### What I concluded

- Tutor inputs are assembled in `app/bot_engine.py` by combining:
  - the committed runtime prompt template
  - sampled topics and current tutoring state
  - the full rubric text
  - a concatenated lecture context built from `lecture_package["context_sections"]`
- Notebook currently enters the runtime tutor flow through lecture package `context_files` defaults in `lectures/config.json`, which are consumed by both `app/lecture_loader.py` and `scripts/export_session_package.py`.
- Minutes are generated manually through the admin app using `prompts/minutes_generation_prompt.md` and `app/admin_workflow.py`.
- The current tutor output/state contract is defined by:
  - runtime prompt instructions in `prompts/dialogue_system_prompt.md`
  - response parsing and validation in `app/bot_engine.generate_reply`
  - state sanitization in `app/bot_engine.sanitize_state_update`
  - persisted session state in `app/session_manager.py`
- There is currently no private decision-trace field in the tutor output contract. Adding one appears safe if it is:
  - parsed in the backend
  - stored only in session state
  - not surfaced in `SendMessageResponse`
- Current contract drift and coherence issues already visible:
  - runtime context still includes raw notebook even though it is a likely candidate for removal
  - exports still assume notebook is part of the tutor package
  - sampled topics can contain duplicates if upstream topic defs repeat
  - `topics_covered` can drift from actual evidence because it is model-reported and merged cumulatively
  - vague time-remaining text is appended in the backend even when the tutor already handled closeout

### What I changed

- Created this worklog to record each major step and keep the revision inspectable.

### Unresolved choices

- Whether the private decision trace should be stored as a top-level session-state field or nested under a dedicated private key.
- Whether `topics_covered` should remain part of tutor-managed state or become backend-derived from evidence-bearing mastery only.
- Whether the admin app should still process notebooks for rubric/minutes generation while excluding them from the runtime tutor package. Current expectation: yes.

## Step 2 - Tutor Contract And Runtime Assembly

### What I inspected

- `app/bot_engine.generate_reply`
- `app/bot_engine.build_dialogue_system_prompt`
- `app/bot_engine.sanitize_state_update`
- `app/session_manager.build_initial_state`
- `app/main.send_message`

### What I concluded

- The tutor prompt and backend parser needed to move together; changing only the prompt would have left contract drift.
- A private decision trace can be added safely as a top-level model output and stored privately in session state.
- The runtime state had stale fields (`confidence`, duplicated `lecture_title`) that did not materially help tutoring decisions.
- Bare topic-ID leakage should be guarded both in prompt instructions and in backend sanitization.

### What I changed

- Added private `decision_trace` support to the tutor output contract.
- Added backend sanitization and persistence for `private_decision_trace`.
- Removed stale runtime state fields `confidence` and persisted `lecture_title`.
- Deduplicated sampled topic IDs before prompt injection and session initialization.
- Added student-facing message sanitization to replace bare topic IDs with labels.
- Changed `topics_covered` handling to be derived from meaningful mastery footholds rather than trusting raw model claims.
- Stopped backend appending a generic time-warning sentence after the tutor reply; timing is now passed as reliable context and left to prompt-guided behavior.

### Unresolved choices

- `topics_covered` is now mastery-threshold-derived. If later analytics need a softer notion of "touched but not yet solid," that should likely be a separate field rather than overloading `topics_covered`.

## Step 3 - Tutor Prompt Revision

### What I inspected

- `prompts/dialogue_system_prompt.md`
- `prompts/tutor_generation_prompt.md`

### What I concluded

- The old runtime prompt contained too much grading geometry and too little explicit structure for choosing the next move.
- The tutor needed a clearer governing objective and a compact hidden turn procedure.
- The move repertoire needed richer operational guidance, especially around revealingness and the one-sentence move.

### What I changed

- Rewrote the runtime tutor prompt around the objective:
  - strongest student-owned evidence
  - least revealing productive intervention
- Added a compact hidden six-step turn procedure and required `decision_trace`.
- Reworked move guidance by family:
  - what the move is for
  - when it fits
  - when it is a bad fit
  - how revealing it is
  - what evidence it tends to elicit
- Added explicit guardrails for:
  - one new content contribution per turn
  - no bare topic IDs in student-facing replies
  - no vague one-sentence requests
  - no time claims without reliable timing data
- Rewrote the tutor-generation prompt to target the new runtime prompt shape instead of the older flatter move list.

### Unresolved choices

- The new decision trace is intentionally compact. If later debugging needs more granularity, expand the trace cautiously to avoid turning it into verbose reasoning text.

## Step 4 - Grading Awareness Bracketed Better

### What I inspected

- Runtime prompt grading sections
- Session state fields injected into the runtime prompt
- Grade snapshot wording in `app/main.py`

### What I concluded

- Grading still needs to guide deepen-versus-broaden decisions, but raw score salience should be reduced.
- The runtime prompt did not need `current_grade` injected to behave grading-aware.
- Old wording such as "banked" was shaping tone in the wrong direction.

### What I changed

- Removed `current_grade` from the injected runtime tutoring state.
- Replaced score-optimizer style runtime language with qualitative progress geometry.
- Replaced backend explanation text `"No topics are banked yet"` with `"No strong footholds yet"`.
- Removed "banked" language from the new tutor prompt and reduced its use in the rubric-generation prompt.

### Unresolved choices

- Existing checked-in lecture rubrics still contain older "banked" wording because they are generated artifacts. The pipeline is updated, but old lecture outputs remain as-is until regenerated.

## Step 5 - Runtime Inputs And Package Shape

### What I inspected

- `lectures/config.json`
- `app/lecture_loader.py`
- `scripts/export_session_package.py`
- admin/build pipeline behavior in `app/admin_workflow.py` and `scripts/build_lecture_package.py`

### What I concluded

- Raw notebook should leave the runtime tutor flow, but remain available upstream for minutes/rubric generation.
- The cleanest way to do that is:
  - remove notebook from default runtime context files
  - filter notebook out of runtime prompt context even if older lecture configs still include it
  - remove notebook from exported runtime session packages

### What I changed

- Removed notebook from default lecture runtime context in `lectures/config.json`.
- Updated runtime context assembly to include only:
  - bot notes
  - slides
  - handout
  - instructional minutes
- Updated export packaging so runtime session exports no longer include `lecture/notebook.md`.
- Kept notebook processing in the admin/build pipeline because it is still an upstream artifact-generation input for minutes and rubric generation.

### Unresolved choices

- Notebook remains in the lecture directory as an upstream build artifact. This is deliberate, but if the repo later wants a stricter runtime/package split, the upstream artifact flow could be separated into a distinct build folder.

## Step 6 - Minutes And Rubric Generation Prompts

### What I inspected

- `prompts/minutes_generation_prompt.md`
- `prompts/master_rubric_generation_prompt.md`
- `scripts/generate_lecture_artifacts.py`

### What I concluded

- The old minutes prompt encouraged a detailed lecture reconstruction with too many schema fields.
- A more selective minutes schema would better serve both rubric generation and runtime tutoring context.
- The rubric prompt should align with the new selective-minutes role and use slightly broader topic granularity.

### What I changed

- Rewrote the minutes prompt into a bounded selective teaching-notes artifact.
- Introduced a leaner minutes schema centered on:
  - central arc
  - selective section notes
  - cross-section priorities
  - rubric handoff notes
- Added boundedness rules:
  - at most 8 sections
  - short arrays
  - omit weak content
- Updated the rubric-generation prompt to treat minutes as selective teaching notes and reduced target topic count from 6-10 to 5-8.
- Added guidance to merge thin adjacent topics into broader, cleaner assessable topics.

### Unresolved choices

- The minutes schema is now much leaner. If later rubric generation proves it needs one extra compact field, add it only with a clear demonstrated use.

## Step 7 - Contract Alignment And Validation

### What I inspected

- prompt export/render code
- test fixtures
- runtime packaging assumptions
- state/output validation

### What I concluded

- Export prompt rendering should reuse the same runtime prompt builder as the live app to avoid drift.
- Tests and fixtures needed to be updated to reflect the no-notebook runtime context and the new private decision trace.

### What I changed

- Updated `scripts/export_session_package.py` to reuse `app.bot_engine.build_dialogue_system_prompt`.
- Removed stale duplicated prompt-rendering logic from the export script.
- Updated fixtures/tests to match:
  - no notebook in runtime context defaults
  - no `confidence` or persisted `lecture_title` in state
  - private `decision_trace` storage
  - no backend-appended timeout message
- Added a small unit test for bare topic-ID sanitization.

### Validation results

- Full automated test suite passed with `pixi run pytest -q`:
  - 99 passed
- Hand-crafted sanity checks confirmed:
  - runtime prompt omits notebook context
  - runtime prompt explicitly enforces one new content contribution
  - runtime prompt explicitly forbids bare topic-ID leakage
  - runtime prompt explicitly constrains the one-sentence move
  - sampled topic IDs are deduplicated before runtime injection
  - student-facing message sanitization replaces bare topic IDs and strips unreliable time claims
  - lecture loader runtime context defaults are now `slides`, `handout`, `minutes`
  - export runtime lecture files no longer include notebook

### Unresolved choices

- The guardrail against multipart questions is prompt-based rather than validator-enforced. That is deliberate for now; a reliable multipart-question detector would need more careful design than a naive punctuation heuristic.

## Follow-up - Move Reveal Discipline Back Into The Prompt

### What I inspected

- the latest user feedback on glib answer-giving
- the recent backend-side low-reveal message shaping in `app/bot_engine.py`
- the current runtime tutor prompt and tutor-generation prompt

### What I concluded

- The backend-side answer-trimming logic was the wrong architectural direction.
- The real issue is that the tutor prompt still allowed the model to choose a low-reveal move in its private trace while emitting a more revealing student-facing message.
- The cleaner fix is prompt-level: require the tutor to draft the reply, critique it for reveal level and productivity, and revise it before emitting `assistant_message`.

### What I changed

- Removed backend-side low-reveal message shaping from `app/bot_engine.py`.
- Kept the backend simple:
  - bare topic-ID replacement
  - unreliable time-claim softening
  - state/contract validation
- Strengthened `prompts/dialogue_system_prompt.md` so the tutor now explicitly:
  - drafts the reply
  - reviews it for productivity and reveal level
  - checks whether it smuggles the answer before the question
  - revises it if a less revealing reply would likely work
- Updated `prompts/tutor_generation_prompt.md` so the generator now targets that stronger internal self-critique step.

### Unresolved choices

- This remains prompt-enforced rather than validator-enforced. That is intentional for simplicity, but it means behavior quality still depends on model compliance rather than a hard backend reject-and-repair loop.

## Follow-up - English-Only Student And Tutor Messages

### What I inspected

- user request to enforce English-only student answers and tutor replies
- current `send_message` flow in `app/main.py`
- student-facing assistant text generation in `app/bot_engine.py`
- available dependencies in `pixi.toml`

### What I concluded

- This is a good fit for the backend because it is a hard interaction policy rather than a tutoring-style preference.
- The implementation should stay small:
  - reject non-English student input before tutoring
  - ensure assistant text returned to the student is English
- A lightweight detector is sufficient if combined with a conservative script check.
- Pure language-ID is too brittle on short English snippets such as "Why sample" or "Next question", so short ASCII phrases need a permissive path.

### What I changed

- Added `langdetect` as a lightweight dependency.
- Added [app/language_policy.py](/home/opher/Repositories/lecture-bot/app/language_policy.py:1) with:
  - disallowed-script detection
  - lightweight English detection
  - English fallback/refusal strings
- Updated [app/main.py](/home/opher/Repositories/lecture-bot/app/main.py:83) so non-English student messages are refused immediately with an English-only reply and are not sent to the tutor model.
- Updated [app/bot_engine.py](/home/opher/Repositories/lecture-bot/app/bot_engine.py:390) so assistant replies and generated report text are forced through English-only fallback handling before reaching the student.
- Added regression tests covering:
  - short English topic picks remain allowed
  - Hebrew student input is refused
  - non-English assistant output is replaced with an English fallback

### Validation results

- `pixi run pytest -q`
- result: `105 passed`

### Unresolved choices

- The detector intentionally allows short ASCII snippets to avoid false positives on short English tutoring replies. That means some very short non-English Latin-script snippets could still slip through. This is an explicit tradeoff in favor of not breaking ordinary English interactions.

## Follow-up - Stepwise Decision Trace And Move Ordering

### What I inspected

- `prompts/dialogue_system_prompt.md`
- `prompts/tutor_generation_prompt.md`
- prompt-focused tests in `tests/test_bot_engine.py`
- the recent debugging discussion about repeated checks, vague one-sentence prompts, and lossy decision-trace summaries

### What I concluded

- The old `decision_trace` language encouraged a retrospective summary rather than a truly staged decision process.
- That made it too hard to see whether the tutor failed at:
  - modeling the student
  - choosing the evidence target
  - selecting among candidate moves
  - reviewing the drafted reply
- The move-family section also still behaved like an unordered catalogue.
- We need both:
  - a stepwise private trace with explicit sequential fields
  - a default move value order plus sharper heuristics about when a move is genuinely useful

### What I changed

- Reworked the runtime prompt so `decision_trace` now mirrors the turn procedure step by step:
  - `step_1_student_model`
  - `step_2_evidence_target`
  - `step_3_move_candidates`
  - `step_4_choice`
  - `step_5_reply_draft`
  - `step_6_reply_check`
  - `step_7_revision`
  - `step_8_final_move`
- Added explicit instructions that later steps must use earlier steps and that the tutor must not collapse the process into a neat retrospective summary.
- Added an explicit default move preference order to the runtime prompt:
  - `contrastive_prompt`
  - `narrowing_question`
  - `partial_frame`
  - `hint`
  - `topic_switch`
  - `concise_reformulation`
  - `compact_explanation`
- Reworked each move-family description so it says more clearly:
  - when the move is strongest
  - when it is a weak or misleading use of that move
  - what kind of pedagogical value it is meant to deliver
- Mirrored those requirements in `prompts/tutor_generation_prompt.md`.
- Added prompt-level regression checks in `tests/test_bot_engine.py`.

### Unresolved choices

- The backend still treats `decision_trace` permissively and does not validate the inner schema. That keeps the code simple, but it means the prompt remains the main enforcement point for trace structure.
