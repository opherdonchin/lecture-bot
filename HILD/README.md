# HILD in lecture-bot

Lecture-bot is developed with its own version of HILD (Human-in-the-Loop
Development), a human-supervised process for building software with coding
agents. The researcher agrees on each piece of work in advance, reviews
every change before it is accepted, and keeps a durable record of goals,
decisions and what they understand.

| File | Purpose |
|---|---|
| [process.md](process.md) | How the researcher and agent work together. The authoritative rules. |
| [plan.md](plan.md) | Current goals, state and next steps. |
| [journal/](journal/) | What happened, one file per day. |
| [decisions/](decisions/) | Why we chose what we chose. |
| [templates/](templates/) | Formats for scope issues, PR explanations, journal entries, decisions and wiki pages. |
| [scripts/](scripts/) | The session-start collector and the wiki staleness checker. |
| [PROVENANCE.md](PROVENANCE.md) | Where this HILD build came from and how it differs from its source. |

Project rules (what lecture-bot is, its layout, coding style, privacy and
deployment rules) are in the root [AGENTS.md](../AGENTS.md). Agent
procedures are the `hild-*` skills in [.agents/skills/](../.agents/skills/).

## Starting a session

Open a chat with a coding agent that can work in this repository, then ask:

> We develop lecture-bot using its HILD process. Please read AGENTS.md and
> HILD/process.md, orient me with `hild-orient`, and then use `hild-scope`
> to work with me on the next piece of work.

In Claude Code, a session-start hook runs
[session_context.sh](scripts/session_context.sh) and gives the agent the plan,
latest journal, recent commits and open issues and PRs. Codex can run the same
collector through [.codex/hooks.json](../.codex/hooks.json) once you trust the
project's hooks. If no hook ran, ask for `hild-orient` explicitly; no HILD
procedure depends on a hook.

## What is verified

A file being present does not prove that an agent found or followed it. The
[plan](plan.md) records what has actually been observed in a live session,
separately for what was installed, discovered, executed and used.
