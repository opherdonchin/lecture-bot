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

- **[Scope #14](https://github.com/opherdonchin/lecture-bot/issues/14)** (build
  lecture-bot's HILD process) is approved. Its draft
  [PR #15](https://github.com/opherdonchin/lecture-bot/pull/15) contains the
  derived HILD files, `AGENTS.md`, the Claude/Codex hooks and proposed
  [decision 0001](decisions/0001-independent-hild-build.md). The HILD
  script tests pass locally. **Live agent discovery and hook execution are
  not yet verified.**
- Production serves Statistics only, from `/srv/lecture-bot` at
  `/stats`/`/stats-admin`. The deployed code is one commit behind `main`.
  Server prompts and docs match the repository.
- Statistics runtime state (database, lectures 01–12, submissions, exports,
  logs, environment) has been copied to the private development folder
  `~/lecture-bot-instances/statistics/`, outside the clone. The clone root
  still holds stale copies of `.env`, `lectures/` and `data/`.
- PML L01's materials are on `main` of the PML development repository
  (`f8b1389`). L02's deck is in progress; L03–L12 exist only as scope
  documents.
- The lecture-bot wiki (understanding map) is enabled but not yet created.

## Next steps

1. **Researcher reviews PR #15** (read track) and merges it. Then verify in
   a fresh Claude Code session that `hild-orient` and `hild-scope` are found
   and the session-start hook output arrives, and record the result here.
2. **Propose Scope 2: separate course instances.** Instance folders, systemd
   template units, nginx paths for PML, a PML instance with its own empty
   database, isolation checks, then migration of Statistics into the same
   layout and an instance-aware development sync. The deployment part comes
   first, because L01 depends on it.
3. **Propose Scope 3: PML L01 tutor live by 2026-10-23.** Build the L01
   package (slides with notes, transcript, solved notebook, minutes,
   rubric), researcher review of the rubric topics, a pilot session and the
   Moodle bonus setup. Then a repeatable pipeline for Typst/PDF sources
   before L02 (2026-10-28).
4. After L01 sessions exist, **propose Scope 4: tutoring adapted to PML**,
   judged against replayed Statistics sessions and real PML sessions.
5. With the researcher's specific agreement, create the wiki's first page and
   set up the understanding map.

## Open decisions

- PML public paths (`/pml` and `/pml-admin` proposed).
- Which PML documents may feed the tutor and rubric.
- The PML Moodle course ID and bonus-assignment setup.
- Who runs the server steps that need sudo.
