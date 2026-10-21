---
name: hild-orient
description: Present a concise start-of-session orientation about project progress, pending human reviews, understanding debt, and next work. Use on session start or when asked where the project stands.
---

# Orient

Rules: [HILD process](../../../HILD/process.md), *Presentations* and *Durable state files*. Resolve any configured authoritative paths before acting.

**Purpose:** restore accurate shared context so the researcher can choose
what needs attention. The session hook and shell collector are helpful
reference mechanisms, not prerequisites for doing this orientation.

1. **Find out what happened.** If a session-start hook has provided information, use it. Otherwise read the plan, latest journal, recent Git changes, open issues and PRs, and available wiki status. The reference `HILD/scripts/session_context.sh` (once installed) can supply these facts; do not assume it has run or exists.
2. **Check what is missing.** Note completed work that the journal doesn't mention and wiki edits that haven't been published. Explain any gaps, then use `hild-journal` or `hild-understood` when authorized to repair them.
3. **Present** in about fifteen lines, leading with what needs the human:
   - **Needs you:** PRs awaiting review and proposed approval tracks, scope
     issues awaiting agreement, **deferred approval points and dependent
     provisional work** from independent development, questions, wiki pages
     to read.
   - **Where we are:** current goal and state.
   - **Since last time:** material changes, with links.
   - **Understanding debt:** code the human has not yet reviewed fully and wiki pages that may no longer match the code.
   - **Next:** the next plan step and what is proposed now.
4. **Wait in ordinary supervised work.** Do not begin unapproved nontrivial
   work before the reviewer responds. When an explicit independent-work
   mandate covers continuing development, the agent may proceed, but
   preserve all unreviewed choices and dependent work as provisional.

A hook firing is not evidence that orientation was delivered or understood. If an information source is unavailable, say so rather than filling it in from memory.
