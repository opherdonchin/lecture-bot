You are being asked to run a disciplined, staged analysis of one exported tutor conversation and its associated design artifacts.

Your job is not to jump to the end. Your job is to reproduce, step by step, a constrained reasoning workflow, while strictly controlling what information is available at each stage.

You must produce a concrete artifact for each stage before moving to the next stage. Each later stage must explicitly use the earlier artifact(s) as input.

Do not skip stages.
Do not collapse stages.
Do not revise earlier-stage conclusions merely because later-stage documents reveal more.
Do not use documents that are not allowed for the current stage.
When a later-stage document changes your view, record that as a comparison against the earlier-stage artifact rather than silently rewriting history.

## Goal

Given an export that includes:
- a tutor conversation / chat transcript
- a runtime tutor prompt
- decision-logic logs or private diagnostic artifacts, if present
- a tutor specification
- a tutor specification contract
- possibly additional contracts, schemas, and backend/runtime artifacts

perform a staged analysis that answers:

1. What does the tutor do behaviorally?
2. What weaknesses in the runtime prompt would you predict purely from the behavior?
3. To what extent do those predicted weaknesses actually appear in the runtime prompt?
4. What are the smallest high-leverage changes worth carrying into specification review?
5. What should the diagnostic logs show if the explanation is correct?
6. Do the diagnostic logs support, weaken, or complicate that explanation?
7. To what extent are the relevant weaknesses already present in the tutor specification?
8. How should the tutor specification be revised to address the supported weaknesses?
9. Is the revised specification aligned with the tutor specification contract?

## General rules

1. At each stage, use only the allowed sources for that stage.
2. Before each stage, explicitly list:
   - allowed sources
   - forbidden sources
   - artifacts from prior stages that you are allowed to use
3. Produce the stage artifact as a standalone markdown file.
4. After each stage artifact, produce a short gate note stating whether the stage is complete and what exact inputs will be carried into the next stage.
5. Do not move to the next stage until the current artifact is complete.
6. When the instructions say “purely behavioral,” do not critique contract structure, schema design, generator design, or implementation mechanics.
7. When the instructions say “predict prompt weaknesses,” do not read the runtime prompt yet.
8. When the instructions say “diagnostic log hypotheses,” do not read the logs yet.
9. When the instructions say “specification review,” do not propose fixes until the designated revision stage.
10. Keep the analysis focused on the specific problem of tutor behavior around:
   - deciding whether to stay on a point or move on
   - recognizing when evidence is enough for now
   - handling repetition, loss of traction, and student pushback
   - whether the tutor’s internal diagnostics explain its visible behavior
11. Be explicit about uncertainty. If a stage conclusion is only a prediction, label it as a prediction.

## Output directory and required artifacts

Create an output directory:

analysis_outputs/

Create these files in order:

1. analysis_outputs/01_behavioral_review.md
2. analysis_outputs/02_predicted_prompt_weaknesses.md
3. analysis_outputs/03_prompt_comparison.md
4. analysis_outputs/04_priority_changes.md
5. analysis_outputs/05_diagnostic_log_hypotheses.md
6. analysis_outputs/06_diagnostic_log_check.md
7. analysis_outputs/07_specification_review.md
8. analysis_outputs/08_revised_tutor_specification.md
9. analysis_outputs/09_contract_alignment_check.md
10. analysis_outputs/10_final_summary.md

Each file must be substantive and self-contained.

## Stage 1 — Pure behavioral review

### Allowed sources
- the tutor conversation / transcript only

### Forbidden sources
- runtime tutor prompt
- diagnostic logs / private artifacts
- tutor specification
- tutor specification contract
- backend/runtime contract
- schemas
- generator prompts
- any earlier or later analysis files except none yet

### Task
Evaluate the tutor purely behaviorally.

Focus on:
- what the tutor does well
- what it does badly
- whether it recognizes when a student has already shown enough understanding
- whether it becomes repetitive or nitpicky
- how it handles irritation, disengagement, or pushback
- how it manages closure and topic switching

Do not yet infer prompt wording.
Do not yet critique contracts or specifications.
Do not yet suggest fixes.

### Required artifact structure
Create 01_behavioral_review.md with sections:
- Scope and source restriction
- Behavioral strengths
- Behavioral weaknesses
- Most important behavioral failure modes
- Overall behavioral verdict
- Open questions to carry forward

## Stage 2 — Predicted prompt weaknesses

### Allowed sources
- the tutor conversation / transcript
- the tutor specification contract only
- 01_behavioral_review.md

### Forbidden sources
- runtime tutor prompt
- diagnostic logs / private artifacts
- tutor specification
- backend/runtime contract
- schemas
- generator prompts
- later-stage artifacts

### Task
Predict what weaknesses you expect to find in the runtime tutor prompt, based on the observed behavior and the structural categories suggested by the tutor specification contract.

Important:
- Do not critique the contract itself.
- Use the contract only as a map of where prompt-shaping commitments are likely to live: foundations, student model, decision architecture, interaction modes, evaluation, success condition, delegated areas.
- The goal is to prepare for reading the prompt.

