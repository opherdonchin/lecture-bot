# Tutor Redesign: Loop Reduction and Value-per-Turn

## What caused the loops

The old non-redirect tutor prompts carried a verbose natural-language synopsis of the interaction:

- `student_goal_now`
- `interaction_state`
- `what_student_has_shown`
- `what_remains_uncertain`
- `why_continue_or_switch`
- `best_next_move`
- `progress_focus`

Those fields were useful as reminders, but they also made the model likely to echo the same planning language back to the student. That showed up as:

- move narration instead of execution
- session-steering talk lasting too many turns
- repeated low-yield checks after the student had already shown enough
- soft acknowledgments of repetition complaints without a real pivot

The prompt family split made that worse. Similar tutoring behavior lived in several prompts, so changes meant to reduce loops were easy to apply unevenly.

## Design choice

I kept:

- the classifier separate
- the redirect prompt separate

I collapsed the other tutor prompts into one unified prompt:

- runtime tutor prompt: [prompts/generated/tutor_prompt.md](/home/opher/Repositories/lecture-bot/prompts/generated/tutor_prompt.md:1)

The unified prompt now receives:

- a compact `tutor_mode`
- compact current-state fields
- a backend-computed action hint

The old non-redirect prompt files are still present only as deprecation notes so the runtime architecture is inspectable.

## What changed

### Prompt architecture

All non-redirect tutoring now flows through one prompt with one core behavior policy:

- answer directly when needed
- return to content quickly
- avoid move narration
- ask at most one substantive content question
- stay source-bounded to lecture materials

### Carried state

The tutor-visible state was reduced to compact operational fields:

- `current_topic_id`
- `current_line_status`
- `last_challenge_level`
- `must_not_repeat`
- backend-owned routing/action memory such as `last_action`, `last_target_topic_id`, `last_reason_code`, `last_repetition_complaint`

Removed fields included the old natural-language synopsis and small loop counters.

### Backend action hints

The backend now computes a compact next-move hint:

- `recommended_action`
- `target_topic_id`
- `challenge_level`
- `reason_code`
- `secondary_reason_code`
- `must_not_repeat`

This is intentionally operational rather than narrative. It lets the backend steer value-per-turn decisions without handing the model a paragraph it can parrot.

### Difficulty ladder

The unified prompt now exposes an explicit ladder:

1. recognition / naming
2. criterion / definition
3. distinction / contrast
4. explanation / why
5. application / transfer
6. practical interpretation
7. independent correction / critique

The action-hint logic now uses this ladder when the student asks for harder or more efficient questions.

### Source-boundedness

The unified prompt now explicitly says:

- use lecture-native terminology only
- do not import outside textbook terminology
- do not upgrade the student’s answer into external jargon
- prefer lecture wording when uncertain

There is also a lightweight backend rewrite pass for a small set of known external terms when they are not in the lecture materials.

### Observability

Per-turn dialogue audit logging now stores:

- effective policy
- prompt template name
- model name
- tutor mode
- action hint JSON
- challenge level
- current topic
- target topic
- whether the turn ended with a content question
- repetition-complaint flag
- whether the tutor switched topics

This makes loop diagnosis much easier than before.

## What remains unresolved

The redesign clearly improved structure, but live runs still showed two remaining weaknesses:

1. Harder-question requests can still become transformed versions of an easy prompt rather than a genuinely higher-ceiling question.
2. The tutor can still occasionally acknowledge a correct answer and then ask a near-duplicate follow-up on the same point.

That means the prompt and backend are now much better aligned against loops, but the model still needs stronger question-shape pressure around:

- true difficulty escalation
- stronger stop conditions after sufficient evidence
- avoiding disguised repeats after a good answer

## Main files changed

- [app/bot_engine.py](/home/opher/Repositories/lecture-bot/app/bot_engine.py:1)
- [app/schema.py](/home/opher/Repositories/lecture-bot/app/schema.py:1)
- [app/session_manager.py](/home/opher/Repositories/lecture-bot/app/session_manager.py:1)
- [app/models.py](/home/opher/Repositories/lecture-bot/app/models.py:1)
- [app/turn_reconstruction.py](/home/opher/Repositories/lecture-bot/app/turn_reconstruction.py:1)
- [prompts/generated/tutor_prompt.md](/home/opher/Repositories/lecture-bot/prompts/generated/tutor_prompt.md:1)
- [prompts/generated/classifier_system_prompt.md](/home/opher/Repositories/lecture-bot/prompts/generated/classifier_system_prompt.md:1)
