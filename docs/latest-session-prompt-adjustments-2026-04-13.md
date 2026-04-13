# Latest-Session Prompt Adjustments (2026-04-13)

## Scope

This note records the prompt adjustments made after reviewing the latest completed session on April 13, 2026:

- session id: `c180c29f-4848-4616-9fcc-19aec1592ae2`
- lecture: `lecture_01`

The goal of this round was narrow:

- improve classifier handling of the specific routing failures seen in the latest session
- improve tutor handling of the specific flat-response patterns seen in the latest session
- avoid broader Python-side changes until we gather more evidence

No Python application logic was changed in this round.
The changes are limited to prompt files, prompt-generator source files, and prompt-guardrail tests.

## Evidence base

The changes were based on replay diagnostics using the real latest-session messages, real recent-message windows, and the current prompt families.

### 1. Classifier failure: terse deferential reply after options

Observed turn:

- tutor: switched topics and then asked whether to start with an overview or a specific question
- student: `Whatever.`
- logged classifier output: `off_task -> redirect`

Replay finding:

- stronger classifier models alone still often treated `Whatever.` as `off_task`
- adding local state/action guidance or adding an explicit classifier rule reliably flipped it to `technical_request -> provide_technical_support`

Interpretation:

- this was not mainly a model-capability failure
- it was a local routing-rule failure on a terse but contextually meaningful steering turn

### 2. Classifier failure: "I think I understand it"

Observed turn:

- student: `Nope. I think I understand it.`
- logged classifier output: `content_answer -> respond`

Replay finding:

- this turn was mixed and somewhat unstable
- stronger models sometimes read it as steering
- action-oriented state and a local classifier rule often flipped it to `technical_request -> provide_technical_support`

Interpretation:

- the current classifier was too eager to treat "I understand it" as content evidence instead of a pace/direction signal

### 3. Classifier / policy miss: thoughtful objection after scaffolding

Observed turn:

- student: `Well, mood varies from day to day so I'm not sure what meaning there is to repeated measures across days.`
- logged classifier output: `content_answer -> respond`

Replay finding:

- stronger models often kept `content_answer` but changed the policy recommendation to `provide_content_support`
- adding a local classifier rule about objections/confounds after scaffolding had the same effect

Interpretation:

- this was less a semantic-class problem than a support-policy problem
- the student was still engaging content, but ordinary `respond` was too weak a recommendation

### 4. Classifier failure: mixed content fragment plus orientation request

Observed turn:

- student: `They reduce it. I'm not sure what you're getting at.`
- logged classifier output: `content_answer -> respond`

Replay finding:

- stronger models often treated this as an orientation request or at least moved it to support mode
- prompt edits and richer state both helped the current classifier recognize the steering/orientation component

Interpretation:

- the current classifier was underweighting the "what are you getting at?" clause when paired with a short answer fragment

### 5. Tutor flatness: generic menu loop after terse steering

Observed turn:

- after the student said `Whatever.`, the tutor responded with another open invitation instead of making a decisive move

Replay finding:

- in technical-support mode, the current prompt often defaulted to another menu or open invitation
- a local prompt edit telling the tutor not to ask another open preference question in this exact situation changed the response materially

Interpretation:

- local operational guidance mattered more than broad "be adaptive" wording

### 6. Tutor flatness: low-value question after "ask me something that gets points"

Observed turn:

- student: `Whatever. Just ask me a question that will get me points.`
- tutor asked a generic low-level warm-up question on the newly opened topic

Replay finding:

- richer action-guidance state improved the current model
- a local technical-support prompt edit about avoiding low-level warm-ups also improved the current model
- broad wording about adapting to the student's goal helped much less

Interpretation:

- the tutor needed a more local instruction about what "high-value" means operationally

### 7. Tutor flatness: indirect reply to "I'm not sure what you're getting at"

Observed turn:

- the tutor explained a bit, then asked for yet another example

Replay finding:

- generic prompt reminders to "answer directly" helped only a little
- stronger local instructions worked better when they forced the tutor to name the target distinction explicitly before asking the next question
- richer line-memory state also helped

Interpretation:

- the prompt needed a sharper local rule for opaque, example-loop situations

## Changes made

### Classifier prompt changes

Added local routing guidance so the classifier now treats these more explicitly:

- terse deferential replies after offered options as often `technical_request` rather than `off_task`
- "I already understand" turns as often pace/direction signals rather than fresh content evidence
- short content fragments plus "I'm not sure what you're getting at" as often orientation requests
- thoughtful objections/confounds after repeated scaffolding as often deserving `provide_content_support`

Files changed:

- `prompts/generated/classifier_system_prompt.md`
- `prompts/generation/classifier_system_prompt_generator.md`

### Technical-support prompt changes

Added local procedural guidance so the tutor now gets clearer instructions to:

- avoid another open preference question after a terse deferential reply like `whatever`
- make one decisive next move instead
- avoid low-level warm-up questions when the student explicitly asks for the most useful question or a question that will get points

Files changed:

- `prompts/generated/provide_technical_support_prompt.md`
- `prompts/generation/provide_technical_support_system_prompt_generator.md`

### Content/respond prompt changes

Added sharper local handling for under-oriented turns:

- when the student asks what the tutor is getting at, the tutor should name the target more explicitly
- when possible, the tutor should state the target as a contrast/distinction rather than another loose rephrase
- when example-driven probing has already gone flat, the tutor should not ask for yet another example before naming the key distinction more plainly

Files changed:

- `prompts/generated/respond_prompt.md`
- `prompts/generation/respond_system_prompt_generator.md`
- `prompts/generated/provide_content_support_prompt.md`
- `prompts/generation/provide_content_support_system_prompt_generator.md`

## Why these changes and not broader ones

The latest-session diagnostics suggested:

- some failures were genuinely routing failures
- some failures were local tutor-move failures even with nominally correct routing
- prompt changes worked best when they were local and operational
- broad philosophical restatements had much weaker effects

For that reason, this round intentionally avoided:

- changing the policy decider
- adding new backend state fields
- changing state merge logic
- changing the dialogue model

Those may still be useful later, but the evidence from the latest session supported a prompt-first pass before broader backend changes.

## Generalization hypothesis

The changes in this round are meant to help three recurring patterns:

1. Very short but contextually meaningful steering turns that were being mistaken for `off_task`
2. Mixed turns that contain a thin answer fragment plus an orientation request
3. Flat tutoring lines where the model keeps asking for more examples instead of naming the missing distinction

The main hypothesis is:

- local rules around these patterns will improve routing and next-move quality more reliably than broader prompt philosophy alone

## Remaining uncertainty

These changes are still provisional.
The diagnostics that motivated them were convincing, but they were replay diagnostics on a small number of latest-session turns.

The main things still to validate with future evidence are:

- whether these local rules improve live sessions without causing overcorrection
- whether classifier stability improves on mixed-intent turns
- whether the tutor now exits menu loops and example loops more reliably
- whether stronger line-memory/state changes are still needed after these prompt adjustments

## Review note

This document is meant to support later review once more live evidence is available.
It should be read together with the git snapshot/tag created immediately beforehand:

- commit: `ac0b50f`
- tag: `pre-experiment-2026-04-13-193401`
