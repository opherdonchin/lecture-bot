# 0002 — A contract aligns tutor prompts and lecture packages; the code does not judge content

**Date:** 2026-10-30 · **Status:** Proposed

**Relationship to earlier decisions:** None. [Decision 0001](0001-independent-hild-build.md) concerns the process and is unaffected.

**Context:** Lecture packages used to come from lecture-bot's own pipeline. Under [scope issue #40](https://github.com/opherdonchin/lecture-bot/issues/40), local agents outside lecture-bot prepare them. The student app checks only that a package's files exist, and a tutor prompt [described the brief it expected in prose](https://github.com/opherdonchin/lecture-bot/blob/f8574e6/prompts/pml_tutor_prompt.md#L8), so an agent had no dependable way to know what was expected, and nothing noticed when a package and a prompt drifted apart. Both existing contracts leave this open: the [Backend–Tutor Runtime Contract](../../docs/backend_tutor_contract.md) only names the lecture inputs, and the [Tutor Specification Contract](../../docs/tutor_specification_contract.md) governs how a specification is written.

**Decision:** Made by the researcher on 2026-10-30 ([journal](../journal/2026-10-30.md), [scope issue #43](https://github.com/opherdonchin/lecture-bot/issues/43)).

1. **The code does not judge a package's content.** It checks that a package loads and declares the right format. The researcher's review of the lecture is the check on content.
2. **The [Lecture Package Contract](../../docs/lecture_package_contract.md) aligns prompts and packages.** It describes the sort of information about a lecture that a tutor expects to have, not the content itself. It is fulfilled because agents read it when preparing a tutor prompt or a package.
3. **It is a separate contract with its own versions,** one format per kind of tutor.
4. **Prompt and package each declare a format, and `check-lecture` compares them when a lecture is prepared.** The backend does not compare them while running.
5. **A format lists only what a prompt or the backend actually uses.**

**Why:**

- **A separate contract, not a section of the backend contract.** Any change to that contract gets a new version, and the backend refuses prompts declaring another, so every prompt and the production code would have to move together. Lecture material changes for different reasons.
- **Not the Tutor Specification Contract.** It tells someone how to write a specification, which would not tell an agent what to produce.
- **Checked when preparing, not while running.** A backend contract mismatch breaks every turn, so refusing is right there. A package mismatch makes a poorer tutor, and refusing could take a live lecture down when a prompt changes.
- **Only what is used.** Otherwise a format accumulates requirements with no effect. The `Importance` line was one: it was required, and nothing used it.
- **Carried by hand now, generated later.** PML's prompt is hand-written until [scope issue #39, PR B](https://github.com/opherdonchin/lecture-bot/issues/39#user-content-pr-b). The generator is to read the same contract.

**Consequences:**

- An agent starts from the prompt's declaration, and a course recipe keeps only sources and emphases.
- Changing what a prompt relies on means changing the format in the same pull request, and packages for the old version must be rebuilt before they pass the check.
- The check cannot show that a format matches what a prompt really does. That stays with review of the pull request changing them.
- Statistics has no format yet: its prompt declares none, and it does not use `check-lecture`.
- The generator and the archive still need to take the contract in, under [scope issue #39, PR A](https://github.com/opherdonchin/lecture-bot/issues/39#user-content-pr-a).

**Validation:** This becomes accepted when the researcher merges the pull request introducing it. The contract itself arrives in [scope issue #43, PR 1](https://github.com/opherdonchin/lecture-bot/issues/43#user-content-pr-1). Its first real use is L02.