### Required artifact structure
Create 02_predicted_prompt_weaknesses.md with sections:
- Scope and source restriction
- Behavioral facts driving the prediction
- Predicted weaknesses in the prompt
- Expected location of each weakness in prompt logic
- Priority of predicted weaknesses
- What would most strongly confirm or disconfirm the prediction

## Stage 3 — Compare prediction against runtime prompt

### Allowed sources
- runtime tutor prompt
- 01_behavioral_review.md
- 02_predicted_prompt_weaknesses.md

### Forbidden sources
- diagnostic logs / private artifacts
- tutor specification
- tutor specification contract
- backend/runtime contract
- schemas
- later-stage artifacts

### Task
Read the runtime tutor prompt and compare it against the predictions from Stage 2.

Do not fix the prompt.
Do not yet propose specification changes.
Just identify which predicted weaknesses are actually present, which are absent, and which are only partially present.

### Required artifact structure
Create 03_prompt_comparison.md with sections:
- Scope and source restriction
- Short description of the prompt’s governing structure
- Confirmed predicted weaknesses
- Partially confirmed predictions
- Disconfirmed predictions
- Additional prompt weaknesses discovered only after reading the prompt
- Most relevant weaknesses for the current problem

## Stage 4 — Smallest high-leverage changes

### Allowed sources
- 01_behavioral_review.md
- 02_predicted_prompt_weaknesses.md
- 03_prompt_comparison.md

### Forbidden sources
- tutor specification
- tutor specification contract
- backend/runtime contract
- schemas
- diagnostic logs / private artifacts
- raw runtime prompt text unless needed only indirectly through Stage 3 artifact
- later-stage artifacts

### Task
Identify the smallest changes that would likely have the largest impact on the problem.

Strongly order them.
No more than 3.
Do not yet edit the specification.
Do not yet write contract language.
Do not propose a laundry list.

The target is to carry these priorities into diagnostic-log review and then specification review.

### Required artifact structure
Create 04_priority_changes.md with sections:
- Scope and source restriction
- Candidate changes considered
- Final ordered top 3 changes
- Why #1 is first
- Why #2 is second
- Why #3 is third
- What is intentionally not prioritized yet

## Stage 5 — Diagnostic log hypotheses

### Allowed sources
- 01_behavioral_review.md
- 02_predicted_prompt_weaknesses.md
- 03_prompt_comparison.md
- 04_priority_changes.md
- runtime tutor prompt, only indirectly through 03_prompt_comparison.md unless direct reference is necessary to formulate a testable hypothesis

### Forbidden sources
- diagnostic logs / private artifacts
- tutor specification
- backend/runtime contract
- schemas
- later-stage artifacts

### Task
Before reading the diagnostic logs or private artifacts, formulate testable hypotheses about what those logs should show if the behavioral/prompt diagnosis is correct.

Focus on:
- whether the tutor’s internal stay/move reasoning should show lack of a clear stopping rule
- whether the tutor should fail to mark “enough for now” even after adequate evidence
- whether it should treat non-material imperfections as reasons to continue probing
- whether it should fail to notice declining traction or pushback
- whether its diagnostics should show mastery/evidence concerns overriding pedagogical movement
- whether its recorded decision logic should match or conflict with the visible behavior

Do not yet inspect the logs.

### Required artifact structure
Create 05_diagnostic_log_hypotheses.md with sections:
- Scope and source restriction
- Diagnosis being tested
- Hypotheses about diagnostic-log contents
- What would support the diagnosis
- What would weaken the diagnosis
- What would complicate the diagnosis
- How the log check will affect specification review

## Stage 6 — Diagnostic log check

### Allowed sources
- diagnostic logs / private artifacts
- 01_behavioral_review.md
- 03_prompt_comparison.md
- 04_priority_changes.md
- 05_diagnostic_log_hypotheses.md

### Forbidden sources
- tutor specification
- tutor specification contract
- backend/runtime contract
- schemas, except the diagnostic-log schema if it is necessary to interpret the logs
- later-stage artifacts

### Task
Read the diagnostic logs or private artifacts and compare them against the hypotheses from Stage 5.

Do not revise the earlier behavioral or prompt findings.
Do not yet revise the specification.
Assess whether the logs support, weaken, or complicate the current explanation.

Focus on:
- whether the tutor’s recorded decision logic explains the visible failure
- whether diagnostics are absent, too thin, inconsistent, or misleading
- whether the logs show a failure of diagnosis, a failure of acting on diagnosis, or both
- whether the logs suggest that the proposed priority changes should be narrowed, strengthened, or deferred

### Required artifact structure
Create 06_diagnostic_log_check.md with sections:
- Scope and source restriction
- Log material inspected
- Hypothesis-by-hypothesis comparison
- Supported parts of the diagnosis
- Weakened or unsupported parts of the diagnosis
- Complications introduced by the logs
- Implications for specification review
- Revised priority list to carry forward

## Stage 7 — Tutor specification review

