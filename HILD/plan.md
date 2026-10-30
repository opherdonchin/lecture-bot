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
  - **In progress:** [scope issue #40](https://github.com/opherdonchin/lecture-bot/issues/40), agent-prepared lecture packages ([PR #41](https://github.com/opherdonchin/lecture-bot/pull/41)), superseding scope issue #18 (closed).
  - **Approved and not started:**
    - [scope issue #20](https://github.com/opherdonchin/lecture-bot/issues/20), a `develop` branch, with `v0.7.0` as the next release.
  - **Delivered but still open:**
    - [scope issue #16](https://github.com/opherdonchin/lecture-bot/issues/16), separate instances; PRs 2b and 2c remain;
    - [scope issue #17](https://github.com/opherdonchin/lecture-bot/issues/17), L01 live;
    - [scope issue #26](https://github.com/opherdonchin/lecture-bot/issues/26), chat language.
- **Known limits:**
  - Score calibration is untested, because the simulated students answer too well.
  - The best-four grade formula lets a student score well without reaching the load-bearing topics. It is out of scope until scoped next week if needed.
- **Wiki:** four concept pages and a scripts guide, all `draft`. Concept-tutor-json-replies needs updating for the tagged format.

## Next steps

1. **Watch the first live PML sessions on `v0.6.1`:** fallbacks, control characters, scoring and the five-minute warning. Then review score calibration on real answers.
2. **[Scope issue #39](https://github.com/opherdonchin/lecture-bot/issues/39):** PR A (the generator and an archive check against the contract), PR B (a PML specification and generated prompt, compared in simulation), PR C (regenerate Statistics' prompt). Then install both archives and unpin Statistics.
3. **PML L02 by agent recipe, [scope issue #40](https://github.com/opherdonchin/lecture-bot/issues/40)** (approved): [PR #41](https://github.com/opherdonchin/lecture-bot/pull/41) is in review. L02 has been prepared and checked locally; next, the researcher reviews the brief and confirms the load-bearing topics (T3, T4), then it is pushed and activated, **after the contract in [scope issue #43](https://github.com/opherdonchin/lecture-bot/issues/43)**, which the researcher wants in place first ([PR #44](https://github.com/opherdonchin/lecture-bot/pull/44) and [PR #45](https://github.com/opherdonchin/lecture-bot/pull/45), in review; review them in the order PR #41, PR #44, PR #45). Window 2026-10-28 to 11-04. The researcher could not follow the PR from its documents; [open questions from 2026-10-30](journal/2026-10-30.md#open-questions) are waiting on the researcher, along with [how a prompt and its package stay aligned](journal/2026-10-30.md#session-2--process-pr-upstream-issue-and-aligning-the-prompt-with-the-package). The process rule that documents stand alone is in [PR #42](https://github.com/opherdonchin/lecture-bot/pull/42), and the suggestion to upstream in [HILD issue #15](https://github.com/Motor-Learning-Lab/HILD/issues/15).
4. Update the wiki page Concept-tutor-json-replies.
5. **[Scope issue #20](https://github.com/opherdonchin/lecture-bot/issues/20):** create `develop`; from then on, work merges there and `v0.7.0` is the next release.
6. **Server cleanup:** remove the old unit files and `legacy.env`.

## Open decisions

- Whether to keep the tutor's message, rather than showing the fallback, when the retry still lacks a valid private note. The contract currently says fallback.
- The grade formula: scope it next week if live sessions show the problem.
- The PML Moodle grade-import setup (course ID, deadlines). The L01 submissions go to the [tutor assignment](https://moodle.bgu.ac.il/moodle/mod/assign/view.php?id=3454021); full credit before the lecture at 11:00 on Wednesday 2026-10-28, half credit before the final exam.
