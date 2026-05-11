# Tutor Specification History

This archive was built from distinct versions of `docs/tutor_specification.md` in commits reachable from `main`. Unmerged branch-only history was not searched. The "why" notes below are inferred from the spec diffs and the relevant commit messages.

## 2026-04-21_1.md

- Commit: `8941bd72033bbe8f25b8483ee4b5fa38d31370f8`
- Subject: `Add tutor spec + contract; update prompt generator`
- Best guess: This introduced the first structured tutor specification as a source of truth for the runtime tutor. The commit message says it added a comprehensive spec and contract to define pedagogy, interaction modes, evaluation, and runtime delegation. The content moves the tutor away from an ad hoc prompt toward an explicit A-E design with foundations, student/subject understanding, interaction repertoire, evaluation, success condition, and runtime-delegated details.

## 2026-04-21_2.md

- Commit: `19e1ac863a4cb8c457e08b5538a5fe14a2accbc9`
- Subject: `Align tutor prompt runtime contract`
- Best guess: This was a small runtime-alignment edit. The only substantive change reframes the opening behavior as the "user-visible tutor experience" opening, which suggests the goal was to distinguish what the student sees from backend/session mechanics owned by runtime.

## 2026-04-22.md

- Commit: `a2569d0ccb7ca6736763852b21f0136094365223`
- Subject: `Recreating tutor specification`
- Best guess: This rebuilt the spec into a more operational contract for prompt generation. The diff moves interaction behavior out of "Tutor understanding" into a new "Tutor cognition" section, adds an explicit turn-level decision algorithm, and introduces recorded decision logic. The likely reason was to make the tutor's internal choice process easier to translate into a runtime prompt and easier to inspect.

## 2026-04-24_1.md

- Commit: `fbd06fa6907dd691886ee968d23780c7833b889b`
- Subject: `Refactor admin and student server scripts to support dynamic root paths and reload options`
- Best guess: This appears to align the specification with the emerging private-artifact/runtime contract work in the same commit. The diff removes the concrete "Recorded decision logic" section and explicitly delegates inspectability, self-verification, private-artifact transport, schema, storage, persistence, validation, and visibility to runtime. It also changes the opening guidance from session-start behavior to initial-locus selection, reducing what the tutor spec claims to own.

## 2026-04-24_2.md

- Commit: `7271ca46a5e92fd025ddb0cb015d75e47abe5aad`
- Subject: `Refactor session export logic and enhance private artifact handling`
- Best guess: This was a large rewrite to make the tutor more inspectable and better aligned with private artifact handling. The commit message mentions exporting contract/schema files and improving validation/logging for private artifacts. The spec adds recognition/supported-use/independent-use distinctions, six attention dimensions, operational stopping definitions, mastery evidence rules, locus judgment, and an inspectability/self-verification section. The intent seems to have been to make both tutoring and evaluation traceable without turning the visible tutor into a quiz engine.

## 2026-04-26_1.md

- Commit: `a5edd2b94ca60819eba433993f1cea35755197dc`
- Subject: `More tutor prompt fiddling`
- Best guess: This version patches a specific behavioral failure mode: the tutor treating repair, procedural pushback, or repetition complaints as new mastery evidence, then continuing to re-test the same locus. The diff adds an explicit latest-message evidence gate, distinguishes new assessable content from prior accumulated evidence, strengthens repetition and tutor-error repair handling, and requires private inspectability records to describe the actual latest message and visible response.

## 2026-04-26_2.md

- Commit: `45fb80ff24ce805596159703ae1e0e6b042195f4`
- Subject: `Finalize tutor prompt updates`
- Best guess: This consolidates the previous repair/repetition fixes into a broader assessment strategy. The diff adds the "current characterization" concept, a question-value dimension, explicit latest-message roles, characterization updates, assessment targets, and high-value question checks. The likely reason was to stop low-value reconfirmation loops and make the tutor ask questions whose answers could actually change the assessment.

