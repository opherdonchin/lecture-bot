MULTI-SESSION TUTOR CONVERSATION ANALYSIS PROMPT

You are being asked to run a disciplined, staged analysis of a multi-session export of tutor conversations and associated design artifacts.

Your job is not to jump to conclusions. Your job is to preserve evidentiary discipline while moving from:

1. observed behavior across sessions,
2. to runtime prompt grouping and prompt-level explanation,
3. to targeted diagnostic-log checks,
4. to specification review and revision,
5. to contract alignment,
6. to student-comment triangulation, if comments are present.

The export may contain:
- multiple tutor conversation transcripts
- student-submitted comments stored outside the conversations, usually as `conversation/session_notes.json`
- one or more runtime tutor prompts
- decision-logic logs or private diagnostic artifacts, if present
- one or more tutor specifications
- a tutor specification contract
- possibly additional contracts, schemas, backend/runtime artifacts, and generated files

Your task is to analyze how the tutor behaves across sessions, how that behavior relates to runtime prompts, whether diagnostic logs support the explanation, what changes should be made to the tutor specification, and whether external student comments corroborate or complicate the analysis.

## Core Principle

Treat sessions as behavioral evidence, prompts as candidate causal mechanisms, diagnostic logs as targeted tests of those mechanisms, and student comments as external user-experience signals.

Student comments are not chat turns. They must not be treated as student answers, mastery evidence, grade evidence, or runtime context. Use them only in Stage 0 to inventory their existence and in Stage 10 to triangulate the completed analysis.

Do not infer prompt failure from isolated bad behavior unless the failure is high-severity or diagnostic evidence shows a general decision-process flaw.

Do not infer specification failure until after behavioral variability, prompt grouping, and diagnostic evidence have been considered.

Do not let student comments reorganize the behavioral inventory. Let them corroborate, weaken, complicate, or add user-experience follow-up after the main analysis is complete.

## Main Questions

Answer these questions through staged artifacts:

1. What behavioral strengths and weaknesses appear across sessions?
2. Which weaknesses recur, and which appear isolated or restricted to a subset of sessions?
3. How many distinct runtime tutor prompts are present?
4. Do behavioral strengths and weaknesses align with prompt differences, or do they occur within the same prompt?
5. What prompt strengths and weaknesses plausibly explain the observed behavioral variability?
6. Which behavior/prompt hypotheses should be tested against diagnostic logs?
7. Do targeted diagnostic logs support, weaken, or complicate those hypotheses?
8. Are the supported weaknesses already present in the tutor specification, absent from it, or only partly addressed?
9. How should the tutor specification be revised?
10. Does the revised tutor specification conform to the tutor specification contract?
11. Do external student comments, if present, corroborate, weaken, complicate, or add follow-up to the analysis?

## General Discipline Rules

1. At each stage, use only the allowed sources for that stage.
2. Before each stage, explicitly list:
   - allowed sources
   - forbidden sources
   - artifacts from prior stages that are allowed
3. At the start of each stage, explicitly state:

   I am not using any forbidden sources for this stage.

4. Produce a standalone markdown artifact for each stage before moving to the next stage.
5. After each artifact, produce a short gate note stating:
   - whether the stage is complete
   - what exact inputs will be carried into the next stage
6. Do not skip stages.
7. Do not collapse stages.
8. Do not silently revise earlier conclusions because later-stage documents reveal more.
9. When later-stage documents change the interpretation of earlier behavior, record that as a comparison against the earlier artifact.
10. Do not let prompt knowledge reorganize the behavioral inventory.
11. Do not let diagnostic logs retroactively rewrite behavioral observations.
12. Do not let student comments retroactively rewrite behavioral observations.
13. Be explicit about uncertainty.
14. Use direct quotations sparingly; prefer analytic paraphrase.
15. Keep the tone analytical, exacting, and unsentimental.
16. All evidence references must be session-qualified.

Use this format for turn references:

`session_id=<id>, turn=<n>`

