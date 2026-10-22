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

## Current state — 2026-10-22

- **Where state lives:** at the researcher's direction (2026-10-21), the plan
  and journal are updated by direct commits to `main` only, so work branches
  carry product changes alone. [scope issue #20](https://github.com/opherdonchin/lecture-bot/issues/20) would make this part of the process.
- **Scopes:**
  - [scope issue #16](https://github.com/opherdonchin/lecture-bot/issues/16), separate course instances: approved as amended ([record](https://github.com/opherdonchin/lecture-bot/issues/16#issuecomment-6326044871)). It uses the `/srv/lecture-bot/{code,instances}` layout and migrates Statistics before PML. [PR #19](https://github.com/opherdonchin/lecture-bot/pull/19) ([scope issue #16, PR 2a](https://github.com/opherdonchin/lecture-bot/issues/16#user-content-pr-2a)) was **merged** on 2026-10-22 as [d5b2231](https://github.com/opherdonchin/lecture-bot/commit/d5b2231) and tagged **v0.4.0**. **Statistics migrated** on 2026-10-22 and now runs `v0.4.0` from `/srv/lecture-bot/instances/statistics/`. Fixes found during the migration are in [PR #25](https://github.com/opherdonchin/lecture-bot/pull/25).
  - [scope issue #17](https://github.com/opherdonchin/lecture-bot/issues/17), PML L01 live with a hand-built package and a tutor-prompt review: approved ([record](https://github.com/opherdonchin/lecture-bot/issues/17#issuecomment-6324977298)). The slides, handout, notebook and bot notes are built, and the [tutor-prompt review](https://github.com/opherdonchin/lecture-bot/issues/17#issuecomment-6326993214) is posted. **Blocked on the L01 Zoom transcript.**
  - [scope issue #18](https://github.com/opherdonchin/lecture-bot/issues/18), course-defined sources and converters: approved. Not started.
  - [scope issue #20](https://github.com/opherdonchin/lecture-bot/issues/20), versioned releases (release branches, release PRs, `CHANGELOG.md`): **awaiting approval**.
- **Releases:** `v0.2` (first deployment), `v0.3.0` (end of spring), `v0.4.0` (instance layout), `v0.4.1` and `v0.4.2` (deployment fixes). Production runs **`v0.4.2`** for both courses. `pixi.toml` still says 0.1.0; versioning in files comes with [scope issue #20](https://github.com/opherdonchin/lecture-bot/issues/20).
- **Repository contents:** code and documentation only.
  - The replay database with session text was removed from `main` ([a517f0d](https://github.com/opherdonchin/lecture-bot/commit/a517f0d)); earlier commits keep it, by the researcher's decision.
  - The presentation, reports, course documents and Quarto were removed ([939fdca](https://github.com/opherdonchin/lecture-bot/commit/939fdca)). The talk is in `~/lecture-bot-talk/`, and the analysis and course documents are in `~/lecture-bot-instances/statistics/`.
- **Production** serves **Statistics** (`/stats`) and **PML** (`/pml`, no lectures yet) from `/srv/lecture-bot/code` with template units. Both server Pixi copies are 0.82.0. The code is read-only to the services. The old unit files and `legacy.env` are to be removed after a day without problems.
- **Wiki:** four concept pages and a scripts guide, all `draft`.
- **Agent verification:** Claude Code skills and session-start hook observed working; Codex not tested.
- PML L01 materials are on `main` of the PML development repository (`~/Repositories/ProbabilisticMachineLearning`).

## Next steps

1. **PML bring-up** (runbook Part 2): the researcher runs the sudo steps and pastes the OpenAI key and admin password; the agent does the rest. In parallel, the researcher reviews [PR #25](https://github.com/opherdonchin/lecture-bot/pull/25); then the agent writes the wiki pages Code-deployment and Guide-adding-a-course.
2. **[scope issue #17](https://github.com/opherdonchin/lecture-bot/issues/17):** once the transcript arrives, build `transcript.md`, then the minutes and rubric, then the researcher's rubric review. Before the pilot, decide which OpenAI key and budget PML uses.
3. After PR #19 merges: the Statistics migration window ([`docs/migration_v0.4.md`](../docs/migration_v0.4.md)), then the PML bring-up. The target for L01 is 2026-10-23; its window closes 2026-10-28.
4. **[scope issue #20](https://github.com/opherdonchin/lecture-bot/issues/20), once approved:** the process PR, then `release/v0.4`.
5. **[scope issue #18](https://github.com/opherdonchin/lecture-bot/issues/18)**, [PR A](https://github.com/opherdonchin/lecture-bot/issues/18#user-content-pr-a), [PR B](https://github.com/opherdonchin/lecture-bot/issues/18#user-content-pr-b) and [PR C](https://github.com/opherdonchin/lecture-bot/issues/18#user-content-pr-c), after v0.4. If they're not merged by 2026-10-26, L02 is built by hand under [scope issue #17](https://github.com/opherdonchin/lecture-bot/issues/17).
6. **[scope issue #16](https://github.com/opherdonchin/lecture-bot/issues/16)**, [PR 2b](https://github.com/opherdonchin/lecture-bot/issues/16#user-content-pr-2b) and [PR 2c](https://github.com/opherdonchin/lecture-bot/issues/16#user-content-pr-2c) (later version). Data access: admin UI and sync now; per-course groups when a second instructor joins.

## Open decisions

- Which OpenAI key and budget PML uses: the Statistics log shows past quota exhaustion.

- PML public paths: `/pml` and `/pml-admin` are used in [scope issue #16, PR 2a](https://github.com/opherdonchin/lecture-bot/issues/16#user-content-pr-2a), pending its review.
- Which PML documents may feed the tutor and rubric.
- The PML Moodle course ID and bonus-assignment setup.
- Sudo steps: the researcher runs them (per [scope issue #16](https://github.com/opherdonchin/lecture-bot/issues/16)); whether the deploy account gets the sudoers rules in the runbook.
