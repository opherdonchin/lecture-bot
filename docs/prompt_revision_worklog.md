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
