# How we work — lecture-bot's HILD process

This is **lecture-bot's own development process**, built from the HILD draft at [Motor-Learning-Lab/HILD@92de97e](https://github.com/Motor-Learning-Lab/HILD/blob/92de97e84bd1c6b61f9e1c997765e361dc7cd458/HILD/process.md), which is itself a faithful adaptation of the [MotorAdpatationSBI process](https://github.com/opherdonchin/MotorAdpatationSBI/blob/main/docs/process.md). It is an independent build, not an installation: lecture-bot owns this text and changes it through reviewed PRs, without tracking upstream for upgrades. [PROVENANCE.md](PROVENANCE.md) records what was taken and how it was changed, and [decision 0001](decisions/0001-independent-hild-build.md) records why.

The aim is that the human **reviewer** stays fully on top of the software: what is being built, why, how it works, what has been checked, and what they understand less well. Agent-produced documentation supports that understanding.

## What HILD requires, and how we implement it

**HILD is a human-supervised development process, not a particular software
package or GitHub workflow.** It is meant to preserve the researcher's
authority, understanding and ability to resume work as agents help develop
scientific software. Five outcomes make the process recognizable:

1. **Agreed authority:** work has an inspectable account of its goal,
   boundaries, success evidence and delegated autonomy. Ordinary supervised
   work begins after researcher approval; explicitly authorized independent
   work may pass ordinary permission checkpoints, but the unapproved work and
   decisions remain provisional pending later human review.
2. **Inspectable change:** proposed changes stay separate from accepted work
   until the researcher can examine their purpose, effects and evidence.
3. **Meaningful review:** the researcher decides whether to accept work, with
   explanation and evidence appropriate to the change. Review intensity does
   not remove the need for human acceptance; the agent never accepts or merges
   on the researcher's behalf.
4. **Recoverable development state:** the goals, progress, decisions, tests
   and unresolved questions remain accessible beyond any one chat session.
5. **Researcher-confirmed understanding:** the agent proposes explanations
   and flags uncertainty, but only the researcher determines their current
   understanding, including withdrawing an earlier confirmation.

**GitHub issues, Git branches, draft PRs, squash merges, agent skills, hooks,
a plan, a journal and an understanding wiki are HILD's reference
implementation.** They are concrete, recommended ways to achieve those
outcomes—not the definition of the outcomes. The procedures below describe
that implementation precisely because it is the one currently developed and
tested; describing another possible implementation does **not** claim it
already works.

**How to read the rest of this document:** Process statements specify what
the human and agent aim to achieve, without depending on a particular tool.
Nearby implementation instructions say how lecture-bot achieves it;
these remain binding conventions until the researcher agrees to change them.
Some passages are wholly process or wholly implementation, where that is
clearer. Do not mechanically duplicate a process statement for every command.
Process rules themselves can also be revised through reviewed decisions.
Interlinked explanations and evidence are part of the process; GitHub
permalinks and wiki links are our concrete way of making those connections.

When the normal mechanism is unavailable or a project has established
alternatives, the agent should explain **what function the mechanism serves**,
work with the researcher on an equivalent way to provide that function, and
record the agreed choice and remaining limitations. For example, another
durable issue tracker could record a scope if the researcher can inspect and
approve the actual record and future sessions can recover that approval.
A casual conversation without a reviewable record is **not** an equivalent
replacement. Do not silently substitute tools, weaken stopping points or
claim equivalence without evidence. When compatibility issues arise, report
specific problems and demonstrated workarounds in lecture-bot's journal; the
researcher decides whether to report them to upstream HILD.

## Authority in lecture-bot

- **Requirement:** each type of authoritative guidance and development state has
  one discoverable home. In lecture-bot those homes are listed in
  *Where each thing lives* below; HILD's own files live under `HILD/`, and
  lecture-bot's established `docs/` and `prompts/` keep their authority.
