# Lecture Package Contract

This contract says what kind of information a tutor prompt expects to find in a lecture package. It sits beside the [Backend–Tutor Runtime Contract](backend_tutor_contract.md), which says what the backend and a prompt exchange, and the [Tutor Specification Contract](tutor_specification_contract.md), which says what a tutor specification must contain. [Concept-tutor-contracts](https://github.com/opherdonchin/lecture-bot/wiki/Concept-tutor-contracts) explains how they fit together.

**It is fulfilled by being read.** Whoever writes a tutor prompt, by hand or with the [generator](../prompts/tutor_generator_prompt.md), relies on this information being there. Whoever prepares a package, normally a local agent following the [`prepare-lecture` skill](../.agents/skills/prepare-lecture/SKILL.md), supplies it. It describes the sort of information the tutor expects about a lecture; it does not specify the lecture's content. [Decision 0002](../HILD/decisions/0002-lecture-package-contract.md) records why.

## Formats and declarations

Each format has a name ending in a version, such as `pml-brief-1`.

- **A tutor prompt declares the format it expects,** after its backend contract line:

  ```text
  Backend contract: 0.6.1

  Lecture package contract: pml-brief-1
  ```

  The backend removes both lines before sending the prompt to the model.
- **A package declares the format it was built for,** as `"package_contract"` in `lecture_config.json`.
- **[`check-lecture`](../README.md#agent-prepared-lectures) compares the two when a lecture is prepared,** and fails if they differ. The backend does not compare them while running, because a mismatch makes a poorer tutor, not a broken one, and refusing would take a live lecture down when a prompt changes.

**Changing a format.** A format lists only what a prompt or the backend actually uses. When a prompt starts or stops relying on some kind of information, change the format and the prompt in the same pull request, and give the format a new version. Packages built for the old version then fail the check until they are rebuilt. Packages already installed are not affected.

The version comparison catches a package built for another format. It cannot show that a format matches what a prompt really does; that is for the review of the pull request that changes them.

## What every package holds

| Item | What it holds |
|---|---|
| `lecture_config.json` | `lecture_id` (the folder's name), `title`, `course`, `active` and `package_contract`. No `topics` list: the [app would use it in preference to the brief's headings](../app/bot_engine.py). |
| `rubric.md` | What the tutor knows and how it judges evidence, with topics under headings written exactly `### T<n>. <name>`, which the backend parses. |
| Context files | The files the course's `lectures/config.json` lists. |

**Number of topics:** no more than the instance's `SAMPLED_TOPIC_COUNT` ([PML's example settings](../deploy/instances/pml.env.example)). The backend samples that many at random for a session, so a further topic could push out one the lecture depends on.

**Privacy:** a package is private course material, stays out of this repository, and holds no student data.

## Format `pml-brief-1`

For the PML tutor, [`prompts/pml_tutor_prompt.md`](../prompts/pml_tutor_prompt.md). `rubric.md` is a **lecture brief**: one document, which the backend sends as `rubric_text`, holding everything the tutor knows about the lecture. The only context file is the instructor's short `bot_notes.md`, sent as `lecture_context`.

### What the tutor expects

**About the whole lecture:**

- its purpose and arc;
- what was intended and what was actually taught, with the materials students had (lecture, recordings, notebook, book sections);
- which topics are **load-bearing**, the ones the lecture exists to build, in a line starting `- **Load-bearing:**`, because the prompt tells the tutor to prefer them when choosing where to go next;
- how the topics connect, score calibration that holds for every topic, and what sounds right but is wrong.

**About each topic, to teach from:**

- notation, following the slides exactly;
- key ideas, and each derivation's chain of steps with the reason for each step;
- worked examples and their numbers, and how to read the figures;
- the notebook's theory, computational insights and programming points, as content, never as "recall the notebook";
- misconceptions and book references.

**About each topic, to judge evidence by:**

- what counts as strong, partial and weak evidence;
- the depth expected of each element (derive, apply, state or mention), and whether it was taught live, in a recording, in the notebook, or intended but not reached, so the tutor teaches unreached material instead of assessing it as if taught;
- good moves: single questions that make the student work on this topic, each asking for one thing, because the tutor copies their shape;
- scoring cues: what is recall or assisted (developing at most), and what makes the evidence solid or strong.

### Structure

```markdown
# Lecture brief: <lecture title>

## Lecture at a glance
<purpose, arc, intended versus taught, materials, how the tutor should use the brief>
- **Load-bearing:** <the topics the lecture exists to build, and why>

### T1. <topic name>
#### Teach
<what to teach from>
#### Assess
- **Strong:** ...
- **Partial:** ...
- **Weak:** ...
- **Depth:** ...
- **Good moves:** ...
- **Scoring cues:** ...

### T2. ...

## Across topics
<calibration, connections, sound-right-but-wrong risks, what not to assess>
```

Pack it efficiently: formulas and short clauses over prose, no slide-by-slide transcription, and no content repeated across topics.

The format's history: [PR #32](https://github.com/opherdonchin/lecture-bot/pull/32) introduced the brief, and [PR #37](https://github.com/opherdonchin/lecture-bot/pull/37) added load-bearing topics, single-question moves and scoring cues after a pilot session. `pml-brief-1` drops the earlier `Importance` line, which neither the prompt nor the backend used ([scope issue #43](https://github.com/opherdonchin/lecture-bot/issues/43)).
