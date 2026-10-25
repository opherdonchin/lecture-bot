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

## Current state — 2026-10-25

- **Where state lives:** at the researcher's direction (2026-10-21), the plan
  and journal are updated by direct commits to `main` only, so work branches
  carry product changes alone.
- **Production runs `v0.6.1` for PML and `v0.6.0` for Statistics.**
  - `v0.6.1` ([PR #36](https://github.com/opherdonchin/lecture-bot/pull/36), [PR #37](https://github.com/opherdonchin/lecture-bot/pull/37), [PR #38](https://github.com/opherdonchin/lecture-bot/pull/38)) brings: renderable math, one question per turn, conservative scoring, the five-minute warning, the tagged reply format, and backend contract `0.6.1`, which each prompt must declare.
  - **Statistics is pinned** to `/srv/lecture-bot/code-v0.6.0` by systemd drop-ins (`pin-v0.6.0.conf`). Its prompt declares no contract, so the new code would refuse it. The pin comes off when [scope issue #39, PR C](https://github.com/opherdonchin/lecture-bot/issues/39) regenerates that prompt.
  - **PML L01 is live**, with brief v2. Its bonus window closes on **2026-10-28**.
- **Scopes:**
  - **In progress:** [scope issue #31](https://github.com/opherdonchin/lecture-bot/issues/31), the PML tutor from compact briefs; PRs #36 to #38 are merged. [Scope issue #39](https://github.com/opherdonchin/lecture-bot/issues/39), both tutors generated for contract 0.6.1 and archived with provenance, is approved but not started.
  - **Approved and not started:**
    - [scope issue #20](https://github.com/opherdonchin/lecture-bot/issues/20), a `develop` branch, with `v0.7.0` as the next release;
    - [scope issue #18](https://github.com/opherdonchin/lecture-bot/issues/18), sources and converters.
  - **Delivered but still open:**
    - [scope issue #16](https://github.com/opherdonchin/lecture-bot/issues/16), separate instances; PRs 2b and 2c remain;
    - [scope issue #17](https://github.com/opherdonchin/lecture-bot/issues/17), L01 live;
    - [scope issue #26](https://github.com/opherdonchin/lecture-bot/issues/26), chat language.
- **Known limits:**
  - Score calibration is untested, because the simulated students answer too well.
  - The best-four grade formula lets a student score well without reaching the load-bearing topics. It is out of scope until scoped next week if needed.
  - The L01 load-bearing designation (T6 and T7 load-bearing, T5 feeding them) awaits the researcher's confirmation.
- **Wiki:** four concept pages and a scripts guide, all `draft`. Concept-tutor-json-replies needs updating for the tagged format.

## Next steps

1. **Watch the first live PML sessions on `v0.6.1`:** fallbacks, control characters, scoring and the five-minute warning. Then review score calibration on real answers.
2. **[Scope issue #39](https://github.com/opherdonchin/lecture-bot/issues/39):** PR A (the generator and an archive check against the contract), PR B (a PML specification and generated prompt, compared in simulation), PR C (regenerate Statistics' prompt). Then install both archives and unpin Statistics.
3. **PML L02** by 2026-10-28: by hand under [scope issue #17](https://github.com/opherdonchin/lecture-bot/issues/17)'s pattern, with a v2 brief, unless [scope issue #18](https://github.com/opherdonchin/lecture-bot/issues/18) lands first.
4. Update the wiki page Concept-tutor-json-replies.
5. **[Scope issue #20](https://github.com/opherdonchin/lecture-bot/issues/20):** create `develop`; from then on, work merges there and `v0.7.0` is the next release.
6. **Server cleanup:** remove the old unit files and `legacy.env`.

## Open decisions

- Whether to keep the tutor's message, rather than showing the fallback, when the retry still lacks a valid private note. The contract currently says fallback.
- The grade formula: scope it next week if live sessions show the problem.
- The L01 load-bearing designation.
- The PML Moodle course ID and bonus-assignment setup.