- **Project rules:** the product's aims, source layout, coding conventions and
  other project-specific rules live in the root [`AGENTS.md`](../AGENTS.md).
  That document **points to** this process rather than copying it.
- **This process is local:** lecture-bot changes it freely through reviewed PRs.
  Later upstream HILD changes are ideas to consider, not updates to apply.
- **Capability status:** a procedure described here is not evidence that it
  works. See [`HILD/plan.md`](plan.md) and actual test evidence to determine
  what has been verified.


## The life of a piece of work — GitHub reference workflow

**Process:** An ordinary piece of work proceeds from a bounded agreement,
through inspectable provisional changes and evidence-based human review, to
human acceptance and a recoverable account of what was learned. Approval of
the work and approval of its eventual result are distinct. Explicitly
authorized independent work can progress ahead of ordinary permission
checkpoints, but cannot make its unapproved choices accepted by doing so
(see *Autonomy*).

**Implementation:** Our default GitHub lifecycle is:

```
scope issue ─► branch + draft PR ─► work in small commits ─► explanation
     ─► human review (appropriate track) ─► final cleanup ─► human squash merge
     ─► final plan/journal update + agreed wiki pages
          (plan and journal also updated during work)
```

1. **Scope and authorization.** Establish the work agreement and its review
   status. Normally create an issue labelled `scope`, present its actual link
   and obtain the researcher's explicit approval, recorded on the issue, before
   implementation (see *Scope agreements*). Under separately authorized
   independent work, mark any missing approval and dependent work provisional.
2. **Inspectable work.** Keep changes separate from accepted code. Use a
   branch named `<area>/<short-description>` and open a draft PR as soon as
   the branch is first pushed. The PR is the durable work-in-progress record.
3. **Small increments and recovery.** Commit small, explainable changes with
   messages saying why. Update the plan and journal at meaningful milestones
   while the PR is open; include unresolved permission points. Push each
   milestone. Do not rewrite pushed PR branch history (no force-push or rebase).
   Move superseded temporary material to `archive/` while the branch is open.
4. **Explain the current change.** Make the PR description a layered explanation
   with evidence, linked sources, consequences, and relevant/proposed wiki pages
   (see *Presentations*). Describe the current diff, not merely the original
   intent. Disclose provisional work and missing human decisions.
5. **Human review and acceptance.** Present the actual PR and ask the
   researcher to choose an appropriate depth of review. All tracks ultimately
   require human acceptance, including trivial changes; a PR comment is a
   useful durable record but not a universal prerequisite for acceptance.
   No agent may merge on the researcher's behalf (see *Approval*).
6. **Finalize reviewable contents.** Remove `archive/` and temporary material
   in the last commit before merge, preserving earlier branch commits.
7. **Human merge.** The researcher squash-merges after acceptance. On `main`,
   the resulting commit uses the PR title and final description, preserving
   the explanation in the Git history.
8. **Record and reconnect knowledge.** Finalize plan/journal after merge
   (without deferring earlier milestone records) and draft agreed wiki pages.
   Link the accepted result back to its scope, evidence and related knowledge.

**Reference-workflow exception:** Small fixes and state updates may be
committed directly to `main` when the researcher explicitly requests or
authorizes that route. Decision records always follow reviewed PRs, not direct
`main` changes (see *Decision records*).

## Scope agreements

**Process:** Scope makes the agent's authority and the expected result
inspectable. In ordinary supervised work, the human reviews and approves the
actual agreement before implementation. A standing authorization to proceed
independently is not approval of later choices beyond that agreement: such
choices and their dependent work must remain visibly provisional until the
human reviews them. Scope changes cannot become approved merely because an
agent recorded them.

**Implementation:** In the GitHub reference workflow, a scope issue follows
[the scope template](templates/scope-issue.md): the goal, what is in
and out of scope, which standing stopping points are lifted, and how we will know the
work is done.

