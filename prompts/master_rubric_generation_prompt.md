# Prompt: Generate a lecture mastery rubric

Use this prompt in a fresh chat. Upload exactly these lecture files before sending the prompt:

- lecture slides
- lecture handout
- lecture notebook
- instructional minutes

---

You are building a **lecture-specific mastery rubric** for a 3rd-year Biomedical Engineering Bayesian statistics course.

Your job is to read the uploaded materials and produce a rubric that can later be used by an educational bot and grading backend to evaluate a short lecture-review dialogue.

## Source roles

Treat the uploaded sources as serving different roles.

- **Slides**: intended lecture structure, sequence, named concepts, figures, examples, and declared emphasis
- **Handout**: compact conceptual reconstruction of the lecture and its terminology
- **Notebook**: concrete demonstrations, code, plots, distributions, worked examples, and what students were expected to inspect
- **Instructional minutes**: oral clarification beyond the slide text, verbally sharpened distinctions, resolved confusions, oral interpretations of figures/formulas/code, warnings against common mistakes, and signals about what seemed central versus incidental

Use all uploaded materials, but do not treat them identically.

- Follow the **lecture flow and scope** primarily from the slides and handout.
- Use the notebook to identify what was concretely demonstrated and therefore can support code/plot/figure-based mastery.
- Use the instructional minutes to deepen the rubric wherever the lecture orally reached a stronger or subtler understanding than the static materials alone would imply.

## Core principles

1. **Use only the uploaded materials.** Do not import outside knowledge unless absolutely necessary to explain notation already used in the files.
2. **Do not hallucinate coverage.** If a topic is only briefly mentioned, mark it as brief. If a topic is missing, say so.
3. **Respect lecture flow.** Follow the lecture’s actual order and emphasis rather than reorganizing into a textbook chapter.
4. **Be pedagogically realistic.** This is not a final exam rubric. It is a mastery rubric for one short lecture-review activity.
5. **Be concept-first.** Reward conceptual understanding, interpretation, discrimination among close ideas, and figure/code understanding rather than memorized wording.
6. **Be short-session compatible.** The rubric must support assessment through a small number of short exchanges.
7. **Minutes deepen understanding; they do not create trivia.** Do not reward recall of classroom anecdotes, logistics, or who asked what.
8. **Generalize oral clarifications.** If a student question triggered an important clarification, extract the underlying conceptual clarification, not the classroom event.
9. **Prefer robust conceptual targets over fragile spoken details.**
10. **Be explicit about changed emphasis.** If the notebook or minutes materially deepen the apparent emphasis of the lecture, say so.

## Important structural rule

This rubric should distinguish clearly between two levels:

- **Topics**: the assessed, sampled, bankable units used for short-session breadth
- **Elements**: the finer conceptual pieces inside a topic

The future tutor may probe individual elements inside a topic, but **lecture-wide coverage, banking, and breadth logic should be based on topics, not on raw element count**.

In other words:

- topics are the bankable breadth units
- elements are the lower-level conceptual pieces inside them

Each element must belong to exactly one topic.
Do **not** repeat the same element in multiple topics.
If something seems to span topics, either split it into narrower elements or assign it one primary home and mention related links only in notes.

## How to use the instructional minutes

Use the minutes to identify:

- distinctions that were verbally sharpened
- confusions that were resolved in a generalizable way
- oral interpretations of figures, formulas, distributions, code, plots, or demonstrations
- warnings against common mistakes
- what seemed central enough to probe carefully
- what seemed incidental enough not to assess directly

Do **not** use the minutes to assess:

- attendance-dependent details
- course logistics
- exact wording from class
- jokes, chatter, or transcript cleanup artifacts
- specifics that mattered only locally in the room

## Task

Produce a complete **lecture mastery rubric** in markdown with the exact top-level headings below.

# Mastery Rubric

## 1. Lecture metadata

Provide:
- lecture title
- lecture number or identifier
- source files used
- main purpose of the lecture
- whether the instructional minutes materially deepened the interpretation of the lecture

## 2. Lecture map

Give a concise table with:
- section or segment name
- 1-2 sentence summary
- relative importance (`core`, `important`, or `brief`)

This should follow the lecture’s actual sequence.

Where relevant, let the summary reflect important oral clarification from the minutes, but do not clutter the table with incidental details.

## 3. Core mastery topics

List the lecture’s main **topics**.

Use **6–10 assessable topics**.

Each topic should:
- be coherent
- be realistically assessable in 2–4 short exchanges
- emphasize concepts rather than wording
- be suitable for short Socratic questioning
- function as a bankable breadth unit for lecture-wide coverage

For each topic, include:
- **topic ID** (T1, T2, ...)
- topic name
- concise description
- importance (`core`, `important`, or `brief`)
- what successful understanding looks like
- common confusion or near-miss likely for this lecture

Keep topics conceptually clean. Merge trivial duplicates.

## 4. Elements within topics

For each topic, list its main **elements**.

Elements are the finer conceptual pieces inside the topic.
They are useful for probing and evidence notes, but they are **not** separate bankable breadth units.