## 2026-05-03.md

- Commit: `53ff74aeb78be89e9bef79ac9e5f5df54b450f17`
- Subject: `Update tutor specification and regenerate runtime tutor`
- Best guess: This replaces the prior spec with a contract-conformant adaptive-challenge version. The commit message is explicit: the tutor should not detect or police AI-assisted answers; strong, fluent, unusually complete, or rapid answers should trigger higher-level conceptual work. The diff adds AI-rich learning stance, adaptive challenge modes, repetition control, breadth after strong evidence, canonical topic/runtime compliance, grade/report handoff rules, and clearer private-artifact/runtime ownership.

## 2026-05-03_1.md

- Source: current working tree snapshot before the next tutor specification update
- Based on: `docs/tutor_specification.md`
- Note: Content-identical to `2026-05-03.md`; retained as an explicit pre-update archive point before editing the live tutor specification again.

## 2026-05-03_2.md

- Source: current working tree snapshot after the adaptive conceptual review tutor revision
- Based on: `docs/tutor_specification.md`
- Best guess: This revision keeps the AI-rich adaptive challenge stance from `2026-05-03.md`, but shifts the tutor away from endless probing. It adds explicit rules for adequate evidence, consolidation, closing pressure, move-on/fatigue signals, and high-performing students so the tutor can recognize when a characterization is defensible enough for the session purpose.

### Revision notes

#### Major changes from original specification

1. Added a stronger distinction between adequate evidence and perfect/maximal evidence.
2. Added an explicit arbitration rule: further probing after adequacy requires consequential remaining uncertainty, not mere possible confidence improvement.
3. Added answer-cycle feasibility under closing pressure.
4. Added explicit treatment of move-on requests, fatigue, and loss of traction as interactional evidence.
5. Added consolidation as a named interaction mode and successful closure as a success condition.
6. Strengthened high-performing student guidance so high mastery is not withheld merely because another subtle question is imaginable.

#### Evidence status for major changes

- Adequate-vs-perfect evidence: recurrent within the same prompt and diagnostic-supported.
- Arbitration after adequate evidence: diagnostic-supported, especially the move-on/integrative-check episode.
- Answer-cycle feasibility: recurrent behaviorally and partly diagnostic-supported.
- Move-on/loss-of-traction rule: rare but high-severity enough to revise; diagnostic-supported in the clearest case.
- Consolidation mode: supported by strong counterexamples and weak closure episodes.
- Polished-answer guidance: retained mostly from original; not significantly expanded because diagnostic support was limited.

#### Issues intentionally not revised

- No backend timeout implementation changes are specified here.
- No new classifier or routing architecture is introduced.
- No detailed private-artifact schema is specified.
- No major redesign of grading weights or official grade computation is introduced.
- Polished/AI-assisted answer handling is not substantially redesigned pending a more targeted diagnostic review.

## 2026-05-11.md

- Source: current working tree snapshot under the current archiving rules
- Based on: `docs/tutor_specification.md`
- Best guess: This revision expands the tutor specification from the abbreviated 2026-05-09 archived form into the full revised adaptive conceptual review tutor specification. It preserves the AI-rich, Socratic-but-pragmatic stance while adding a full-characterization continuation pathway, highest-value remaining move logic, grade-improvement process guidance, fallback/low-traction recovery, near-100 mastery guidance, and explicit runtime delegation boundaries.

## 2026-05-11_1.md

- Source: current working tree snapshot before the next tutor prompt/specification revision
- Based on: `docs/tutor_specification.md`
- Best guess: This snapshot records the active compact adaptive conceptual review tutor specification used during the score-improvement investigation. It emphasizes lecture-grounded evidence, marginal-value breadth/depth decisions, coverage transparency, consolidation and terminal closure, plateau-cause disclosure, repetition control, high-performing student depth, and explicit delegation of official grades, reports, lifecycle, persistence, and runtime transport.
