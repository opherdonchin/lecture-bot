# Lecture brief format, version 2

A **lecture brief** is one markdown document per lecture that replaces both the mastery rubric and the separate lecture context for a course whose tutor prompt expects it (currently PML, `prompts/pml_tutor_prompt.md`). It is stored as the lecture's `rubric.md`, so that the existing backend uses it unchanged: it is injected as `rubric_text`, its `### Tn.` headings define the session's topics, and topic scoring and the final report read it as the rubric. The lecture's `lectures/config.json` then lists only the instructor's `bot_notes.md` as context.

Scope: [scope issue #31](https://github.com/opherdonchin/lecture-bot/issues/31). Version 1 was hand-built for PML L01; version 2 adds load-bearing content, single-question good moves and scoring cues, after the first pilot session showed compound questions and generous scores; a generator follows in that scope's PR C.

## Required structure

```markdown
# Lecture brief: <lecture title>

## Lecture at a glance
<purpose, arc, what was intended versus what was actually taught, materials (lecture, recordings, notebook, book sections), load-bearing content, and how the tutor should use the brief>

### T1. <topic name>
- **Importance:** core | important | brief
#### Teach
<notation; key ideas; derivation chain with the reason for each step; worked examples and their numbers; figure interpretations; notebook: computation and programming points; misconceptions; book references>
#### Assess
- **Strong evidence:** ...
- **Partial evidence:** ...
- **Weak evidence:** ...
- **Depth:** derive | apply | state | mention, per element, and whether taught live, in a recording, in the notebook, or intended but not reached
- **Good moves:** single questions that make the student work on this topic, one per turn
- **Scoring cues:** what is recall or assisted (developing at most), and what makes the evidence solid and strong

### T2. ...

## Across topics
<score calibration that holds for every topic, connections between topics, sound-right-but-wrong risks, what not to assess>
```

Rules:

- Topic headings are exactly `### T<n>. <name>` followed by a `- **Importance:**` line; the backend parses these.
- Cover the **intended** material (scope and section design), not only what was reached in class, and mark which parts were intended but not taught live, so the tutor can teach them rather than assess them as if taught.
- Name the **load-bearing** topics, the ones the lecture exists to build, separately from framing and supporting topics, so that the tutor steers each session to the lecture's core.
- Write each good move as **one question asking for one thing**. The tutor copies their shape, and a move that bundles several asks produces compound questions.
- Give each topic **scoring cues** that place recall and answers to a question that supplied the frame at developing or below, so that a single correct line is not scored as solid.
- Include the notebook's theory, computational insights and programming points as content, without asking students to recall the notebook.
- Pack efficiently: prefer formulas and short clauses to prose; no slide-by-slide transcription; no duplicated content across topics.
- No student data. The brief is private course material and never goes into the repository.
