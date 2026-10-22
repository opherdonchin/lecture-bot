# 0001 — Lecture-bot builds its own HILD process instead of installing HILD

**Date:** 2026-10-21 · **Status:** Accepted (by the merge of [PR #15](https://github.com/opherdonchin/lecture-bot/pull/15) as [8545f82](https://github.com/opherdonchin/lecture-bot/commit/8545f82), 2026-10-21)

**Relationship to earlier decisions:** None.

**Context:** Lecture-bot is about to take on substantial new work: separate
course instances on one server and a tutor for the Probabilistic Machine
Learning course, under a deadline. The researcher wants that work scoped,
reviewed and recorded with HILD. HILD's installer accepts only new, nearly
empty repositories, and the upstream fixes and process wording lecture-bot
would use were still in unmerged draft PRs
([#11](https://github.com/Motor-Learning-Lab/HILD/pull/11),
[#13](https://github.com/Motor-Learning-Lab/HILD/pull/13)). Lecture-bot
already has established homes for project rules, design specifications and
prompt history.

**Decision:** Lecture-bot keeps an **independent build** of HILD, derived from
[HILD@92de97e](https://github.com/Motor-Learning-Lab/HILD/tree/92de97e84bd1c6b61f9e1c997765e361dc7cd458).
It owns and changes its copy through its own reviewed PRs. It records where
the copy came from ([PROVENANCE.md](../PROVENANCE.md)) but not an upgrade
baseline, and it does not reconcile with or reinstall from upstream. Later
upstream ideas may be adopted deliberately, as ordinary lecture-bot changes.
Lecture-bot's existing authorities stay where they are: `docs/` for product
design, `prompts/` (including its archive) for prompts, and a new root
`AGENTS.md` for project rules.

**Why:** An install would have required an unsupported existing-repository
path and an upgrade relationship to code that is still changing upstream.
An independent build can use the draft today and be shaped to lecture-bot
(for example its archives and public-repository constraints) without
creating reconciliation debt. Alternatives considered: waiting for upstream
to merge and support existing repositories (too slow for the course
deadline); a tracked installation with a hash manifest (reconciliation
work with no benefit, since lecture-bot will diverge deliberately).

**Consequences:** Upstream HILD fixes do not reach lecture-bot automatically.
When a lecture-bot finding is relevant to HILD, the journal records it and
the researcher decides whether to report it upstream. The HILD tooling here
is tested only by lecture-bot's own suite and by observed sessions.

**Validation:** This record is a proposal until the researcher accepts and
merges PR #15. Live agent discovery of the skills and hooks is verified
separately and recorded in the [plan](../plan.md).
