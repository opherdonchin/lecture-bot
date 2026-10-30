# Lecture Package Contracts

**Each tutor prompt has its own lecture package contract,** saying what that prompt can rely on finding in a lecture package. Contracts are in [`docs/lecture_package_contracts/`](lecture_package_contracts/), one file each, so a course can have its own without affecting another. This document holds what they share. [Decision 0002](../HILD/decisions/0002-lecture-package-contract.md) calls them formats.

| Contract | For |
|---|---|
| [`pml-brief-1`](lecture_package_contracts/pml-brief-1.md) | The PML tutor, [`prompts/pml_tutor_prompt.md`](../prompts/pml_tutor_prompt.md) |

They sit beside the [Backend–Tutor Runtime Contract](backend_tutor_contract.md), which says what the backend and a prompt exchange, and the [Tutor Specification Contract](tutor_specification_contract.md), which says what a tutor specification must contain. [Concept-tutor-contracts](https://github.com/opherdonchin/lecture-bot/wiki/Concept-tutor-contracts) explains how they fit together, and [Concept-lecture-package](https://github.com/opherdonchin/lecture-bot/wiki/Concept-lecture-package) explains packages.

**A contract is fulfilled by being read.** Whoever writes a tutor prompt, by hand or with the [generator](../prompts/tutor_generator_prompt.md), relies on it. Whoever prepares a package, normally a local agent following the [`prepare-lecture` skill](../.agents/skills/prepare-lecture/SKILL.md), supplies what it describes. [Decision 0002](../HILD/decisions/0002-lecture-package-contract.md) records why.

## Three levels

| Level | What it settles | Who decides | How exact |
|---|---|---|---|
| [1. What the app requires](#1-what-the-app-requires-of-every-package) | What every package needs in order to run, whatever its contract | The code; this section only describes it | Exact |
| [2. What makes a contract valid](#2-what-makes-a-contract-valid) | The rules any contract must follow | The researcher, by accepting this document | Exact |
| 3. A contract, such as [`pml-brief-1`](lecture_package_contracts/pml-brief-1.md) | The sorts of information one tutor prompt expects about a lecture | The researcher, by accepting it with the prompt that uses it | The sorts of information, not their wording or layout |

**Two things a contract does not decide:**

- **A course's recipe** says where that course's sources are and what it emphasises. The contract says what the tutor needs; the recipe says how to get it from this course's materials. The researcher owns it. A recipe can ask for more than a contract does, but it cannot remove what a contract expects.
- **A lecture's content:** its topics, what is taught and how it is scored. The preparing agent proposes these, and the researcher's review is the only check on them.

## 1. What the app requires of every package

These come from the code and hold whatever the contract. The code is the authority: if this section and the code disagree, this section is wrong.

**A package must have:**

- a folder named for the lecture;
- `lecture_config.json`, valid JSON ([`load_lecture_package`](../app/lecture_loader.py));
- `rubric.md`, which the backend sends to the tutor as `rubric_text`;
- every context file marked required in the course's `lectures/config.json`.

**Topic headings in `rubric.md`,** the one place the code reads the text itself. A heading is `### T<n>. <name>` or `### T<n> — <name>` ([`parse_rubric_topics`](../app/bot_engine.py)). The app would still open a session with no headings, but it keeps scores only for known topics, so nothing could be scored. The [package check](#comparing-declarations) therefore fails without them.

**Context files reach the tutor only under the keys `bot_notes`, `slides`, `handout` and `minutes`.** A file listed under any other key loads and is then silently left out.

**Optional settings in `lecture_config.json`, which the student app reads:**

| Setting | If absent | Note |
|---|---|---|
| `active` | **The lecture is on** | Installing a package always sets it to `false`. |
| `title` | The lecture's folder name | |
| `topics` | Topics come from the headings | A copy of the headings that the app prefers to them. The package check fails if it disagrees with them. |
| `tutor_prompt_template` | The instance's prompt | Lets one lecture use a different prompt. |
| `context_files` | The course's `lectures/config.json` | |

**Everything else is ignored by the student app.** That includes other files in the folder, and other settings: `course` and `files`, which the admin pages use; `package_contract`, which only the package check reads; and `lecture_id`, which the package check requires to match the folder if present.

## 2. What makes a contract valid

A contract is valid if:

1. **It has a name ending in a version,** such as `pml-brief-1`, and its own file, `docs/lecture_package_contracts/<name>.md`.
2. **A tutor prompt declares it,** and the contract names that prompt. A prompt declares it after its backend contract line, and the backend removes both lines before the model sees the prompt:

   ```text
   Backend contract: 0.6.1

   Lecture package contract: pml-brief-1
   ```

3. **It fits level 1.** The tutor receives only `rubric_text` and the context files, so everything a contract expects must arrive through them, and the topic headings must be there.
4. **It lists only what the prompt or the backend actually uses.** If nothing uses a kind of information, it does not belong in the contract.
5. **It describes sorts of information, not a lecture's content.** It requires exact wording only where the code or the prompt depends on that wording, and says so. Any layout it shows is an example.
6. **It changes with its prompt.** When a prompt starts or stops relying on some kind of information, the contract and the prompt change in the same pull request, and the contract gets a new version and a new file.

<a id="comparing-declarations"></a>
**Comparing declarations.** A package declares the contract it was built for, as `"package_contract"` in `lecture_config.json`. The **package check**, which is [`check-lecture`](../README.md#agent-prepared-lectures), compares that with the prompt's declaration and fails if they differ or if the contract has no file. So packages built for an old version fail the check until they are rebuilt; lectures already installed are not affected. The backend does not compare them while running, because a mismatch makes a poorer tutor, not a broken one, and refusing could take a live lecture down when a prompt changes.

**What the comparison cannot do.** It catches a package built for another contract. It cannot show that a contract matches what a prompt really does, or that a package supplies what its contract describes. Those rest on review.
