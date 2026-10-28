---
name: prepare-lecture
description: Prepare a course's lecture package from its sources by following the course's private recipe, check it, and push it inactive to the server when the researcher asks. Use when asked to prepare, build, update or install a lecture for a course instance.
---

# Prepare a lecture

Rules: [AGENTS.md](../../../AGENTS.md) (privacy, instance data outside the
repository) and the README's *Agent-prepared lectures* section for the commands.

1. **Read the recipe:** `~/lecture-bot-instances/<course>/lecture_recipe.md`.
   It says where the sources are, which files to produce and what the course
   emphasises. If the course has no recipe, stop and ask the researcher.
2. **Read the previous lecture's package** in the same instance, so the new one
   matches its form, unless the recipe says otherwise.
3. **Build** the package in `~/lecture-bot-instances/<course>/lectures/<lecture_id>/`
   and keep converted sources and drafts in `~/lecture-bot-instances/<course>/build/<lecture_id>/`,
   with a `provenance.md` naming each source and its commit or date. Never put
   course materials, transcripts or student data in this repository.
4. **Check** with `pixi run check-lecture <lecture folder>` and fix every error.
5. **Report to the researcher:** the check's output (files, topics, load-bearing
   lines), what was taught versus intended, and anything the recipe did not
   cover. The researcher confirms the load-bearing designation and reviews the
   brief or rubric.
6. **Push only when the researcher asks:** `pixi run push-lecture -- <course> <lecture_id> --dry-run`,
   then without `--dry-run`. It installs the lecture inactive. Use `--replace` only
   when the researcher asked to replace that lecture.
7. **Activation is the researcher's,** in the admin page, unless they explicitly
   ask the agent to do it.
8. Record the preparation in the journal (hashes of the installed files, no content).

If the recipe was unclear or wrong, propose an edit to it; the researcher owns it.