**Ordinary GitHub scoping uses two distinct agreements.** First, the researcher agrees to
**record a proposed scope issue**. The agent creates it (if access allows),
shares its GitHub link, briefly explains what it authorizes and excludes,
and **stops**. The researcher then examines the **actual issue** and explicitly
approves it or requests changes. A conversational agreement to a summary,
including a brief "OK" to proceed with scoping, is not approval of an unseen
issue. If an issue cannot be created, present a draft and resolve the blocker;
do not begin implementation on the strength of that draft.

**Record scope approval in the issue before work starts.** The researcher may
comment there directly, or the agent may faithfully record approval given in
chat, clearly attributed to the researcher rather than written as the agent's
own approval. In either case the record identifies the agreed issue. A later
material amendment requires renewed review and approval of the revised scope.
Creating an issue and approving a PR are **different** decisions; neither
substitutes for scope approval.

Work inside an approved scope is authorized for execution, not thereby
accepted as a result. In ordinary supervised work, the agent stops and asks
before exceeding it. **Only when the researcher has explicitly authorized
independent work** may the agent pass ordinary stopping points: it records
each deferred permission and the resulting provisional work, presents the
expanded or changed scope for later approval, and does not merge or otherwise
represent provisional work as accepted. If scope changes materially, the
proposed change is linked to the original issue; the earlier approval does
not automatically extend to it. External actions that cannot be recovered
are not made safe merely by a provisional label.

### Develop scopes through dialogue

A scope agreement covers four questions: **goal** (what and why),
**boundaries** (what's in and out), **evidence** (how success will be
recognized), and **autonomy** (what the agent may do without further
permission). These describe a completed agreement, **not four questions to
ask in order**. Develop them in natural conversation, drawing on what the
researcher already said, offering relevant expertise, and reflecting back
emerging agreement. A "yes" to *working on a scope* is not approval of the
finished scope or permission to implement it.

When there is a good, reversible default, recommend it and explain its value;
mention that alternatives exist. Present a small set of alternatives when
important tradeoffs genuinely require a choice. Do not present every possible
option as a questionnaire. Keep technical investigations rigorous, but disclose
details as they become relevant to the researcher's next decision. If an
access or tooling limitation blocks an agreed action, work with the researcher
to diagnose it and choose a way forward. The completed issue may be detailed
even when the conversation that produced it was short and focused.

## Presentations

Proposals, explanations and orientations follow the same rules, so that each one is a
real check of the reviewer's understanding rather than a request for an OK.

Write so that **a researcher unfamiliar with HILD's internal terminology can follow**.
Name the actor and action rather than relying on vague references ("it", "this").
Explain unfamiliar terms when first used, give concrete examples when a procedure is
abstract, and distinguish working capabilities from proposals and untested behavior.
A procedure that is clear only to the agent still needs improvement.

1. **Purpose first.** Which goal this serves and why now. If it cannot be connected to a
   goal, say so: that is a warning sign.
2. **What you should understand.** Two or three things the reviewer should be able to
   explain by the end.
3. **Explain in layers,** using the [PR explanation template](templates/pr-explanation.md).
   Start with a plain-language summary, then discuss the important parts, evidence
   and consequences. Include mathematical background when relevant, and describe
   surprises when there were any. **Omit sections that have nothing to say.**
   The template is a default: the researcher may agree to adjust the format for
   the project's work without losing the purpose of each review.