When useful, also use episode references:

`session_id=<id>, episode=<label>, turns=<start-end>`

Use this format for student comments:

`session_id=<id>, comment=<n>`

Never write an unqualified reference such as "turn 17" or "comment 2" in a multi-session analysis.

## Focus Of The Analysis

Keep the analysis focused on the tutor's behavior around:

- deciding whether to stay on a point or move on
- recognizing when evidence is enough for now
- handling repetition, loss of traction, and diminishing returns
- handling student irritation, disengagement, or pushback
- managing closure and topic switching
- distinguishing useful assessment from unnecessary nitpicking
- whether internal diagnostics explain visible behavior

Avoid broad redesign unless it is necessary to address the supported weaknesses.

## Output Directory And Required Artifacts

Create an output directory:

`analysis_outputs/`

Create these files in order:

1. `analysis_outputs/00_export_inventory.md`
2. `analysis_outputs/01_behavioral_session_inventory.md`
3. `analysis_outputs/02_cross_session_behavioral_synthesis.md`
4. `analysis_outputs/03_prompt_inventory_and_grouping.md`
5. `analysis_outputs/04_prompt_group_analysis.md`
6. `analysis_outputs/05_behavior_prompt_hypotheses.md`
7. `analysis_outputs/06_targeted_diagnostic_log_check.md`
8. `analysis_outputs/07_specification_review.md`
9. `analysis_outputs/08_revised_tutor_specification.md`
10. `analysis_outputs/09_contract_alignment_check.md`
11. `analysis_outputs/10_comment_triangulation.md`
12. `analysis_outputs/11_final_summary.md`

Each file must be substantive and self-contained.

The workflow is complete only when all 12 required files exist.

## Stage 0 - Export Inventory

### Allowed Sources
- export file tree
- session metadata
- transcript filenames
- prompt filenames
- diagnostic/private artifact filenames
- student-comment filenames and metadata sufficient to count comment records per session
- specification filenames
- contract filenames
- schemas or manifests only as needed to identify file roles, not to interpret behavior, comments, or design

### Forbidden Sources
- transcript contents, except minimal metadata needed to count turns if no metadata file exists
- student-comment contents, except minimal metadata needed to count comments if no metadata file exists
- runtime prompt contents
- diagnostic log contents
- tutor specification contents
- contract contents, except titles or filenames
- backend/runtime implementation details
- later-stage artifacts

### Task
Inventory the export without interpreting tutor behavior or student comments.

Identify:
- all sessions
- all available transcripts
- all student-comment files
- all runtime prompts
- all diagnostic/private artifacts
- all tutor specifications
- all tutor specification contracts
- any additional contracts or schemas
- any missing expected artifacts

For each session, record:
- session_id
- student_id if available
- lecture_id if available
- transcript path
- student-comment path, if available
- comment count, if safely knowable without interpreting comments
- runtime prompt path or prompt identifier if available
- diagnostic/private artifact path if available
- number of user turns
- number of assistant turns
- whether grade/report events appear to exist
- whether the session appears complete or truncated
- any uncertainty about file matching

Do not evaluate behavior yet.
Do not interpret student comments yet.

### Required Artifact
Create `analysis_outputs/00_export_inventory.md` with sections:
- Scope and source restriction
- Export structure
- Session inventory table
- Student-comment inventory
- Runtime prompt inventory
- Diagnostic/private artifact inventory
- Specification and contract inventory
- File-matching uncertainties
- Gate note

## Stage 1 - Behavioral Session Inventory

### Allowed Sources
- all tutor conversation transcripts
- `00_export_inventory.md`

### Forbidden Sources
- student-comment contents
- runtime prompt contents
- diagnostic logs / private artifact contents
- tutor specification contents
- tutor specification contract contents
- backend/runtime contract contents
- schemas, except if needed only to interpret transcript format
- generator prompts
- later-stage artifacts

### Task
Evaluate tutor behavior across each individual session, using transcripts only.

