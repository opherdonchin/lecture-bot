# Prompt: Generate a lecture mastery rubric

Use this prompt in a fresh chat. Upload exactly these lecture files before sending the prompt:

- lecture slides
- lecture handout
- lecture notebook

---

You are building a **lecture-specific mastery rubric** for a 3rd-year Biomedical Engineering Bayesian statistics course.

Your job is to read the uploaded **slides, handout, and notebook** and produce a rubric that can later be used by an educational bot to tutor students and assign them a lecture-review grade.

## Core principles

1. **Use only the uploaded materials.** Do not import outside knowledge unless absolutely necessary to explain notation already used in the files.
2. **Do not hallucinate coverage.** If a topic is only briefly mentioned, mark it as brief. If a topic is missing, say so.
3. **Respect lecture flow.** Follow the lecture's actual order and emphasis rather than reorganizing into a textbook chapter.
4. **Be pedagogically realistic.** This is not a final exam rubric. It is a mastery rubric for one short lecture-review activity.
5. **Be gradeable.** The rubric must support an estimated numeric grade from 0-100 based on what the student has demonstrated.
6. **Concept-first.** The rubric should reward conceptual understanding, interpretation, discrimination among close ideas, and figure/code understanding rather than memorized wording.
7. **Short-session compatible.** The rubric must be structured so that a later educational bot can sample a small subset of targets for a session lasting under 10 minutes.

## Task

Produce a complete **lecture mastery rubric** in markdown with the exact top-level headings below.

# Mastery Rubric

## 1. Lecture metadata

Provide:

- lecture title
- lecture number or identifier
- source files used
- main purpose of the lecture

## 2. Lecture map

Give a concise table with:

- section or segment name
- 1-2 sentence summary
- relative importance (`core`, `important`, or `brief`)

This should follow the lecture's actual sequence.

## 3. Core mastery targets

List the lecture's main learning targets.

For each target, include:

- target name
- concise description
- importance (`core`, `important`, or `brief`)
- what successful understanding looks like
- common confusion or near-miss likely for this lecture

Keep targets conceptually clean. Merge trivial duplicates.

## 4. Assessable target clusters for short sessions

Group the mastery targets into **4-8 topic clusters** that could be sampled by a lecture-review bot.

Each cluster should:

- be coherent
- be realistically assessable in 2-4 short exchanges
- emphasize concepts rather than wording
- be suitable for short Socratic questioning

For each cluster, provide:

- cluster name
- included targets
- why this cluster is coherent
- what kinds of questions fit it best (e.g. classification, figure interpretation, error detection, comparison, one-sentence explanation)

## 5. Evidence standards

For each target cluster, define what would count as:

- **Full evidence**
- **Partial evidence**
- **Weak or no evidence**

These standards should be based on demonstrated understanding in dialogue.
Do not require verbatim definitions.
Do not require long prose.
Accept short, imperfect English if the idea is clear.

## 6. Grade structure

Provide a grade structure that can support both:

- **whole-lecture review** if needed
- **sampled session grading** where only a subset of clusters is assessed in a given chat

Include:

- a suggested total weighting across clusters summing to 100
- guidance for how to convert sampled-cluster performance into a **session grade out of 100**
- a rule that grading should be based on the **best demonstrated mastery so far**
- a rule that uncovered material counts as not yet demonstrated
- a rule that vague buzzwords do not earn full credit

## 7. Good question forms for this lecture

List the best kinds of questions for checking understanding of this lecture.

Prefer forms such as:

- forced distinction
- classification
- figure interpretation
- identifying what is wrong in a claim
- choosing between two plausible alternatives
- one-sentence correction
- one-sentence explanation

Also list question forms that should be used sparingly or avoided.

## 8. Report-ready mastery labels

Provide short phrase labels that a bot could use in interim or final reports.

For each target cluster, give:

- mastered label
- partial label
- missing label

These should be concise and student-readable.

## 9. Rubric use notes

Write short notes for the future bot designer about:

- what the lecture seems to care about most
- where the lecture is vulnerable to superficial regurgitation
- which targets need especially careful probing
- how much fidelity to slide wording matters versus fidelity to concepts

## Additional constraints

- Use only the uploaded materials.
- Keep the rubric lecture-specific.
- Do not write generic study advice.
- Be explicit when the lecture is broad but the assessment session should stay short.
- If the notebook materially changes the lecture emphasis, say so.

---

## Second output: topics.txt  ⚠️ REQUIRED — produce this as a separate file

After completing the rubric, produce a second file called **`topics.txt`**.

This file is read directly by the lecture bot and must follow a strict format:

- One topic per line
- Each line: `<topic name> | <importance>`
- Importance must be exactly one of: `core`, `important`, `brief`
- Lines starting with `#` are comments and are ignored
- No blank lines between topics (blank lines are skipped, that's fine)
- Topic names must match the cluster names from section 4 of the rubric exactly

Example `topics.txt`:
```
Models and parameters | core
Bayes rule | core
Grid approximation | important
Prior choice | important
Conjugacy | brief
```

The bot assigns topic IDs (T1, T2, ...) automatically in file order.
Do not include IDs in this file — only names and importance.
