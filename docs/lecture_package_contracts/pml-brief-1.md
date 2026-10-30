# Lecture package contract `pml-brief-1`

For the PML tutor, [`prompts/pml_tutor_prompt.md`](../../prompts/pml_tutor_prompt.md), which declares this contract. The [rules all contracts follow, and what the app requires of every package](../lecture_package_contract.md), are in the shared document. `rubric.md` is a **lecture brief**: one document holding everything the tutor knows about the lecture. The only context file is the instructor's short `bot_notes.md`.

## The sorts of information the tutor expects

**About the whole lecture:**

- its purpose and arc;
- what was intended and what was actually taught, with the materials students had (lecture, recordings, notebook, book sections);
- which topics are **load-bearing**, the ones the lecture exists to build, because the prompt tells the tutor to prefer them when choosing where to go next;
- how the topics connect, score calibration that holds for every topic, and what sounds right but is wrong.

**About each topic, to teach from:**

- notation, following the slides;
- key ideas, and each derivation's chain of steps with the reason for each step;
- worked examples and their numbers, and how to read the figures;
- the notebook's theory, computational insights and programming points, as content the tutor can use;
- misconceptions and book references.

**About each topic, to judge evidence by:**

- what counts as strong, partial and weak evidence;
- the depth expected of each element (derive, apply, state or mention), and whether it was taught live, in a recording, in the notebook, or intended but not reached, so the tutor teaches unreached material instead of assessing it as if taught;
- good moves: single questions that make the student work on this topic, each asking for one thing, because the tutor copies their shape;
- scoring cues: what is recall or assisted (developing at most), and what makes the evidence solid or strong.

**How many topics:** no more than the instance's `SAMPLED_TOPIC_COUNT` ([PML's example settings](../../deploy/instances/pml.env.example)). The backend samples that many at random for a session, so a further topic could push out a load-bearing one.

## Exact wording this contract depends on

Only these:

- **The topic headings** ([level 1](../lecture_package_contract.md#1-what-the-app-requires-of-every-package)).
- **Formulas written as `$…$`,** because the prompt warns the tutor that the brief writes them that way and that it must not copy them.
- **A line starting `- **Load-bearing:**`,** so that `check-lecture` can show it to the researcher to confirm. Without it the check reports none marked and still passes, and the tutor can still read the topics named elsewhere in the brief.

## An example layout

This is what the L01 and L02 briefs use. It is an example, not a requirement: another layout that supplies the same information is valid.

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

## History

[PR #32](https://github.com/opherdonchin/lecture-bot/pull/32) introduced the brief, and [PR #37](https://github.com/opherdonchin/lecture-bot/pull/37) added load-bearing topics, single-question moves and scoring cues after a pilot session. This contract drops the earlier `Importance` line, which neither the prompt nor the backend used ([scope issue #43](https://github.com/opherdonchin/lecture-bot/issues/43)).