4. **Interconnected explanations and evidence.** Link important claims,
   decisions, results, code and explanations to the material they rely on,
   so a future researcher or agent can follow and evaluate the reasoning.
   **GitHub implementation:** Every claim about code links to the exact
   lines with a GitHub permalink (`https://github.com/<owner>/<repo>/blob/<commit>/<path>#L10-L20`). Every
   other reference, to an issue, pull request, commit, file, decision record, wiki page
   or notebook cell, is a link too, in anything posted on GitHub and in every file in the
   repo. Do not rely on GitHub to make the link: a bare `#12` or commit hash links only
   in issue and PR text and never inside backticks, and nothing links by itself in a
   repository file or the wiki.
   **Say what a number refers to.** Name the kind of thing in the link text:
   - "[scope issue #16](…)", not "#16";
   - "[PR #19](…)";
   - "issue #21" for an ordinary issue.

   A PR planned inside a scope issue (for example "PR 2a") is always named with its
   scope and linked to its place in the issue: "[scope issue #16, PR 2a](…/issues/16#user-content-pr-2a)".
   For that link to work, the scope issue gives each planned PR an anchor,
   `<a id="pr-2a"></a>`, on the line before its description. GitHub adds no ids to
   headings in issues, and shows an anchor `id="pr-2a"` as `user-content-pr-2a`,
   which is why the link uses that form.
5. **Load-bearing vs boilerplate.** The walkthrough labels code as *load-bearing — read
   this* or *boilerplate — skim*.
6. **One sitting, one method.** As our current *process* limit, if a change
   cannot be explained in about fifteen minutes, it is too big and gets split.
   The researcher may explicitly adjust this limit as the process evolves. A change introduces one method at a time. A
   method the reviewer has not been shown before comes with its background (a concept
   page in the wiki) and with a check against a result the reviewer already trusts,
   such as a published result or existing code, before anything is built on it.
7. **"I don't get it" is always a good answer.** It means the explanation or the code
   needs work, never that the reviewer failed.
8. **Math that survives GitHub's markdown.** Display math goes in fenced ` ```math `
   blocks, whose content markdown leaves alone. In `$...$` and `$$...$$`, markdown eats
   a backslash before punctuation (`\,` `\;` `\!` `\{` become `,` `;` `!` `{`) and
   mangles `<`; avoid them there (write `y_{1:t-1}`, not `y_{<t}`, and `\lbrace`,
   `\rbrace` for braces). Check that with `gh api markdown` when in doubt. GitHub also
   refuses some macros, `\operatorname` among them (write `\mathrm{...}`); that error
   appears only in the browser, so `gh api markdown` cannot show it.
9. **An explanation always describes the change as it now stands.** After review, the
   explanation is rewritten in place, not patched: a reader should never have to combine
   an old description with a list of amendments. What changed in response to review is
   recorded at the very end, in a dated *Changes after review* section; each later round
   appends another.

10. **Wiki pages are part of an explanation.** Every explanation has a *Wiki pages*
    section with two lists. *Relevant pages:* each existing wiki page the change relies on
    or affects, with how it is relevant and its status, so the reviewer can see which
    background they have confirmed and which they have not. *Proposed pages:* each page
    the change calls for, new or to be updated, with what it would cover. A concept page
    the reviewer needs in order to follow the change is written before review (rule 6)
    and listed as relevant. The other proposed pages are written once the reviewer
    agrees to them; code pages after the merge, because they record a `main` commit.

| Presentation | When | Where |
|---|---|---|
| Proposal | Before nontrivial work | The scope issue |
| Explanation | Before merge | The PR description |
| Orientation | Start of every session (automatic) | Chat |
| Journal | At milestones | `HILD/journal/` |


## Approval

**Process:** Producing work is not accepting it. The researcher decides
whether to accept every change, including a trivial one. Explanation and
review depth are proportional to the change; they do not substitute for
acceptance. Independent work beyond approved authority is provisional until
the researcher reviews the deferred choices and the consequences built on
them. Acceptance of a downstream result cannot silently erase that debt.

**GitHub implementation:** The agent provides the actual PR link and current
explanation and requests review. The researcher chooses a track; the PR
description proposes one. PR comments can document the track and discussion,
and the agent may faithfully attribute an approval received in chat, but a
specific comment phrase is **not** mandatory for PR acceptance. The researcher
alone approves the final merge and performs it. A draft PR or merely sending
a status link does not constitute human review.

