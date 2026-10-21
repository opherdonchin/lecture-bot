# Using HILD in this repository

HILD is a **human-supervised development process** for guiding, understanding
and reviewing scientific software produced with coding agents. Its core
requirements are explicit authorization, inspectable changes, meaningful
review and recoverable understanding. [The process](process.md) explains
those requirements; GitHub issues, PRs, skills and other installed files are
its **reference implementation**. The project's [agent instructions](../AGENTS.md)
describe its scientific goals and coding conventions.

This page shows **how to begin**; it does not replace the process rules.
The [plan](plan.md) records the project's goals and what to do next.

## Start a conversation

Open a new chat with an AI coding agent that can read and work with **this
repository**. Copy this message:

> I want to develop this repository using HILD. Please read its agent
> instructions and HILD process, and use the `hild-scope` skill to work
> with me on our next piece of work.
>
> I'm new to HILD, so I'd like to learn by going through an **onboarding
> scope** together. Start by helping me understand what we want to
> accomplish and why; then discuss the scope with me before writing any
> files or creating an issue.

**Already familiar with HILD?** Replace "onboarding scope" with the work you
actually want to do.

The [scope skill](../.agents/skills/hild-scope/SKILL.md) has a
[companion file](../.agents/skills/hild-scope/onboarding-scope.md) for
onboarding. It is read only for onboarding requests; there is no separate
onboarding skill.

## What happens during onboarding?

The agent first helps you **develop a scope together**: what would be useful
to accomplish, what to leave for later, and what success would look like.
It explains HILD as you use it, rather than presenting its internal tooling
upfront. **In ordinary supervised work**, the process requires a durable,
approved work agreement before implementation, inspectable changes and human
acceptance. If the researcher expressly delegates independent work, the
agent may go further provisionally, recording approvals deferred for later
human review; independence is not acceptance. **In the installed
GitHub implementation**, an issue records the agreement, a branch and draft
pull request (PR) keep changes visible, and you review and merge them. The
plan and journal help future sessions recover current development state.

The PR can propose a wiki page called `Process-HILD` explaining how this
particular project uses HILD. If you agree, the agent drafts that page
**after merging**, and you review it before confirming that you understand it.

**Checking installation** means checking files, settings and links.
**Validating onboarding** means observing an actual agent and researcher
following the process. These are different checks. Onboarding is recommended
for beginners, not required for every installation or update.

If a skill, script or wiki is missing, the agent should report that instead
of claiming the capability works.

For technical details of Claude Code, Codex and Copilot setup and what is
still untested, see [agent startup integrations](agent-setup.md).

See the [upstream HILD project](https://github.com/Motor-Learning-Lab/HILD)
for documentation and updates. Local HILD files may evolve with the project;
future upstream changes must be reviewed rather than blindly replacing them.