This is a behavioral inventory, not a prompt critique.

For each session, identify:
- behavioral strengths
- behavioral weaknesses
- whether the tutor recognized when the student had shown enough understanding for now
- whether the tutor became repetitive, nitpicky, or over-focused on local imperfections
- how the tutor handled irritation, disengagement, or pushback
- how the tutor handled closure and topic switching
- notable strong episodes
- notable weak episodes
- uncertainty or limitations

Do not yet infer prompt wording.
Do not yet read or critique runtime prompts.
Do not yet inspect diagnostics.
Do not yet inspect student comments.
Do not yet suggest specification fixes.

Every example must be session-qualified.

### Required Artifact
Create `analysis_outputs/01_behavioral_session_inventory.md` with sections:
- Scope and source restriction
- Session-by-session behavioral profiles
- Notable strong episodes
- Notable weak episodes
- Initial behavioral failure-mode table
- Open questions to carry forward
- Gate note

The behavioral failure-mode table should include:
- failure mode
- definition
- sessions where observed
- strongest examples
- counterexamples
- severity
- frequency
- confidence

## Stage 2 - Cross-Session Behavioral Synthesis

### Allowed Sources
- all tutor conversation transcripts
- `00_export_inventory.md`
- `01_behavioral_session_inventory.md`

### Forbidden Sources
- student-comment contents
- runtime prompt contents
- diagnostic logs / private artifact contents
- tutor specification contents
- tutor specification contract contents
- backend/runtime contract contents
- generator prompts
- later-stage artifacts

### Task
Synthesize behavior across sessions.

Identify:
- recurrent behavioral strengths
- recurrent behavioral weaknesses
- isolated weaknesses
- subset-specific weaknesses
- counterexamples where the tutor behaved well under similar conditions
- behavior that varies substantially across sessions
- behavior that appears stable across sessions
- high-severity rare failures
- the most important behavioral questions to test against prompts and diagnostics

Do not yet read prompts.
Do not yet infer that a prompt caused a behavior.
Do not yet inspect student comments.
Do not yet propose specification revisions.

The goal is to establish the behavioral variability that later prompt analysis must explain.

### Required Artifact
Create `analysis_outputs/02_cross_session_behavioral_synthesis.md` with sections:
- Scope and source restriction
- Cross-session behavioral strengths
- Cross-session behavioral weaknesses
- Recurrent failure modes
- Isolated or subset-specific failure modes
- Counterexamples and variability
- High-severity episodes
- Behavioral hypotheses to carry into prompt grouping
- Gate note

## Stage 3 - Prompt Inventory And Grouping

### Allowed Sources
- runtime tutor prompt files
- prompt metadata
- `00_export_inventory.md`
- `01_behavioral_session_inventory.md`
- `02_cross_session_behavioral_synthesis.md`

### Forbidden Sources
- student-comment contents
- diagnostic logs / private artifact contents
- tutor specification contents
- tutor specification contract contents
- backend/runtime contract contents
- schemas, except if needed only to identify prompt associations
- generator prompts unless they are the only way to identify prompt provenance
- later-stage artifacts

### Task
Determine how many distinct runtime tutor prompts are present and how sessions map to prompts.

For each runtime prompt:
- assign a prompt identifier
- identify which sessions used it
- determine whether the prompt is identical to or different from other prompts
- summarize the prompt's high-level governing structure
- do not yet perform full prompt critique

Then compare prompt grouping with behavioral patterns from Stages 1-2.

Determine whether:
1. there is one prompt with variable behavior across sessions
2. there are multiple prompts and behavior differs by prompt
3. there are multiple prompts but behavior does not clearly differ by prompt
4. prompt-to-session mapping is uncertain

This stage should not analyze diagnostic logs, specifications, or student comments.

### Required Artifact
Create `analysis_outputs/03_prompt_inventory_and_grouping.md` with sections:
- Scope and source restriction
- Prompt inventory
- Prompt identity and difference analysis
- Session-to-prompt mapping
- Behavioral patterns by prompt group
- Behavioral variability within prompt group
- Prompt-grouping interpretation
- Uncertainties
- Gate note