### Allowed sources
- tutor specification
- tutor specification contract
- 04_priority_changes.md
- 06_diagnostic_log_check.md

### Forbidden sources
- runtime tutor prompt
- raw diagnostic logs except as summarized in 06_diagnostic_log_check.md
- backend/runtime contract
- schemas
- later-stage artifacts

### Task
Read the tutor specification through the lens of the prioritized changes and diagnostic-log check.

Important:
- This stage is not yet the revision stage.
- Do not fix the specification yet.
- Identify whether the relevant weaknesses are already present in the specification, absent from it, or only partly addressed.
- Use the tutor specification contract only to understand required structure and to notice where the relevant commitments should live. Do not critique the contract itself.

### Required artifact structure
Create 07_specification_review.md with sections:
- Scope and source restriction
- Where the specification is already strong
- Weakness 1 in relation to the specification
- Weakness 2 in relation to the specification
- Weakness 3 in relation to the specification
- What the diagnostic-log check changes
- Most important specification gap
- Revision targets for the next stage

## Stage 8 — Revised tutor specification

### Allowed sources
- tutor specification
- tutor specification contract
- 04_priority_changes.md
- 06_diagnostic_log_check.md
- 07_specification_review.md

### Forbidden sources
- runtime tutor prompt
- raw diagnostic logs except as summarized in 06_diagnostic_log_check.md
- backend/runtime contract
- schemas
- later-stage artifacts except as produced so far

### Task
Produce a revised tutor specification that addresses the supported weaknesses while preserving the original specification as much as possible.

The revision should:
- remain recognizably close to the original unless a stronger change is required
- change only what is needed for the prioritized issues
- preserve the overall pedagogical identity unless revision is necessary
- remain specification-level, not runtime-level
- avoid generator-targeted instructions
- avoid backend mechanics
- reflect the diagnostic-log check only through specification-level pedagogical commitments

### Required artifact structure
Create 08_revised_tutor_specification.md as a full revised specification document, not just a diff.

Also include, at the end, a short section:
- Major changes from original specification

## Stage 9 — Contract alignment check

### Allowed sources
- 08_revised_tutor_specification.md
- tutor specification contract

### Forbidden sources
- runtime tutor prompt
- original tutor specification except only through the revised spec if needed
- diagnostic logs / private artifacts
- backend/runtime contract
- schemas
- earlier-stage analysis except where absolutely necessary

### Task
Check whether the revised tutor specification conforms to the tutor specification contract.

This is a structural and conformance review, not a pedagogical review.

You must:
- check all required items
- note recommended items if relevant
- identify any non-conformances
- if minor changes are needed to make the revised specification conform, make them directly in 08_revised_tutor_specification.md and record them here
- do not use this stage to introduce new pedagogical redesigns

### Required artifact structure
Create 09_contract_alignment_check.md with sections:
- Scope and source restriction
- Required-item checklist
- Recommended-item observations
- Any conformance issues found
- Any fixes applied to the revised specification
- Final conformance verdict

## Stage 10 — Final summary

### Allowed sources
- all stage artifacts

### Task
Produce a concise synthesis of the whole workflow:
- what the main behavioral problem was
- what prompt weakness best explained it
- what the diagnostic logs showed
- what the highest-leverage specification change was
- whether the revised specification now addresses it
- whether the revised specification conforms to the contract

### Required artifact structure
Create 10_final_summary.md with sections:
- Main behavioral diagnosis
- Main prompt diagnosis
- Diagnostic-log verdict
- Ordered revision priorities
- Main changes made to the specification
- Contract-alignment verdict

## Additional discipline rules

- At the start of each stage, explicitly state: “I am not using any forbidden sources for this stage.”
- If you accidentally inspect a forbidden source, stop immediately and record the breach in the current artifact before proceeding.
- Preserve the chronology of reasoning. Later documents may explain earlier behavior, but they may not retroactively erase the earlier-stage analysis.
- When in doubt, be more explicit about what source supports what claim.
- Use direct quotations sparingly. Prefer analytic paraphrase.
- Keep the tone analytical, exacting, and unsentimental.

## File discovery guidance

You may need to discover the relevant files in the export. Use sensible names if the export names differ. At minimum, locate equivalents of:
- the conversation transcript
- the runtime tutor prompt
- diagnostic logs or private artifacts, if present
- the tutor specification
- the tutor specification contract

If diagnostic logs or private artifacts are not present, still create 05_diagnostic_log_hypotheses.md. In 06_diagnostic_log_check.md, state that no diagnostic logs were available and explain how that limits the confidence of the specification review.

If additional contracts or schemas are present, ignore them unless and until a stage explicitly allows them.

## Deliverable standard

The workflow is complete only when:
- all 10 required files exist
- each file is substantive
- each stage obeyed its source restrictions
- each stage used earlier artifacts as input where required
- diagnostic-log hypotheses were formulated before diagnostic logs were inspected
- the diagnostic-log check was completed or explicitly marked impossible because logs were absent
- the revised specification is complete
- the contract-alignment check is complete

Return a final note listing the produced files in order.