Write a production-ready single runtime system prompt for a lecture-review tutoring bot.

You will be given one primary input: a tutor specification in the current structured format:
- A. Tutor foundations
- B. Tutor understanding
- C. Evaluation
- D. Success condition

Your task is to convert that tutor specification into the actual runtime system prompt for the tutor itself.

Do not write commentary about the specification.
Do not write analysis of the specification.
Do not write implementation notes.
Do not write a generator prompt.
Do not write multiple prompt families.
Do not write routing logic or classifier logic.
Return only the final runtime system prompt.

## Source of truth

The tutor specification is the governing source of truth.

Your job is to translate it into runtime behavior, not to improve it, replace it, or smuggle in your own tutoring philosophy.

If you are tempted to add a default assumption about how tutors should behave, stop and check whether that assumption is actually supported by:
- the tutor specification itself, or
- the runtime contract given below

If it is not supported, do not add it.

## What you are producing

Produce one coherent runtime system prompt that could directly govern the tutor’s behavior during ordinary tutoring turns.

The prompt should be concise enough for real use, but rich enough to faithfully encode:
- the tutor’s purpose
- the tutor’s stance
- the tutor’s priorities
- the tutor’s model of the student and interaction
- the tutor’s decision architecture
- the tutor’s interaction modes
- the tutor’s evaluation logic
- the tutor’s success condition
- the tutor’s output contract

The runtime prompt must feel like a prompt for a real tutor, not a summary of a document.

## Core translation requirement

Do not merely paraphrase headings.

Translate the specification into operational guidance:
- what the tutor is trying to do on each turn
- what it should notice
- how it should choose among possible moves
- how it should respond to confusion, partial understanding, stalls, help-seeking, and progress
- how it should balance teaching and evidence collection
- how it should treat scaffolding and student ownership
- how it should behave visibly in dialogue
- how it should update state conservatively and honestly

## Structural fidelity requirements

You must preserve the distinctions built into the tutor specification.

### A. Tutor foundations
Translate A into the tutor’s identity, purpose, center of gravity, and turn-level priorities.

Preserve:
- whether the tutor is fundamentally a teacher, coach, guide, evaluator, or some combination
- the ordering of priorities
- the intended tone and stance
- the relation between teaching and evidence gathering

### B. Tutor understanding
Translate B into the tutor’s working model of:
- the learning task
- the student
- the interaction

#### B1. View of subject matter / learning task
Make this shape the tutor’s behavior toward depth, breadth, connections, distinctions, application, and coherence.

#### B2. View of the student and interaction
Make this shape what the tutor attends to in the student’s state and in the momentum of the exchange.

#### B3. Interaction repertoire
Handle B3 especially carefully.

You must preserve the distinction between:
- B3.1. Core decision architecture
- B3.2. Interaction modes
- B3.3. Applied interactional guidance

Do not collapse these into one generic “tutor behavior” section.

Specifically:
- B3.1 should become the tutor’s central organizing judgment about what kind of work is needed now
- B3.2 should become the tutor’s available recurring modes of educational action, without turning them into rigid stages
- B3.3 should become the visible conversational behavior and practical difficulty-handling guidance that governs actual replies

If the specification gives the tutor a central question or governing decision rule, that should become a central operating principle in the runtime prompt.

### C. Evaluation
Handle C especially carefully.

You must preserve the distinction between:
- C1. Evaluation structure
- C2. Evaluation criteria

Specifically:
- C1 should determine the role evaluation plays in the interaction and how it relates to teaching
- C2 should determine what counts as stronger or weaker evidence of understanding

Do not turn evaluation into the tutor’s primary purpose unless the specification explicitly makes it primary.

If the specification makes evaluation subordinate to teaching, preserve that.
If it makes evaluation co-equal with teaching, preserve that.
Do not normalize it to your own default.

### D. Success condition
Use D to define what a successful turn and a successful overall interaction are trying to achieve.

The success condition should not be tacked on as a slogan.
It should shape the runtime behavior.

## Runtime contract you must build into the prompt

Assume the application provides the tutor with:
- lecture title
- rubric text
- lecture context
- current state
- recent conversation
- the student’s latest message

Assume the tutor must return JSON only in exactly this shape:

{
  "assistant_message": "string",
  "updated_state": { ... }
}

The runtime prompt you write must require JSON-only output.

The runtime prompt must require the tutor’s visible reply to stay short and focused.

The runtime prompt must require the tutor to ask at most one meaningful next question or invitation on a turn, unless the specification clearly justifies a different pattern.

## State update contract

Assume current state includes at least:
- topics_sampled
- topics_covered
- mastery
- evidence_notes
- turn_count
- lecture_title

Build the runtime prompt so that:
- `topics_sampled` is treated as backend-owned and must not be changed by the tutor
- canonical topic IDs are used when updating topic-linked state
- `topics_covered` is updated only for meaningfully engaged topics
- `mastery` is updated conservatively and honestly
- `evidence_notes` briefly reflect the strongest current evidence
- `turn_count` advances by one
- `lecture_title` is preserved or carried through appropriately

If a turn does not yield real content-assessment evidence, the tutor should return empty content-assessment fields rather than inventing them:
- `"topics_covered": []`
- `"mastery": {}`
- `"evidence_notes": {}`

Do not invent additional state fields unless they are clearly required by the tutor specification and fit naturally inside `updated_state`.

## What not to invent

Do not invent any of the following unless the tutor specification explicitly requires them:
- hidden scoring arithmetic
- grading weights
- topic sampling logic
- classifier categories
- routing architecture
- prompt families
- hard backstop rules
- assessment dimensions not present in the specification
- mastery scales not present in the specification
- UI features
- tool usage
- logging structures

The runtime prompt may include guardrails needed for safe and honest tutoring behavior, but they should arise from the tutor specification and the runtime contract, not from your private defaults.

## Style of the runtime prompt

The runtime prompt you write should itself be:
- clear
- direct
- operational
- well organized
- suitable for production use

The tutor it defines should sound like what the specification calls for, not like a generic helpful assistant.

## Recommended working method

Before writing the final runtime prompt, silently do this:

1. Identify the tutor’s governing purpose and priority structure from A and C.
2. Identify the tutor’s model of learning and the student from B1 and B2.
3. Identify the tutor’s central decision architecture from B3.1.
4. Identify the tutor’s interaction modes from B3.2.
5. Identify the tutor’s applied conversational behavior from B3.3.
6. Identify the role and evidential standards of evaluation from C1 and C2.
7. Identify the practical success condition from D.
8. Convert all of that into a single coherent runtime prompt that a model could actually follow turn by turn.
9. Check that you did not import unsupported pedagogy from yourself.

Do not output this analysis.
Output only the final runtime system prompt.

## Final output requirement

Return only the completed runtime system prompt.
No headings outside the prompt.
No explanation.
No commentary.