## Stage 4 - Prompt Group Analysis

### Allowed Sources
- runtime tutor prompt files
- `01_behavioral_session_inventory.md`
- `02_cross_session_behavioral_synthesis.md`
- `03_prompt_inventory_and_grouping.md`

### Forbidden Sources
- student-comment contents
- diagnostic logs / private artifact contents
- tutor specification contents
- tutor specification contract contents
- backend/runtime contract contents
- schemas
- generator prompts
- later-stage artifacts

### Task
Analyze the strengths and weaknesses of each distinct runtime prompt in light of the behavioral variability.

For each prompt or prompt group, identify:
- prompt strengths that plausibly support good behavior
- prompt weaknesses that plausibly permit bad behavior
- ambiguous or conflicting commitments
- missing arbitration rules
- missing "enough for now" logic
- missing "low marginal value of another question" logic
- handling of repetition and declining traction
- handling of student pushback
- closure and topic-switching logic
- whether the same prompt appears capable of producing both strong and weak behavior

Do not yet inspect diagnostics.
Do not yet inspect tutor specification.
Do not yet inspect student comments.
Do not yet propose specification edits.

The goal is to formulate prompt-level explanations that account for both strengths and weaknesses.

### Required Artifact
Create `analysis_outputs/04_prompt_group_analysis.md` with sections:
- Scope and source restriction
- Prompt group summaries
- Prompt strengths by group
- Prompt weaknesses by group
- Within-prompt behavioral variability
- Between-prompt behavioral differences
- Most plausible prompt-level explanations
- Alternative explanations
- Gate note

## Stage 5 - Behavior/Prompt Hypotheses

### Allowed Sources
- `01_behavioral_session_inventory.md`
- `02_cross_session_behavioral_synthesis.md`
- `03_prompt_inventory_and_grouping.md`
- `04_prompt_group_analysis.md`
- runtime tutor prompts only as already analyzed in Stage 4, unless a direct prompt reference is necessary to formulate a testable hypothesis

### Forbidden Sources
- student-comment contents
- diagnostic logs / private artifact contents
- tutor specification contents
- tutor specification contract contents
- backend/runtime contract contents
- schemas
- later-stage artifacts

### Task
Formulate testable hypotheses about the relationship between behavior and prompt design.

Each hypothesis must include:
- behavioral pattern
- prompt-level explanation
- sessions or prompt groups involved
- predicted diagnostic-log signature
- what would support the hypothesis
- what would weaken the hypothesis
- what would complicate the hypothesis
- alternative explanations

Focus especially on:
- whether the tutor has a clear stopping rule
- whether it marks "enough for now"
- whether it treats non-material imperfections as reasons to keep probing
- whether it notices declining traction or student pushback
- whether mastery/evidence concerns override pedagogical movement
- whether repeated probing reflects diagnosis failure, arbitration failure, expression failure, or logging failure

Do not inspect diagnostic logs yet.
Do not inspect student comments yet.

### Required Artifact
Create `analysis_outputs/05_behavior_prompt_hypotheses.md` with sections:
- Scope and source restriction
- Hypothesis table
- Hypothesis details
- Predicted diagnostic signatures
- Target episodes for log inspection
- Alternative explanations
- How diagnostic checks will affect recommendations
- Gate note

The target episodes should include, if available:
- at least one strong episode where the tutor moved on appropriately
- at least one weak episode where the tutor perseverated or nitpicked
- at least one episode involving student pushback or disengagement
- at least one closure or report-generation episode
- episodes from different prompt groups, if multiple prompts exist

This selection does not need to be comprehensive. It must be sufficient to support or refute the main hypotheses.

## Stage 6 - Targeted Diagnostic-Log Check

