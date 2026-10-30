# Lecture Package Contract

This contract says what a tutor prompt can rely on finding in a lecture package. It sits beside the [Backend–Tutor Runtime Contract](backend_tutor_contract.md), which says what the backend and a prompt exchange, and the [Tutor Specification Contract](tutor_specification_contract.md), which says what a tutor specification must contain. [Concept-tutor-contracts](https://github.com/opherdonchin/lecture-bot/wiki/Concept-tutor-contracts) explains how they fit together, and [Concept-lecture-package](https://github.com/opherdonchin/lecture-bot/wiki/Concept-lecture-package) explains packages.

**It is fulfilled by being read.** Whoever writes a tutor prompt, by hand or with the [generator](../prompts/tutor_generator_prompt.md), relies on it. Whoever prepares a package, normally a local agent following the [`prepare-lecture` skill](../.agents/skills/prepare-lecture/SKILL.md), supplies what it describes. [Decision 0002](../HILD/decisions/0002-lecture-package-contract.md) records why.

## Three levels

| Level | What it settles | Who decides | How exact |
|---|---|---|---|
| [1. What the app requires](#1-what-the-app-requires-of-every-package) | What every package needs in order to run, whatever its format | The code; this section only describes it | Exact |
| [2. What makes a format valid](#2-what-makes-a-format-valid) | The rules any format must follow | The researcher, by accepting this contract | Exact |
| [3. A format](#3-format-pml-brief-1) | The sorts of information one tutor prompt expects about a lecture | The researcher, by accepting the format with the prompt that uses it | The sorts of information, not their wording or layout |

**Two things this contract does not decide:**

- **A course's recipe,** `~/lecture-bot-instances/<course>/lecture_recipe.md`, says where that course's sources are and what it emphasises. The format says what the tutor needs; the recipe says how to get it from this course's materials. The researcher owns it. A recipe can ask for more than a format does, but it cannot remove what a format expects.
- **A lecture's content:** its topics, what is taught and how it is scored. The preparing agent proposes these, and the researcher's review is the only check on them.

## 1. What the app requires of every package

These come from the code and hold whatever the format. The code is the authority: if this section and the code disagree, this section is wrong.

**A package must have:**

- a folder named for the lecture;
- `lecture_config.json`, valid JSON ([`load_lecture_package`](../app/lecture_loader.py));
- `rubric.md`, which the backend sends to the tutor as `rubric_text`;
- every context file marked required in the course's `lectures/config.json`.

**Topic headings in `rubric.md`,** the one place the code reads the text itself. A heading is `### T<n>. <name>` or `### T<n> — <name>` ([`parse_rubric_topics`](../app/bot_engine.py)). The app would still open a session with no headings, but it keeps scores only for known topics, so nothing could be scored. [`check-lecture`](../README.md#agent-prepared-lectures) therefore fails without them.

**Context files reach the tutor only under the keys `bot_notes`, `slides`, `handout` and `minutes`.** A file listed under any other key loads and is then silently left out.

**Optional settings in `lecture_config.json`, which the student app reads:**

| Setting | If absent | Note |
|---|---|---|
| `active` | **The lecture is on** | `push-lecture` always installs it as `false`. |
| `title` | The lecture's folder name | |
| `topics` | Topics come from the headings | A copy of the headings that the app prefers to them. `check-lecture` fails if it disagrees with them. |
| `tutor_prompt_template` | The instance's prompt | Lets one lecture use a different prompt. |
| `context_files` | The course's `lectures/config.json` | |

**Everything else is ignored by the student app.** That includes other files in the folder, and other settings: `course` and `files`, which the admin pages use; `package_contract`, which only `check-lecture` reads; and `lecture_id`, which `check-lecture` requires to match the folder if present.

## 2. What makes a format valid

A format is valid if:

1. **It has a name ending in a version,** such as `pml-brief-1`.
2. **A tutor prompt declares it,** and the format names that prompt. A prompt declares it after its backend contract line, and the backend removes both lines before the model sees the prompt:

   ```text
   Backend contract: 0.6.1

   Lecture package contract: pml-brief-1
   ```

3. **It fits level 1.** The tutor receives only `rubric_text` and the context files, so everything a format expects must arrive through them, and the topic headings must be there.
4. **It lists only what the prompt or the backend actually uses.** If nothing uses a kind of information, it does not belong in the format.
5. **It describes sorts of information, not a lecture's content.** It requires exact wording only where the code or the prompt depends on that wording, and says so. Any layout it shows is an example.
6. **It changes with its prompt.** When a prompt starts or stops relying on some kind of information, the format and the prompt change in the same pull request, and the format gets a new version.

**Comparing declarations.** A package declares the format it was built for, as `"package_contract"` in `lecture_config.json`. `check-lecture` compares that with the prompt's declaration and fails if they differ. So packages built for an old version fail the check until they are rebuilt; lectures already installed are not affected. The backend does not compare them while running, because a mismatch makes a poorer tutor, not a broken one, and refusing could take a live lecture down when a prompt changes.

**What the comparison cannot do.** It catches a package built for another format. It cannot show that a format matches what a prompt really does, or that a package supplies what its format describes. Those rest on review.

## 3. Format `pml-brief-1`

For the PML tutor, [`prompts/pml_tutor_prompt.md`](../prompts/pml_tutor_prompt.md). `rubric.md` is a **lecture brief**: one document holding everything the tutor knows about the lecture. The only context file is the instructor's short `bot_notes.md`.

### The sorts of information the tutor expects

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

**How many topics:** no more than the instance's `SAMPLED_TOPIC_COUNT` ([PML's example settings](../deploy/instances/pml.env.example)). The backend samples that many at random for a session, so a further topic could push out a load-bearing one.

### Exact wording this format depends on

Only these:

- **The topic headings** (level 1).
- **Formulas written as `$…$`,** because the prompt warns the tutor that the brief writes them that way and that it must not copy them.
- **A line starting `- **Load-bearing:**`,** so that `check-lecture` can show it to the researcher to confirm. Without it the check reports none marked and still passes, and the tutor can still read the topics named elsewhere in the brief.

### An example layout

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

### History

[PR #32](https://github.com/opherdonchin/lecture-bot/pull/32) introduced the brief, and [PR #37](https://github.com/opherdonchin/lecture-bot/pull/37) added load-bearing topics, single-question moves and scoring cues after a pilot session. `pml-brief-1` drops the earlier `Importance` line, which neither the prompt nor the backend used ([scope issue #43](https://github.com/opherdonchin/lecture-bot/issues/43)).
