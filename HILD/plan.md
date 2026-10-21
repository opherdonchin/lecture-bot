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
  carry product changes alone. [#20](https://github.com/opherdonchin/lecture-bot/issues/20) would make this part of the process.
- **Scopes:**
  - [#16](https://github.com/opherdonchin/lecture-bot/issues/16), separate course instances: approved as amended ([record](https://github.com/opherdonchin/lecture-bot/issues/16#issuecomment-6326044871)). It uses the `/srv/lecture-bot/{code,instances}` layout and migrates Statistics before PML. [PR #19](https://github.com/opherdonchin/lecture-bot/pull/19) is a draft, being reworked.
  - [#17](https://github.com/opherdonchin/lecture-bot/issues/17), PML L01 live with a hand-built package and a tutor-prompt review: approved ([record](https://github.com/opherdonchin/lecture-bot/issues/17#issuecomment-6324977298)). Not started.
  - [#18](https://github.com/opherdonchin/lecture-bot/issues/18), course-defined sources and converters: approved. Not started.
  - [#20](https://github.com/opherdonchin/lecture-bot/issues/20), versioned releases (release branches, release PRs, `CHANGELOG.md`): **awaiting approval**.
- **Releases:** tags `v0.2` (first deployment, 2026-04-21) and `v0.3.0` (`3f4979a`, what production runs). The instance work is to be `v0.4`.
- **Repository contents:** code and documentation only.
  - The replay database with session text was removed from `main` ([a517f0d](https://github.com/opherdonchin/lecture-bot/commit/a517f0d)); earlier commits keep it, by the researcher's decision.
  - The presentation, reports, course documents and Quarto were removed ([939fdca](https://github.com/opherdonchin/lecture-bot/commit/939fdca)). The talk is in `~/lecture-bot-talk/`, and the analysis and course documents are in `~/lecture-bot-instances/statistics/`.
- **Production** serves Statistics only, at `v0.3.0`, from `/srv/lecture-bot`. Do not run `publish-prod` from `main` until PR #19 merges.
- **Wiki:** four concept pages and a scripts guide, all `draft`.
- **Agent verification:** Claude Code skills and session-start hook observed working; Codex not tested.
- PML L01 materials are on `main` of the PML development repository (`~/Repositories/ProbabilisticMachineLearning`).

## Next steps

1. **PR #19 rework** (#16 PR 2a): new paths, a Statistics env example, a property test over instance examples, tag support in `publish-prod`, and a rewritten description. Then the researcher's full-track review.
2. **#17:** build the PML L01 package and post the tutor-prompt review.
3. After PR #19 merges: the Statistics migration window ([`docs/migration_v0.4.md`](../docs/migration_v0.4.md)), then the PML bring-up. The target for L01 is 2026-10-23; its window closes 2026-10-28.
4. **#20, once approved:** the process PR, then `release/v0.4`.
5. **#18** PRs A–C, after v0.4. If they're not merged by 2026-10-26, L02 is built by hand under #17.
6. **#16** PRs 2b and 2c (later version). Data access: admin UI and sync now; per-course groups when a second instructor joins.

## Open decisions

- PML public paths: `/pml` and `/pml-admin` are used in PR 2a, pending its review.
- Which PML documents may feed the tutor and rubric.
- The PML Moodle course ID and bonus-assignment setup.
- Sudo steps: the researcher runs them (per #16); whether the deploy account gets the sudoers rules in the runbook.