| Track | Appropriate for | Review expected | Acceptance |
|---|---|---|---|
| **Trivial** | Typos, straightforward wording changes, pinned dependency bumps, `explore_` notebooks | Brief inspection; no formal explain-back | Researcher accepts and merges |
| **Read** | Documentation, process text, decision records | Read the change and raise questions | Researcher accepts and merges |
| **Full** | Code and changes whose behavior is not evident from text | Explain back what changed and why; agent checks against actual behavior | Researcher accepts and merges |
| **Fast** | Code when immediate detailed review is not worthwhile | Confirm purpose, inputs/outputs and affected areas | Researcher accepts and merges, with visible understanding debt |

On the full track, compare the researcher's explain-back with the
implementation. A mismatch means the explanation or change needs work.
On the fast track, label the PR `understanding-debt`, create a follow-up
issue and mark related wiki pages `needs-review`. The conservative trivial
category may be recalibrated by the researcher. Review depth, explicit
execution permission, PR acceptance and merging are separate decisions.

## Understanding map

**Process:** Maintain a linked, recoverable map of the researcher's current
understanding and uncertainties. The researcher alone judges what they
understand; they may withdraw an earlier confirmation at any time, and that
current judgment overrides a stale page status. An agent's draft, status
checker, or past confirmation cannot certify present understanding.

**Implementation:** The **understanding map** records what the reviewer understands. In lecture-bot it is the repository's [GitHub wiki](https://github.com/opherdonchin/lecture-bot/wiki), cloned into the gitignored `wiki/` directory. The wiki is enabled but **not yet created**: GitHub requires its first page to be made in the browser. Creating it is a separate, approved step (see the [plan](plan.md)).

The understanding map is never authoritative. It may restate and summarize what the repo says, in
the reviewer's terms, to make the repo easier to approach; the repo is the source. When
the two drift apart, that is a signal to slow down and check that the reviewer is still
on top of the work, and that it is making real progress rather than only producing code.

**Page kinds.** A page's name starts with its kind (`Code-environment`,
`Concept-kalman-filter`), and `Home` and the sidebar group pages by kind.

| Kind | What it holds |
|---|---|
| `code` | One load-bearing module or finalized notebook: *What it does*, *How and why*, *How it fits the larger project*, *Invariants and pitfalls* (what must stay true if the code changes, and the mistakes that are easy to make). Records the files it covers and the `main` commit it describes. |
| `concept` | An idea the code relies on, linking code pages to the math. |
| `process` | How we work and how the tooling works: explanation of the process, as opposed to the project's content. |
| `guide` | A reading path: which pages to read, in what order, to understand an area. |
| `resource` | A background source: what it is, a link, and why it matters here. |

New kinds are added here when a real page needs one. Pages use the [code-page template](templates/wiki-code-page.md) and [general-page template](templates/wiki-page.md); the [new-wiki procedure](../.agents/skills/hild-understood/new-wiki.md) describes creating the wiki.

**Statuses.**

| Status | Set by | Meaning |
|---|---|---|
| `not-written` | nobody | No page exists yet. Another page links to it, or a pull request proposes it. |
| `stub` | agent | A page that exists only as a placeholder, still to be written. |
| `draft` | agent | Written by the agent; the reviewer has not confirmed it. |
| `understood` | reviewer only | The reviewer currently confirms it; this may be withdrawn later. |
| `needs-revision` | either | The reviewer has read it and it did not do its job, or the agent knows it falls short. The agent owes a rewrite. |
| `needs-review` | either | Merged on the fast track, or the reviewer is no longer sure. |
| `stale` | script | The code changed materially since the commit the page describes. |

`not-written` is the one status that is not recorded on a page, since there is no page:
it is what an explanation's *Wiki pages* section says of a page that is linked or
proposed and does not exist.

`needs-revision` and `needs-review` point in opposite directions: the first says the
page must change, the second that the reviewer must read it again.

In the reference implementation, a generated *Status board* page lists the pages that exist by status, and the
`not-written` pages that some page links to.

