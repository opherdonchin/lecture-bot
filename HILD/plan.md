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

## Current state — 2026-10-21

- **[Scope #14](https://github.com/opherdonchin/lecture-bot/issues/14) is complete**
  ([PR #15](https://github.com/opherdonchin/lecture-bot/pull/15), merged as
  [8545f82](https://github.com/opherdonchin/lecture-bot/commit/8545f82)).
  [Decision 0001](decisions/0001-independent-hild-build.md)'s status line is
  corrected to *Accepted* in PR 2a.
- The repository allows squash merges only, with automatic branch deletion.
- **Agent verification:**
  - Claude Code *discovered and used* the `hild-*` skills through `.claude/skills`.
  - Claude Code's session-start hook *executed and used*: observed in session 2 on 2026-10-21, whose orientation was built from the hook's output.
  - Codex: not tested.
- **Scopes:**
  - [#16](https://github.com/opherdonchin/lecture-bot/issues/16), separate course instances: **approved** ([record](https://github.com/opherdonchin/lecture-bot/issues/16#issuecomment-6310738318)). PR 2a is in progress on `deploy/pml-instance`.
  - [#17](https://github.com/opherdonchin/lecture-bot/issues/17), PML L01 live with a hand-built package: rewritten and amended (now including a tutor-prompt review); **awaiting approval**.
  - [#18](https://github.com/opherdonchin/lecture-bot/issues/18), course-defined sources and a converter family: **approved** ([record](https://github.com/opherdonchin/lecture-bot/issues/18#issuecomment-6320392819)). It replaces #17's former part 3b.
- **Production** serves Statistics only, from `/srv/lecture-bot` at
  `/stats`/`/stats-admin`, at `3f4979a`, behind `main`. The server checkout
  was used for development (its history is commits made in place, never
  pulls). The old rsync `publish-prod` could delete server lectures and
  server-only files; PR 2a replaces it with a git fast-forward, and
  `publish-prod` must not be run from `main` until PR 2a merges.
- The deploy account (`opher`) has no passwordless sudo on the server, so
  service restarts need the sudoers rules in the PR 2a runbook.
- Statistics runtime state is copied to `~/lecture-bot-instances/statistics/`.
  The clone root still holds stale `.env`, `lectures/` (01–09) and `data/`.
- PML L01's materials are on `main` of the PML development repository
  (`f8b1389`). L02's deck is in progress.
- The lecture-bot wiki (understanding map) is enabled but not yet created.

## Next steps

1. **PR 2a ([#16](https://github.com/opherdonchin/lecture-bot/issues/16)):** open the draft PR and get the researcher's full-track review. After merge, the researcher runs the sudo steps of runbook section 24 and the agent the rest, bringing up `/pml`; then the first git-based `publish-prod`.
2. **[#17](https://github.com/opherdonchin/lecture-bot/issues/17), once approved:** build the L01 package, review the tutor prompt, then rubric review, pilot and Moodle dry run, by 2026-10-23.
3. **[#18](https://github.com/opherdonchin/lecture-bot/issues/18):** PRs A–C. If not merged by 2026-10-26, L02 is built by hand under #17.
4. **PR 2b ([#16](https://github.com/opherdonchin/lecture-bot/issues/16)):** enforced isolation. It must also cover tutor-prompt activation, which rewrites the shared `prompts/` files from any instance's admin app.
5. After real PML sessions, propose a PML-tutoring scope (runtime prompt, grading calibration), using the gaps listed in #17's tutor-prompt review.
6. With the researcher's specific agreement, create the wiki's first page.

## Open decisions

- PML public paths: `/pml` and `/pml-admin` are used in PR 2a, pending its review.
- Which PML documents may feed the tutor and rubric.
- The PML Moodle course ID and bonus-assignment setup.
- Sudo steps: the researcher runs them (per #16); whether the deploy account gets the sudoers rules in the runbook.
- Server-only files in `/srv/lecture-bot` (`reports/`, `presentations/`, the grading-policy PDF and grade calculator): keep there, or move into an instance folder.