For each element, include:
- element name
- concise description
- why it belongs inside this topic
- whether it was made especially important by:
  - slides / handout
  - notebook
  - instructional minutes

Keep elements short and conceptually meaningful.
Do not create trivia elements.

## 5. Evidence standards

For each topic, define what would count as:
- **Full evidence**
- **Partial evidence**
- **Weak or no evidence**

These standards should be based on demonstrated understanding in dialogue.

Do not require verbatim definitions.
Do not require long prose.
Accept short, imperfect English if the idea is clear.

Use the instructional minutes to sharpen what counts as real understanding versus superficial regurgitation.

### Important calibration rule

Treat **Full evidence** as enough evidence for the topic to count as **meaningfully mastered / banked** for session purposes.

Do **not** define Full evidence as exhaustive, perfect, or maximal mastery.
The highest mastery levels should still leave room for unusually strong transfer, synthesis, precision, and independence beyond the threshold for a solid mastered topic.

Also include a short note on **mastery progression cues** for that topic, aligned qualitatively to an 8-level within-topic progression, moving from:
- first meaningful foothold
- clearer distinction or usable explanation
- student-owned explanation
- fresh check or guided transfer
- stronger independent use
- robust understanding across more than one probe
- strong transfer or synthesis
- near-complete session mastery

Do not turn this into rigid scoring arithmetic.
Do not use unexplained internal jargon.
Use it as a qualitative progression guide for distinguishing shallow, solid, and unusually strong evidence.

For each topic, make clear:
- what kind of evidence is merely echoed or assisted
- what kind of evidence is genuinely student-owned
- what kind of fresh check or transfer would raise confidence
- which near-misses are especially important for this lecture
- whether this topic is especially vulnerable to students sounding right without understanding

## 6. Grade structure

Provide **grading-relevant structure** for the future bot and backend, without inventing or recommending hidden numerical weighting schemes.

Do **not**:
- suggest numerical weights across topics
- suggest formulas for converting sampled-topic performance into a session grade
- restate hidden grading arithmetic
- include tutor policy about when to stay on a topic, switch topics, or revisit earlier topics
- include implementation-facing decision logic that is not part of the mastery rubric itself

Instead, include:
- a clear statement of what it means for a topic to count as **meaningfully mastered / banked** for lecture-wide coverage
- concise **qualitative lecture-wide coverage anchors** aligned to increasing breadth across the lecture, such as:
  - strong foothold in one central lecture idea
  - meaningful early coverage across the lecture
  - solid grounding across the core lecture terrain
  - broad and competent coverage
  - very broad coverage with only small gaps remaining
  - full lecture mastery for session purposes
- a rule that grading should reflect the **best demonstrated mastery so far**
- a rule that uncovered material counts as **not yet demonstrated**
- a rule that vague buzzwords, label-matching, or tutor-echoing do **not** earn strong credit
- a short note that assisted answers may establish partial evidence, but independent explanation, fresh interpretation, and transfer provide stronger evidence
- a short note that later refinement on a topic can strengthen confidence, but should not be treated as the only way for a topic to count as solidly understood

The purpose of this section is to help the rubric align with the grading policy’s breadth/depth logic **without** asking the rubric writer to specify hidden numerical policy or bot behavior.

## 7. Good question forms for this lecture

List the best kinds of questions for checking understanding of this lecture.

Prefer forms such as:
- forced distinction
- classification
- figure interpretation
- code or plot interpretation
- identifying what is wrong in a claim
- choosing between two plausible alternatives
- one-sentence correction
- one-sentence explanation
- applying the idea to a new but nearby case
- explaining why an example fits one concept and not another

Also list question forms that should be used sparingly or avoided.

Explicitly avoid:
- “What did the professor say about...”
- “Which example was used in class...”
- transcript-memory questions
- wording-recall questions unless the wording itself was conceptually important

## 8. Report-ready mastery labels

Provide short phrase labels that a bot could use in interim or final reports.

For each topic, give:
- mastered label
- partial label
- missing label

These should be concise and student-readable.

## 9. Rubric use notes

Write short notes about:
- what the lecture seems to care about most
- where the lecture is vulnerable to superficial regurgitation
- which topics need especially careful probing
- how much fidelity to slide wording matters versus fidelity to concepts
- which important clarifications came mainly from oral explanation rather than the static materials
- whether the notebook materially changes what should count as mastery
- whether the minutes revealed hidden depth that should influence questioning

Do not include bot-policy recommendations, routing strategy, or implementation logic unless they are directly necessary to interpret the mastery rubric.

## Additional constraints

- Use only the uploaded materials.
- Keep the rubric lecture-specific.
- Do not write generic study advice.
- Be explicit when the lecture is broad but the assessment session should stay short.
- If the notebook materially changes the lecture emphasis, say so.
- If the instructional minutes materially change the lecture emphasis, say so.
- Distinguish between:
  - what was explicit in the slides/handout,
  - what was concretely demonstrated in the notebook,
  - and what was clarified orally in the instructional minutes.
- When in doubt, prefer robust conceptual targets over narrow spoken details.