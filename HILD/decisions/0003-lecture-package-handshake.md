# 0003 — One handshake between course agents and an instance; only the route changes

**Date:** 2026-10-30 · **Status:** Accepted by the researcher, 2026-10-30 ([PR #49](https://github.com/opherdonchin/lecture-bot/pull/49))

**Relationship to earlier decisions:** Modifies one provision of [decision 0002](0002-lecture-package-contract.md). Item 4 there says `check-lecture` compares a package's contract with its prompt's. That comparison is now made by the handshake's `check` and `install`, with `check-lecture` remaining for a lecture-bot clone. It still happens when a lecture is prepared and not while the app runs. Everything else in decision 0002 still applies. The handshake is how an agent gets the contract that decision describes.

**Context:** Under [scope issue #40](https://github.com/opherdonchin/lecture-bot/issues/40), an agent had to work in a lecture-bot clone, and `push-lecture` sent a script over SSH that had to know the server's folders. A course working from its own repository, or an agent with no clone, could not use it. The researcher wanted admin hooks eventually, and a process now that would be reusable and would not change much as capabilities improve.

**Decision:** Made by the researcher on 2026-10-30 ([scope issue #46](https://github.com/opherdonchin/lecture-bot/issues/46)).

1. **One [handshake](../../docs/lecture_package_handshake.md) with three operations:** `contract`, `check` and `install`, with one archive format and one result format, and a version number.
2. **Every route calls the same code** and gives the same result: a command over SSH and an admin page now, and machine-facing hooks later.
3. **A recipe is local to its course.** It says where the course's sources are and what it emphasises. It does not depend on the instance.
4. **A course needs only its recipe and a line saying how to reach the instance.** The instructions and the contract arrive through `contract`.
5. **No operation switches a lecture on.** That stays with the instructor on the admin page.

**Why:**

- **Fix the exchange and let the route change.** The researcher's aim was that later improvements should not disturb the process. Hooks would then replace SSH and an agent's token would replace its SSH access, with the operations and results unchanged.
- **A command on the server, not a script sent to it.** The sender no longer has to know the server's folders, and the contract served is the one the deployed code and prompt use.
- **Why not hooks now.** They need a production web route, a limited token and a decision about reaching them from outside the VPN. SSH already works from the researcher's machine, where agents run.
- **`.zip`, not a tar archive.** It suits both agents and a browser upload.

**Consequences:**

- A handshake change has to be deployed before agents see it, and gets a new handshake version.
- An agent that cannot reach the instance, such as one on GitHub, hands its package to someone who can.
- `push-lecture` is a thin client of `install`, so it also needs the deployed handshake.
- One fixed path remains until hooks exist: the command's location on the server, in a line of a course's `AGENTS.md`.

**Validation:** Its first real use is an agent in PML's repository preparing Lecture 3 with no lecture-bot clone.
