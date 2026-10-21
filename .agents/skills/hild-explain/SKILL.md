---
name: hild-explain
description: Prepare a human-understandable pull-request explanation with code permalinks, evidence, consequences, wiki-page proposals and a review track. Use when a PR is ready for review or an implementation needs explanation.
---

# Explain

Rules: [HILD process](../../../HILD/process.md), *Presentations* and *Approval*.
Format: [PR explanation template](../../../HILD/templates/pr-explanation.md).
**Purpose:** enable the researcher to understand a proposed change, evaluate
the evidence and choose an appropriate review before accepting it. A
GitHub PR description and review track are our reference implementation.
An approved squash merge should use the PR title and final description as its commit message.

## Write

1. Commit and push the work within the agreed scope; do not rewrite a pushed PR branch.
2. Record the exact head commit, and inspect the complete diff against the actual PR base (`git diff <base-ref>...HEAD`;
do not assume a stacked PR targets `main`). Explain what **currently exists**, not the agent's original intention.
3. If the change cannot be explained in one sitting, propose splitting it.
4. Explicitly identify any **provisional work**, deferred scope/permission
   decisions and dependent changes. Explain what remains for human approval;
   passing tests does not accept those decisions. Fill the template in
   conceptual order, not file order. Include mathematics **only if it helps explain this change**, load-bearing code permalinks, evidence, untested behavior and consequences. Add a **Surprises** section only when something unexpected happened; say whether follow-up work is needed. Omit sections that have nothing to say.
5. **Wiki pages:** inspect the configured understanding map when available; list relevant pages and their statuses, then propose new/updated pages. Essential concept explanations precede review; code pages describing the merge commit follow it. If no wiki is configured, say so plainly rather than inventing links or statuses.

## Check and publish

- Render math in GitHub markdown or report that rendering was not checked. Verify links and line references.
- Beware GitHub's closing keywords: write `Closes #N` only when this PR *finishes* issue N; otherwise write `Part of #N`.
- Update the PR description to describe the whole change as it stands. Mark ready for review when the explanation is accurate.

## Acceptance and review depth

Every track (including trivial) ends with a human decision to accept or
reject the PR. A required approval-as-comment phrase is not part of HILD's
process; comments and explain-backs remain useful when they convey
substantive evidence. Only the researcher merges.

## After review

- Reply in the reviewer's original comment thread, with permalinks to fixes.
- After new commits, **rewrite the explanation in place**, updating permalinks to the new head. At its end append a dated *Changes after review* section; later rounds append, not prepend.
- **Full track:** compare the human's explain-back with the code, then clarify or change the code if they differ.
- **Fast track:** label the PR `understanding-debt`, create a follow-up issue, and set related wiki pages `needs-review` after merge.
- **During implementation:** use `hild-journal` at meaningful milestones; scope, PR status and test evidence must be recoverable before merge.
- **After the human merges:** finalize the plan/journal using `hild-journal`, then prepare agreed wiki pages using `hild-understood`.

Never claim review approval, successful tests or a merge before the actual evidence exists.
