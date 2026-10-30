---
name: prepare-lecture
description: Prepare a course's lecture package from its sources, check it with the course's lecture-bot instance, and install it switched off when the researcher asks. Use when asked to prepare, build, update or install a lecture for a course.
---

# Prepare a lecture

You may be working in the course's own repository, without lecture-bot. Everything
you need from lecture-bot comes through the
[lecture package handshake](../../../docs/lecture_package_handshake.md), and these
are the instructions it returns. The course's `AGENTS.md` says how to reach the
instance: below, `<handshake>` means the command it gives, up to and including
`lecture-package`, and `<course>` the course's name.

1. **Read what the tutor expects:** `<handshake> contract <course>`. It returns the
   contract the course's tutor prompt declares, and the rules all contracts share.
   The package you build must supply what the contract describes, and declare it
   as `package_contract` in `lecture_config.json`.
2. **Read the course's recipe,** `lecture_recipe.md`. It says where the sources are
   and what the course emphasises. If you cannot find one, stop and ask the
   researcher. The previous lecture's package is a useful example, if the recipe
   says where it is; where it disagrees with the contract, follow the contract.
3. **Build** the package in a folder of its own, wherever the recipe says. Keep
   working files apart from it, with a `provenance.md` naming each source and its
   commit or date. Do not publish course materials, transcripts or student data.
4. **Check:** put only the package's files at the top level of a `.zip`, then run
   `<handshake> check <course> <lecture_id> < package.zip`. Fix every error.
5. **Report to the researcher:** the result (topics, load-bearing lines, contract),
   what was taught versus intended, and anything the recipe did not cover. The
   researcher confirms the load-bearing designation and reviews the package. `ok`
   means the package loads and declares the right contract, not that it is good.
6. **Install only when the researcher asks:**
   `<handshake> install <course> <lecture_id> < package.zip`. It installs the lecture
   switched off. Add `--replace` only when the researcher asked to replace that lecture.
7. **Switching the lecture on is the researcher's,** on the admin page.
8. **Record what you installed:** in the course's own records, or in your report if
   it has none, give hashes of the installed files and no content.

If the recipe was unclear or wrong, propose an edit to it; the researcher owns it.
If you cannot reach the instance, hand the package to the researcher.
