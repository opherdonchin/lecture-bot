---
name: hild-digest
description: Audit repo understandability, stale material, duplicated rules, neglected decisions and understanding-map freshness, and propose a bounded cleanup. Use for periodic repo reviews and requests to inspect hygiene.
---

# Digest

The aim is a project the human researcher can readily understand. Authoritative criteria come from lecture-bot's [`AGENTS.md`](../../../AGENTS.md) and [HILD process](../../../HILD/process.md). **Do not duplicate a separate hygiene rulebook in this skill.**

1. **Understanding map:** when the wiki exists, pull fast-forward and check code pages for staleness using `HILD/scripts/wiki_status.py`; record missing pages and open understanding-debt issues. Create/update issues and wiki status only as authorized by the project's agreed scope. Report missing tooling rather than pretending this check ran.
2. **Review the repository:** examine tracked files (`git ls-files`), plan, decisions, code, relevant wiki pages, PRs and tests. Look for obsolete or unused files, the same rule written in multiple places, confusing names, missing test evidence, conflicting claims and changes awaiting review. Also flag language that confuses a **process outcome or human safeguard**
with a particular GitHub, skill or hook mechanism, or treats an untested
alternative as working. Check that independent-work permission debt is not
misreported as accepted and that altered older decisions have a prominent
forward link at the beginning to their successor. Retain concrete
implementation conventions rather than replacing them with vague goals. Judge them against the project's own rules.
3. **Report before making changes:** say whether the repository is getting easier or harder to understand. For each important problem, give its location, the relevant rule and a specific suggested fix. Identify things that can be simplified or removed.
4. **Follow up by agreement:** do not repair nontrivial issues merely because they were identified. Each approved fix gets a scope issue or joins an existing agreed scope. Record the audit milestone using `hild-journal`.

The process file, not this skill, remains the rule authority.