### Allowed Sources
- diagnostic logs / private artifacts
- diagnostic-log schema, only if necessary to interpret the logs
- `00_export_inventory.md`
- `01_behavioral_session_inventory.md`
- `02_cross_session_behavioral_synthesis.md`
- `03_prompt_inventory_and_grouping.md`
- `04_prompt_group_analysis.md`
- `05_behavior_prompt_hypotheses.md`

### Forbidden Sources
- student-comment contents
- tutor specification contents
- tutor specification contract contents
- backend/runtime contract contents
- unrelated schemas
- generator prompts
- later-stage artifacts

### Task
Inspect diagnostic logs or private artifacts only for the target episodes identified in Stage 5, unless broader inspection is necessary because the target episodes are missing logs.

Compare logs against the hypotheses.

Assess whether the logs show:
- accurate diagnosis but poor action selection
- inaccurate diagnosis
- reasonable decision-making but poor wording
- no explicit "enough for now" judgment
- recognition of evidence but failure to move on
- recognition of pushback but failure to adapt
- mastery/evidence concerns overriding pedagogical movement
- lack of diagnostic detail
- inconsistency between recorded reasoning and visible behavior

If diagnostic logs are absent, create the artifact anyway and state that the check is impossible. Explain how that limits confidence.

Do not revise earlier behavioral findings.
Do not revise the tutor specification yet.
Do not inspect student comments yet.

### Required Artifact
Create `analysis_outputs/06_targeted_diagnostic_log_check.md` with sections:
- Scope and source restriction
- Log material inspected
- Missing or unavailable log material
- Hypothesis-by-hypothesis comparison
- Strong episodes: diagnostic interpretation
- Weak episodes: diagnostic interpretation
- Pushback/disengagement episodes: diagnostic interpretation
- Closure/report episodes: diagnostic interpretation
- Supported explanations
- Weakened explanations
- Complications introduced by diagnostics
- Diagnosis failure vs arbitration failure vs expression failure vs logging failure
- Implications for specification review
- Revised recommendation priorities to carry forward
- Gate note

## Stage 7 - Tutor Specification Review

### Allowed Sources
- tutor specification
- tutor specification contract
- `05_behavior_prompt_hypotheses.md`
- `06_targeted_diagnostic_log_check.md`

### Forbidden Sources
- student-comment contents
- runtime tutor prompt contents, except as summarized in Stage 5
- raw diagnostic logs, except as summarized in Stage 6
- raw transcripts, except as summarized in Stages 1-2
- backend/runtime contract contents
- schemas
- generator prompts
- later-stage artifacts

### Task
Review the tutor specification through the lens of the supported behavioral/prompt/diagnostic findings.

This is not yet the revision stage.

Identify:
- where the specification is already strong
- whether each supported weakness is already present in the specification
- whether each supported weakness is absent from the specification
- whether each supported weakness is present but too weak, implicit, or underspecified
- whether the specification distinguishes enough evidence from perfect evidence
- whether it requires movement when another question has low marginal value
- whether it addresses repetition and loss of traction
- whether it addresses student pushback
- whether it gives the tutor a way to choose between assessment and pedagogical movement
- where in the contract structure the relevant commitments belong

Use the tutor specification contract only to understand required structure and where commitments should live.

Do not critique the contract itself.
Do not edit the specification yet.
Do not use student comments yet.

### Required Artifact
Create `analysis_outputs/07_specification_review.md` with sections:
- Scope and source restriction
- Specification strengths
- Supported weakness 1 in relation to the specification
- Supported weakness 2 in relation to the specification
- Supported weakness 3 in relation to the specification
- Additional supported weaknesses, if any
- What the diagnostic-log check changes
- Most important specification gaps
- Revision targets for the next stage
- Gate note

## Stage 8 - Revised Tutor Specification

### Allowed Sources
- tutor specification
- tutor specification contract
- `05_behavior_prompt_hypotheses.md`
- `06_targeted_diagnostic_log_check.md`
- `07_specification_review.md`

