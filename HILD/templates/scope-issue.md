<!-- Title: "Scope: <short description>". Label: scope. -->

## Goal

What result this work must achieve for the researcher, and which goal in the
plan it serves. Describe the process objective, not merely the tools to use.

## What this rests on

Start with a short account of how the earlier decisions, specifications and
wiki-defined concepts work together to give this scope its background, so that
the reader does not have to remember them. Then list each one. Say so plainly
when something has no record. This section does not replace links in the text
above and below it (process, *Presentations*, the rule that a document stands alone).

| Earlier decision or fact | Where it was decided | Where it is specified | Where it is explained |
|---|---|---|---|
| ... | Issue, PR or decision record | Document or code | Wiki page and its status |

## In scope

How the work will be carried out using this project's agreed tools and records;
which files or directories it touches. GitHub PRs are the reference review
mechanism. If several PRs are needed, list them: each must be explainable in
one sitting. Give each planned PR a short name and an anchor on the line before
its description, so other documents can link to it as "scope issue #N, PR 2a":

<a id="pr-2a"></a>
**PR 2a: <what it does> (<review track>).**

## Out of scope

What this work will not do.

## Stopping points and autonomy

Name exactly which standing checkpoints this scope delegates (new classes,
helper functions, directories, dependencies, etc.). The ordinary GitHub
workflow requires approval of this issue before implementation. If the
researcher separately authorizes independent continuation, record the
mandate, the ordinary approval points deferred and how provisional
dependent work will be surfaced for later human review. Delegated execution
never constitutes acceptance of unreviewed choices or a PR.

## Done when

Checkable conditions. For scientific work, the correctness checks agreed with the
reviewer. When assessing an existing repository, explicitly require read-only
assessment before proposing any changes.