**Who writes.** The agent drafts pages; the reviewer edits them, in the browser or
through the agent. When the researcher retracts an earlier `understood`
judgment, update the page status (normally to `needs-review` or
`needs-revision`, as appropriate) rather than treating the prior status
as authoritative.

**Staleness.** A script compares the commit each code page describes with `main`;
pages whose code has changed materially become `stale`, and an issue is opened to
review them. Code pages record `main` commits (code as it stands); journals and
explanations may link to branch commits.

**When the wiki is committed and pushed.** The wiki has no pull requests; its history is
its record. When a git-backed understanding map is configured, the agent pulls it before touching it (to pick up the reviewer's browser edits) and commits and pushes it straight after every change it makes. Nothing is left
uncommitted in the local clone. The session-start collector reports anything unpushed.

## Where each thing lives, and how to change it

**Process:** Preserve one authoritative source for each rule, decision,
procedure and current-state record, with links between related knowledge
instead of duplicated prose.

**Implementation:** Every rule, format and procedure has exactly one authoritative home. Other places
point to it; they never restate it.

| What | Authoritative home in lecture-bot |
|---|---|
| Why the project exists; layout; coding, privacy and deployment rules | [`AGENTS.md`](../AGENTS.md) |
| How reviewer and agent work together | `HILD/process.md` (this file) |
| Step-by-step agent procedures | `hild-*` skills in [`.agents/skills/`](../.agents/skills/) (Claude Code reads them through the `.claude/skills` link) |
| Formats for scope issues, PRs, journal, decisions, understanding pages | [`HILD/templates/`](templates/) |
| Machinery, including scripts | [`HILD/scripts/`](scripts/), tested in [`tests/hild/`](../tests/hild/) |
| Agent-specific hooks | `.claude/settings.json`, `.codex/hooks.json` |
| Product, tutor and grading design | [`docs/`](../docs/README.md) |
| Runtime and generation prompts, and their history | [`prompts/`](../prompts/) |
| Current goals, state and next steps | [`HILD/plan.md`](plan.md) |
| What happened | [`HILD/journal/`](journal/) |
| Why we chose what we chose | [`HILD/decisions/`](decisions/) |
| What the reviewer understands | the [lecture-bot wiki](https://github.com/opherdonchin/lecture-bot/wiki) |
| What remains unvalidated or insufficiently understood | GitHub issues, with the `understanding-debt` label |

To change something:

1. Find its authority in this table and edit it there.
2. A new coding or hygiene habit goes in `AGENTS.md`; a change to how
   human and agent work together goes here. Skills point to rules and templates
   rather than restating them; a skill changes when the **procedure** changes.
3. If something seems to need saying in two places, make one a pointer.
4. Rule and decision changes arrive through a reviewed PR on the **read** track.
   Audits must look for rules that have crept into secondary locations.

## How the tooling works

The process above defines **what** the human and agent must do. Tooling makes
those steps easier to remember and carry out; it does not create new rules.
There are three different kinds of supporting tool:

- **Skills are instructions for the agent.** For example, the orientation skill
  says how to turn repository facts into a short report for the reviewer.
  The skill points to the rules here and to a template where appropriate.
- **Scripts do mechanical work.** They collect or compare information that
  would be tedious or error-prone for an agent to assemble by hand. They are
  not the source of process rules.
- **Hooks connect a supported agent event to an action.** For example, a
  Claude Code session-start hook runs a script automatically. An agent without
  that hook can still perform the same work by following the skill manually.

**Concrete example — starting a session.** When Claude Code starts a session
in lecture-bot, its hook runs [`session_context.sh`](scripts/session_context.sh).
That script collects the current branch, plan, latest journal, recent commits,
open issues and pull requests, and wiki status. Claude then follows the
`hild-orient` skill: it explains what needs human attention, what changed,
and what to do next. The script supplies facts; the skill supplies steps;
this document supplies the governing rules.

**Concrete example — checking understanding.** Code pages in the wiki record
which files they explain and the `main` commit they describe. The
[`wiki_status.py`](scripts/wiki_status.py) script compares those files with
current code and flags pages that may be outdated. The `hild-digest` and
`hild-understood` skills tell the agent how to report or follow up; only the
reviewer can confirm a page as `understood`.

| Skill | Purpose |
|---|---|
| [`hild-orient`](../.agents/skills/hild-orient/SKILL.md) | Present a session-start status and questions for the reviewer |
| [`hild-scope`](../.agents/skills/hild-scope/SKILL.md) | Prepare an agreed scope before nontrivial development |
| [`hild-explain`](../.agents/skills/hild-explain/SKILL.md) | Prepare a layered PR explanation for human review |
| [`hild-journal`](../.agents/skills/hild-journal/SKILL.md) | Record milestones and refresh the plan |
| [`hild-understood`](../.agents/skills/hild-understood/SKILL.md) | Draft or revise an understanding-map page |
| [`hild-digest`](../.agents/skills/hild-digest/SKILL.md) | Review repository hygiene and understanding debt |

**Verification:** a skill's presence does not establish that an agent
discovered or followed it, and a configured hook does not prove it ran.
What has actually been observed belongs in the [plan](plan.md) and journal.
Until a tool is verified, the agent follows the rules manually rather than
pretending automation exists.

## Durable state files

**Process:** Goals, decisions, significant results, open questions, progress
and any deferred human decisions must survive a chat and remain connected to
the evidence that produced them. Keep the current plan distinct from the
factual history of how work developed.

**Implementation:** State lives in files, not in chat.

The agent cannot tell when a session will end, so the plan and journal are updated at
**milestones**, not at the end:

- a sub-step of agreed work is finished and pushed;
- a PR is opened, marked ready, or merged;
- a significant result, finding or dead end;
- a decision is made or a deferred authorization creates provisional work;
- context is compacted: hooks ask the summary to keep unrecorded milestones and remind
  the agent to record them straight afterwards;
- at the start of a session, if orientation finds the last session's work missing from
  the journal, the agent fills it in from git history before anything else.

### Plan — `HILD/plan.md` (default)

- **What:** current goals, current state, and the ordered next steps. Nothing else.
- **When to update:** at milestones (above), whenever a goal, the state, or the next steps
  change.
- **How:** rewrite in place; the old versions are in `main`'s history (see *Git and
  GitHub*).
- **When to read:** at the start of every session.

### Journal — `HILD/journal/YYYY-MM-DD.md` (default)

- **What:** a factual log of the work, including decisions, links to evidence,
  provisional actions and deferred permission points where relevant.
  One file per day; a second session on the same day adds a new
  `## Session N` section.
- **When to update:** at milestones (above). Each update adds to the current session's
  section, so the entry is always complete up to the last milestone.
- **Format:** [the journal-entry template](templates/journal-entry.md).
- **When to read:** the latest entry at startup; earlier entries when resuming a thread
  of work (search by topic).
- Entries are history: do not rewrite past entries except to fix errors, and say so.


### Decision records — `HILD/decisions/NNNN-short-title.md` (default)

- **Process:** Record consequential choices and their reasoning so future
  work can recover what is currently decided and why. A decision is not
  retroactively rewritten to present a changed judgment as the original one.
  A *new decision* may **modify**, **overrule** specific provisions of, or
  **replace** an earlier decision. It must link the predecessor, state the
  precise effect and what still applies, and explain its reasoning in full.
  An earlier accepted decision remains historical evidence even when its
  current applicability changes.
- **Reference implementation:** Decisions use numbered files
  `HILD/decisions/NNNN-short-title.md` and
  [the decision-record template](templates/decision-record.md). The agent
  drafts them and the researcher accepts them by reviewing and merging a
  PR on the *read* track. Never commit decisions directly to `main`.
- **Forward notice:** In the same PR that introduces the successor, edit
  the **beginning** of every affected older record to show a prominent
  link to the proposed successor and summarize its intended effect. Keep
  the historical content intact. Distinguish *proposed* supersession
  (not yet operative) from *accepted* supersession. Upon acceptance, the
  older record's opening notice identifies any partial or full supersession
  and links to the accepted successor. Do not bury this notice at the end.
- **Current authority:** Update the operative rule in this `process.md`
  (or the relevant project's rules) when the successor is accepted; never
  require agents to resolve conflicting historical decisions to know the
  current rule. A proposed PR's changes are not accepted authority until
  human review/merge.
- **When:** Draft a record for decisions constraining future work—tools,
  models, conventions and rejected alternatives worth remembering.
  Minor choices go in the journal. Read relevant existing titles and
  successor notices before deciding in an area.


## Autonomy

**Process:** Delegation of execution and human approval are different.
Ordinary supervised work proceeds inside an approved scope and stops at
unapproved boundaries. When the researcher **explicitly authorizes
independent work**, the agent may keep developing beyond ordinary permission
checkpoints. Such permission authorizes *continuation*, not the unreviewed
choices, scope expansions or dependent results as accepted HILD work. The
agent records what was done, which ordinary approvals were bypassed and
what later work depends on those choices. All of that remains **provisional**
until the researcher works through it and decides what to accept, revise or
reject. Later work cannot bootstrap approval for its own prerequisites.

**Reference GitHub conventions:**

- **Routine, without additional permission:** reads, searches, local edits,
  running notebooks/tests, normal Git operations and creating/commenting on
  issues and PRs within the existing scope.
- **Ordinary stopping points:** ask before introducing new classes or helper
  functions, new directories or auxiliary-file kinds, dependencies,
  destructive/hard-to-reverse changes and external side effects beyond
  this repository's issues, branches and PRs, unless the approved scope
  explicitly delegates them.
- **Independent work:** record every deferred checkpoint, agent choice,
  affected commit and dependent work in the journal's `Permission points`
  and surface them in the PR explanation and next session orientation.
  Keep the relevant PR draft/provisional; do not merge, publish as accepted,
  or erase deferred approvals. Project-local destructive edits may be made
  provisionally under a specifically authorized independent-work mandate,
  with recoverable Git history. Irreversible effects on external systems
  are not made reversible by labeling them provisional; seek explicit
  authority for these separately.
- **Decision style:** when a tradeoff is not obvious, explain briefly and
  prefer the simpler, less stateful option, while recording provisional
  choices where approval is deferred.

## Git and GitHub — reference implementation details

**Process:** Proposed work must remain inspectable, recoverable and linked
to its scope and explanation, and only human-accepted changes may become
accepted project state.

**Implementation:** These are the currently supported, binding Git-based
conventions, not an assertion that a GitHub feature is intrinsically
required for human-supervised development.

- Before starting, decide whether the work needs a branch, say what was decided, and
  commit any pending work.
- Branches merge into `main` only with the reviewer's approval, through a pull request,
  as a squash merge.
- Never stop work while waiting for a merge: continue on the branch or start the next
  piece of work.
- All work must be recoverable on another machine: push at every milestone.
- **Superseded material** — the one rule, referred to elsewhere:
  - on a branch, move it to `archive/` so it stays at hand while the work continues;
  - the final commit before merge deletes `archive/`; the material stays reachable
    through the PR's commits;
  - on `main`, delete superseded files rather than keeping `old` copies; git history is
    the archive. Update or remove references in the same change.
  - Exception: decision records are kept and marked superseded.
  - Exception: [`prompts/archive/`](../prompts/archive/) and
    [`docs/archive/`](../docs/archive/) are deliberate histories of the
    runtime tutor prompt and specification, not superseded drafts. Keep them.
- Commit messages explain why, not just what.
- When the agent acts through the reviewer's GitHub account, its comments start with
  **🤖 Claude:** (or **🤖 Codex:**) so it is clear who wrote what.
- Replies to review comments go in the comment's own thread, with permalinks to the fix.