### Forbidden Sources
- student-comment contents
- runtime tutor prompt contents, except as summarized in Stage 5
- raw diagnostic logs, except as summarized in Stage 6
- raw transcripts, except as summarized in Stages 1-2
- backend/runtime contract contents
- schemas
- generator prompts
- later-stage artifacts except those produced so far

### Task
Produce a full revised tutor specification that addresses the supported weaknesses while preserving the original specification as much as possible.

The revision should:
- remain recognizably close to the original unless stronger change is required
- change only what is needed for the supported issues
- preserve the overall pedagogical identity unless revision is necessary
- remain specification-level, not runtime-level
- avoid generator-targeted instructions
- avoid backend mechanics
- reflect diagnostic-log findings only through specification-level pedagogical commitments
- distinguish enough evidence from perfect evidence
- include a clear principle for moving on when further probing has low marginal diagnostic value
- include handling for repetition, declining traction, and student pushback
- include closure and topic-switching expectations where appropriate

Do not introduce unsupported redesigns.
Do not base revisions on student comments; comments are checked only after contract alignment.

Each major change should be justified by one of these evidence statuses:
- recurrent across same prompt
- prompt-specific
- rare but high-severity
- diagnostic-supported
- diagnostic-unsupported but behaviorally plausible

Only recurrent, prompt-specific, or rare high-severity weaknesses should drive significant revisions. Diagnostic support should strengthen, narrow, or qualify the revision.

### Required Artifact
Create `analysis_outputs/08_revised_tutor_specification.md`.

This must be a full revised specification document, not a diff.

At the end include:
- Major changes from original specification
- Evidence status for major changes
- Issues intentionally not revised

## Stage 9 - Contract Alignment Check

### Allowed Sources
- `08_revised_tutor_specification.md`
- tutor specification contract

### Forbidden Sources
- student-comment contents
- runtime tutor prompt contents
- original tutor specification except through the revised specification if needed
- diagnostic logs / private artifacts
- transcripts
- backend/runtime contract contents
- schemas
- generator prompts
- earlier-stage analysis except where absolutely necessary to understand whether a change was already applied

### Task
Check whether the revised tutor specification conforms to the tutor specification contract.

This is a structural and conformance review, not a pedagogical review.

You must:
- check all required items
- note recommended items if relevant
- identify any non-conformances
- if minor changes are needed to make the revised specification conform, make them directly in `analysis_outputs/08_revised_tutor_specification.md` and record them here
- do not introduce new pedagogical redesigns at this stage

Do not use student comments yet.

### Required Artifact
Create `analysis_outputs/09_contract_alignment_check.md` with sections:
- Scope and source restriction
- Required-item checklist
- Recommended-item observations
- Any conformance issues found
- Any fixes applied to the revised specification
- Final conformance verdict
- Gate note

## Stage 10 - Student Comment Triangulation

### Allowed Sources
- student-comment files, usually `conversation/session_notes.json`
- conversation transcripts, only to anchor comments to their surrounding conversational moment
- session message metadata if needed to resolve comment anchors
- `00_export_inventory.md`
- `01_behavioral_session_inventory.md`
- `02_cross_session_behavioral_synthesis.md`
- `06_targeted_diagnostic_log_check.md`
- `09_contract_alignment_check.md`

### Forbidden Sources
- runtime tutor prompt contents
- tutor specification contents
- tutor specification contract contents
- backend/runtime contract contents
- schemas
- raw diagnostic logs / private artifacts except as summarized in Stage 6
- later-stage artifacts

### Task
Triangulate the completed analysis against external student comments, if present.

Important:
- Do not revise earlier-stage conclusions.
- Do not treat comments as chat turns, student answers, mastery evidence, grade evidence, or runtime context.
- Do not run the full user-facing comment analysis here. Use `prompts/comment_analysis_prompt.md` for that separate workflow.
- Use comments only to ask whether the completed tutor-behavior/specification diagnosis is corroborated, weakened, complicated, or missing a user-experience signal.
- All comment references must be session-qualified.

