# Lecture-bot plan

The living plan records goals, current state and ordered next steps. History
is in Git and the [journal](journal/).

## Goals

1. Develop lecture-bot under its own [HILD process](process.md), so that the
   researcher scopes, reviews and understands each change.
2. Run the Statistics course (367-1-4361) and the Probabilistic Machine
   Learning course (Advanced Statistics 2027-1, 367-2-5561) as **separate
   instances on one server**: one code checkout, with fully separate
   databases, lectures, submissions, logs and secrets.
3. Have the PML tutor live for each lecture in time for the syllabus's
   tutoring bonus. Full credit requires finishing before the next lecture;
   L01 was taught on 2026-10-21, so its window closes on **2026-10-28**.
4. Adapt lecture preparation and tutoring to PML's materials (Typst slides
   with speaker notes, solved and student notebooks, Zoom transcripts) and to
   a more mathematical, graduate course, without degrading Statistics.

## Current state — 2026-10-31

- **Where state lives:** at the researcher's direction (2026-10-21), the plan
  and journal are updated by direct commits to `main` only, so work branches
  carry product changes alone.
- **Production runs [PR #53](https://github.com/opherdonchin/lecture-bot/pull/53) (commit `f39d96e`, backend contract `0.7.0`) for PML and `v0.6.0` for Statistics.** L01 and L02 are live on the generated tutor from 2026-10-31, with packages under `pml-brief-2`.
  - **Statistics is pinned** to `/srv/lecture-bot/code-v0.6.0` by systemd drop-ins (`pin-v0.6.0.conf`). Its prompt declares no contract, so the new code would refuse it. The pin comes off under [catch-up scope issue #51](https://github.com/opherdonchin/lecture-bot/issues/51).
- **Scopes:**
  - **In progress:** [scope issue #31](https://github.com/opherdonchin/lecture-bot/issues/31), the PML tutor from compact briefs; PRs #36 to #38 are merged. [Scope issue #39](https://github.com/opherdonchin/lecture-bot/issues/39), PML's tutor generated for contract 0.6.1 and archived with provenance: PR A is merged ([PR #50](https://github.com/opherdonchin/lecture-bot/pull/50)), and PR B is next.
  - **In progress:** [scope issue #40](https://github.com/opherdonchin/lecture-bot/issues/40), agent-prepared lecture packages ([PR #41](https://github.com/opherdonchin/lecture-bot/pull/41)), superseding scope issue #18 (closed).
  - **Approved and not started:**
    - [catch-up scope issue #51](https://github.com/opherdonchin/lecture-bot/issues/51), bringing Statistics to the current version. **This is the open catch-up scope:** each PR that adds to what Statistics must catch up with adds its item there.
    - [scope issue #20](https://github.com/opherdonchin/lecture-bot/issues/20), a `develop` branch, with `v0.7.0` as the next release.
  - **Delivered but still open:**
    - [scope issue #16](https://github.com/opherdonchin/lecture-bot/issues/16), separate instances; PRs 2b and 2c remain;
    - [scope issue #17](https://github.com/opherdonchin/lecture-bot/issues/17), L01 live;
    - [scope issue #26](https://github.com/opherdonchin/lecture-bot/issues/26), chat language.
- **Known limits:**
  - Score calibration is tested only on simulated students. Some short assisted answers still score above developing.
  - The best-four grade formula stays for now; every route must reach at least four topics so that following one can't cap the grade.
- **Wiki:** four concept pages and a scripts guide, all `draft`. Concept-tutor-json-replies needs updating for the tagged format.

## Next steps

1. **The researcher posts the announcement to students.**
2. **Watch the first real sessions on the new tutor:** whether scoring is too strict for careful, slow students; how many topics sessions reach; false faults; quizzing on notation. **Then** fix [the missing prompt link](https://github.com/opherdonchin/lecture-bot/issues/54), put the redo rule in the Moodle import before any grades are imported, and prepare L03 once the transcript of the 2026-11-04 lecture exists.
3. **[Scope issue #46](https://github.com/opherdonchin/lecture-bot/issues/46)** (approved): one handshake between course agents and an instance, over SSH now, for Lecture 3 onward. [PR #47](https://github.com/opherdonchin/lecture-bot/pull/47), then [PR #48](https://github.com/opherdonchin/lecture-bot/pull/48) and [PR #49](https://github.com/opherdonchin/lecture-bot/pull/49), are in review. Then a deploy, PML's recipe moved to its repository, and a fresh agent preparing Lecture 3.
4. The researcher reviews the wiki page [Concept-tutor-json-replies](https://github.com/opherdonchin/lecture-bot/wiki/Concept-tutor-json-replies), updated for the tagged format and now `needs-review`.
5. **[Scope issue #20](https://github.com/opherdonchin/lecture-bot/issues/20):** create `develop`; from then on, work merges there and `v0.7.0` is the next release.
6. **Revise the wiki page [Concept-tutor-architecture](https://github.com/opherdonchin/lecture-bot/wiki/Concept-tutor-architecture)** (`needs-revision`) when the researcher returns to it: first ask whether the complication is in the system or in the description.
7. **Server cleanup:** remove the old unit files and `legacy.env`.

## Open decisions

- Whether to keep the tutor's message, rather than showing the fallback, when the retry still lacks a valid private note. The contract currently says fallback. It didn't occur in the last 480 simulated turns.
- Whether the grade fills too fast: one topic at 60 and three near developing gives about 88.
- The PML Moodle grade-import setup (course ID, deadlines), which must also apply the researcher's rule for redoing a tutor after its deadline ([journal](journal/2026-10-31.md)). The L01 submissions go to the [tutor assignment](https://moodle.bgu.ac.il/moodle/mod/assign/view.php?id=3454021); full credit before the lecture at 11:00 on Wednesday 2026-10-28, half credit before the final exam.