For each relevant comment:
- summarize what the comment says
- anchor it to the nearest relevant conversation moment, if possible
- state whether it supports, weakens, complicates, or is unrelated to the main behavioral diagnosis
- state whether it supports, weakens, complicates, or is unrelated to the diagnostic-log verdict
- state whether it suggests any follow-up outside the revised specification

Across comments, identify:
- recurrent comment themes across sessions
- isolated comments
- comments attached to already-identified weak episodes
- comments that point to issues missed by transcript/log/specification analysis
- comments that are ambiguous or not judgeable from the transcript

If no comments are present, create the artifact and state that no external comments were available.

### Required Artifact
Create `analysis_outputs/10_comment_triangulation.md` with sections:
- Scope and source restriction
- Comment material inspected
- Comment-to-conversation anchors
- Cross-session comment themes
- Relationship to main behavioral findings
- Relationship to diagnostic-log verdict
- Relationship to specification revision
- User-facing follow-up suggested by comments
- Ambiguous or not-judgeable comments
- Triangulation verdict
- Gate note

## Stage 11 - Final Summary

### Allowed Sources
- all prior stage artifacts

### Forbidden Sources
- raw transcripts
- raw prompts
- raw diagnostic logs
- raw student comments
- raw specifications
- raw contracts
- backend/runtime artifacts

### Task
Produce a concise synthesis of the whole workflow.

Address:
- what the main behavioral patterns were
- which weaknesses recurred
- which weaknesses were isolated or subset-specific
- how many runtime prompts were present
- whether behavioral differences tracked prompt differences or appeared within prompts
- what prompt weaknesses best explained the behavior
- what the diagnostic logs showed
- what recommendation priorities emerged
- what changed in the revised specification
- whether the revised specification conforms to the contract
- how student comments affected confidence or follow-up priorities
- what should be checked in the next export after revision

### Required Artifact
Create `analysis_outputs/11_final_summary.md` with sections:
- Main behavioral findings
- Behavioral variability across sessions
- Prompt inventory verdict
- Prompt diagnosis
- Diagnostic-log verdict
- Ordered recommendation priorities
- Main specification changes
- Contract-alignment verdict
- Comment-triangulation verdict
- Follow-up checks for the next export

## File Discovery Guidance

You may need to discover the relevant files in the export. Use sensible names if the export names differ.

At minimum, locate equivalents of:
- conversation transcripts
- student-comment files, if present
- runtime tutor prompts
- diagnostic logs or private artifacts, if present
- tutor specification
- tutor specification contract

If diagnostic logs or private artifacts are not present:
- still create `analysis_outputs/05_behavior_prompt_hypotheses.md`
- create `analysis_outputs/06_targeted_diagnostic_log_check.md`
- state that no diagnostic logs were available
- explain how that limits confidence

If student comments are not present:
- still create `analysis_outputs/10_comment_triangulation.md`
- state that no comments were available
- explain that the final summary cannot use external student annotations as triangulation evidence

If multiple tutor specifications are present:
- identify them in Stage 0
- defer deciding which governs the analyzed sessions until Stage 7 unless metadata makes it clear earlier

If additional contracts or schemas are present:
- ignore them unless a stage explicitly allows them

## Deliverable Standard

The workflow is complete only when:
- all 12 required files exist
- each file is substantive and self-contained
- each stage obeyed its source restrictions
- all behavioral evidence is session-qualified
- all comment evidence is session-qualified
- behavioral variability across sessions is explicitly analyzed
- prompt grouping is completed before prompt diagnosis
- diagnostic-log hypotheses are formulated before diagnostic logs are inspected
- diagnostic-log checks are targeted to selected strong/weak episodes
- specification review occurs only after diagnostic-log check
- student-comment triangulation occurs only after contract alignment
- the revised specification is complete
- the contract-alignment check is complete
- the final summary distinguishes recurrent, subset-specific, isolated, and high-severity findings

Return a final note listing the produced files in order.
