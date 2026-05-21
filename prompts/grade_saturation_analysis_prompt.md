GRADE SATURATION ANALYSIS PROMPT

You are being asked to investigate a single tutoring session in which the student performed well and received moderately high feedback from the tutor, but the final grade was lower than the quality of the conversation warranted. The specific failure mode under investigation is **grade saturation**: the tutor stops escalating challenge after a student demonstrates solid understanding, treating good-enough evidence as a reason to close or consolidate rather than as a platform for harder questions.

The working hypothesis is that the tutor has an implicit ceiling in its challenge escalation — it is willing to ask follow-up questions to clarify weak understanding, but is not willing to ask genuinely harder questions when understanding appears solid. This means strong students cannot earn higher grades because the tutor consolidates instead of probing deeper or broader.

Your task is to diagnose whether and where this ceiling occurs, trace it to prompt language or specification gaps, and produce a specification revision that removes the ceiling.

---

## Core Principle

A well-functioning tutor should always be willing to ask a harder question when the student has just answered well. Consolidation and closure are appropriate only when no harder question would yield materially more evidence — not when the student has merely demonstrated solid basic understanding. A student who answers every question correctly at the current difficulty level has not earned a ceiling; they have earned a harder question.

Grade saturation occurs when the tutor treats demonstrated solid understanding as a stopping signal rather than as a green light for escalation.

---

## Main Questions

1. At what point in the session did challenge level stop increasing?
2. Did the tutor have opportunities to ask harder questions and fail to take them?
3. What categories of harder question were available but not asked?
4. Do the diagnostic logs show the tutor explicitly choosing not to escalate, or is escalation simply absent from the decision process?
5. Does the tutor prompt give the tutor a mechanism for escalating after strong answers, or does it only give mechanisms for recovering after weak ones?
6. Does the tutor specification establish that strong answers call for harder questions, or does it only say to ask the next useful question?
7. What specification language would ensure that the tutor always treats strong answers as a platform for escalation?

---

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
8. Keep the tone analytical, exacting, and unsentimental.
9. All evidence references must be turn-qualified.

Use this format for turn references:

`turn=<n>, role=<user|assistant>`

Use this format for diagnostic log references:

`turn=<n>, artifact_field=<field_path>`

---

## Output Directory And Required Artifacts

Create an output directory:

`analysis_outputs/`

Create these files in order:

1. `analysis_outputs/00_session_inventory.md`
2. `analysis_outputs/01_grade_trajectory.md`
3. `analysis_outputs/02_challenge_level_profile.md`
4. `analysis_outputs/03_missed_escalation_inventory.md`
5. `analysis_outputs/04_prompt_escalation_analysis.md`
6. `analysis_outputs/05_diagnostic_log_check.md`
7. `analysis_outputs/06_specification_review.md`
8. `analysis_outputs/07_revised_tutor_specification.md`
9. `analysis_outputs/08_contract_alignment_check.md`
10. `analysis_outputs/09_final_summary.md`

Each file must be substantive and self-contained.

The workflow is complete only when all 10 required files exist.

---

## Stage 0 — Session Inventory

### Allowed Sources
- export file tree and manifest
- session metadata (session_id, student_id, lecture_id, timestamps, final grade)
- transcript filenames
- prompt filenames
- diagnostic/private artifact filenames
- rubric filenames
- specification filenames
- contract filenames

### Forbidden Sources
- transcript contents
- runtime prompt contents
- diagnostic log contents
- specification contents
- contract contents except titles or filenames

### Task
Inventory the export without interpreting behavior.

Record:
- session_id, student_id, lecture_id, final grade, session duration
- number of user turns, number of assistant turns
- whether grade events and a final report event exist
- which runtime prompt was used (identifier only)
- whether diagnostic/private artifact logs are present (yes/no, count of turns covered)
- which tutor specification is present
- which rubric is present
- any file-matching uncertainties

### Required Artifact
Create `analysis_outputs/00_session_inventory.md` with:
- Session metadata table
- File inventory
- Grade event summary (grade values only, no behavioral interpretation yet)
- Uncertainties
- Gate note

---

## Stage 1 — Grade Trajectory

### Allowed Sources
- grade events (payload_json values)
- session state (mastery and best_mastery fields)
- rubric (topic IDs, topic labels, and grade weights only — not behavioral guidance)
- `00_session_inventory.md`

### Forbidden Sources
- transcript contents
- runtime prompt contents
- diagnostic log contents
- specification contents
- contract contents

### Task
Map the grade trajectory across the session without reading the transcript.

Determine:
- what grade events occurred and at what timestamps
- which topics received mastery scores and what those scores were
- which topics received no score
- what the topic weights are from the rubric
- where grade improvement stopped
- which topics, if any covered, were scored low despite being discussed
- what maximum grade would have been achievable if all topics had been scored at the rubric's top tier

This stage establishes the quantitative shape of the saturation before any behavioral evidence is considered.

### Required Artifact
Create `analysis_outputs/01_grade_trajectory.md` with:
- Grade event table (timestamp, grade value, topic scores)
- Final mastery map by topic
- Unscored topics
- Topic weight table from rubric
- Grade ceiling analysis: what was achievable vs what was achieved
- Where grade improvement stalled
- Gate note

---

## Stage 2 — Challenge Level Profile

### Allowed Sources
- all tutor conversation transcripts
- `00_session_inventory.md`
- `01_grade_trajectory.md`

### Forbidden Sources
- runtime prompt contents
- diagnostic log contents
- specification contents
- contract contents

### Task
Read the transcript and characterize the challenge level of each tutor question turn by turn.

For each assistant turn that contains a substantive question, assess:
- the topic being probed
- the cognitive demand (define / distinguish / explain / apply / interpret / critique / repair / compress / synthesize)
- whether the question was harder, same, or easier than the preceding question on the same topic
- whether the student's prior answer warranted escalation
- whether the tutor escalated after a strong student answer

Identify:
- the highest cognitive demand reached per topic
- whether challenge level increased, plateaued, or decreased after strong student answers
- specific turns where the tutor could have escalated but did not
- specific turns where the tutor did escalate successfully
- turns where the tutor consolidated or closed after a strong answer rather than escalating
- the approximate turn at which challenge level stopped increasing

Do not read the prompt yet.
Do not read diagnostic logs yet.
Do not yet explain why escalation did or did not happen.

### Required Artifact
Create `analysis_outputs/02_challenge_level_profile.md` with:
- Per-turn challenge level table (turn, topic, cognitive demand, escalation decision, student answer quality)
- Challenge level trajectory narrative
- Topics where ceiling was reached early
- Topics where escalation was sustained
- Missed escalation candidates (turn reference, what harder question was available)
- Consolidation/closure episodes after strong answers
- Gate note

---

## Stage 3 — Missed Escalation Inventory

### Allowed Sources
- all tutor conversation transcripts
- `00_session_inventory.md`
- `01_grade_trajectory.md`
- `02_challenge_level_profile.md`

### Forbidden Sources
- runtime prompt contents
- diagnostic log contents
- specification contents
- contract contents

### Task
For each missed escalation opportunity identified in Stage 2, construct the harder question that the tutor could have asked.

For each missed opportunity:
- quote or paraphrase the student answer that warranted escalation
- describe the cognitive operation the student performed
- identify the higher cognitive operation that was available next
- write the harder question that could have been asked
- explain what new evidence that question would have elicited
- assess whether that evidence would have materially improved the mastery characterization

Also identify:
- the total number of missed escalation opportunities
- whether missed opportunities cluster at particular points in the session (early, middle, late)
- whether missed opportunities cluster on particular topics
- whether the tutor's consolidation language is explicitly closing or merely not escalating

This inventory will serve as the evidentiary basis for prompt and specification analysis.

### Required Artifact
Create `analysis_outputs/03_missed_escalation_inventory.md` with:
- Missed escalation table (turn, student answer quality, available escalation, question not asked, evidence impact)
- Harder question constructions
- Clustering analysis
- Consolidation language episodes
- Summary: how many missed escalations, how much grade impact
- Gate note

---

## Stage 4 — Prompt Escalation Analysis

### Allowed Sources
- runtime tutor prompt
- `02_challenge_level_profile.md`
- `03_missed_escalation_inventory.md`

### Forbidden Sources
- student-comment contents
- diagnostic log contents
- specification contents
- contract contents
- transcript contents except as already summarized in Stages 2-3

### Task
Analyze the runtime tutor prompt specifically for its challenge escalation logic.

Identify:
- every place the prompt addresses what to do after a strong student answer
- every place the prompt addresses adaptive challenge
- every place the prompt addresses consolidation or closure decisions
- whether the prompt gives an explicit instruction to escalate after strong answers
- whether the prompt gives a stopping rule based on evidence sufficiency
- whether the stopping rule could trigger before a strong student has been adequately challenged
- whether the prompt distinguishes "enough evidence to characterize current understanding" from "enough evidence to determine the student cannot go further"
- whether the prompt explicitly states that strong answers are a green light for harder questions
- whether the prompt's consolidation language could be interpreted as preferring early closure
- what prompt changes would directly address the missed escalations in Stage 3

Do not read diagnostic logs yet.
Do not read the specification yet.

### Required Artifact
Create `analysis_outputs/04_prompt_escalation_analysis.md` with:
- Prompt excerpt inventory (relevant escalation, closure, and challenge sections)
- Escalation mechanism assessment
- Stopping rule assessment
- Consolidation language assessment
- Prompt-level explanation for each missed escalation cluster
- Missing prompt language
- Candidate prompt fixes (defer to specification revision, but note them here)
- Gate note

---

## Stage 5 — Diagnostic Log Check

### Allowed Sources
- diagnostic logs / private artifacts (per-turn artifact_json)
- diagnostic-log schema if necessary to interpret fields
- `03_missed_escalation_inventory.md`
- `04_prompt_escalation_analysis.md`

### Forbidden Sources
- student-comment contents
- specification contents
- contract contents
- transcript contents except as already summarized

### Task
Inspect the diagnostic logs for the missed escalation turns identified in Stage 3.

For each missed escalation turn with available logs, determine:
- what `selected_mode` the tutor chose
- what `breadth_depth_choice` the tutor chose
- what `evidence_strength` the tutor assessed
- what `next_probe_materially_improves_characterization` the tutor assessed
- whether the self-verification fields show the tutor recognized the student answered strongly
- whether the tutor recorded a decision rationale that explains why it did not escalate
- whether the log reveals the tutor saw the opportunity and declined, or simply did not consider it

Classify each logged missed escalation as one of:
- **diagnosis failure**: the tutor did not recognize the answer was strong
- **arbitration failure**: the tutor recognized the answer was strong but chose not to escalate
- **expression failure**: the tutor intended to escalate but the question was not harder
- **logging failure**: the logs do not contain enough detail to classify

If no diagnostic logs are available, state that clearly and explain the resulting limits on confidence.

### Required Artifact
Create `analysis_outputs/05_diagnostic_log_check.md` with:
- Log material inspected (turns covered, turns missing)
- Per-missed-escalation log analysis
- Classification table (diagnosis / arbitration / expression / logging failure)
- Supported explanations
- Unsupported or underdetermined explanations
- Implications for specification and prompt revision
- Gate note

---

## Stage 6 — Specification Review

### Allowed Sources
- tutor specification
- tutor specification contract (structure only)
- `03_missed_escalation_inventory.md`
- `04_prompt_escalation_analysis.md`
- `05_diagnostic_log_check.md`

### Forbidden Sources
- student-comment contents
- runtime tutor prompt contents except as summarized in Stage 4
- raw diagnostic logs except as summarized in Stage 5
- raw transcripts except as summarized in Stages 2-3
- contract contents beyond structure

### Task
Review the tutor specification for its treatment of challenge escalation after strong answers.

Determine:
- whether the specification explicitly states that strong answers call for harder questions
- whether the specification distinguishes "sufficient evidence to characterize" from "sufficient challenge for the student"
- whether the specification has a principle that prevents premature consolidation of a strong student
- whether the specification's stopping rule is tied to "no harder question would yield material evidence" or to "enough evidence has been collected"
- where in the specification structure the escalation commitment belongs
- what precise specification language would close the grade saturation gap

Do not edit the specification yet.

### Required Artifact
Create `analysis_outputs/06_specification_review.md` with:
- Existing specification strengths regarding challenge
- Specification gaps regarding escalation after strong answers
- Specification gaps regarding consolidation timing
- Specification gaps regarding distinguishing characterization sufficiency from challenge sufficiency
- Precise revision targets
- Gate note

---

## Stage 7 — Revised Tutor Specification

### Allowed Sources
- tutor specification
- tutor specification contract
- `03_missed_escalation_inventory.md`
- `05_diagnostic_log_check.md`
- `06_specification_review.md`

### Forbidden Sources
- student-comment contents
- runtime tutor prompt contents except as summarized in Stage 4
- raw diagnostic logs except as summarized in Stage 5
- raw transcripts except as summarized in Stages 2-3

### Task
Produce a full revised tutor specification that addresses grade saturation while preserving the original specification as much as possible.

The revision must:
- add an explicit principle that a strong student answer is a green light for a harder question, not a consolidation trigger
- add an explicit principle that consolidation and closure are appropriate only when no harder question would yield materially more evidence — not merely when the student has shown solid basic understanding
- add an explicit principle that the tutor's stopping rule must be tied to challenge exhaustion, not evidence sufficiency at the current difficulty level
- preserve the overall pedagogical identity of the original specification
- remain specification-level, not runtime-level
- avoid generator-targeted instructions
- avoid backend mechanics

Each major change must be justified by evidence status:
- diagnostic-supported
- behaviorally observed but not logged
- structurally necessary given the stopping-rule gap

### Required Artifact
Create `analysis_outputs/07_revised_tutor_specification.md`.

This must be a full revised specification document, not a diff.

At the end include:
- Major changes from original specification
- Evidence status for each major change
- Issues intentionally not revised

---

## Stage 8 — Contract Alignment Check

### Allowed Sources
- `07_revised_tutor_specification.md`
- tutor specification contract

### Forbidden Sources
- all others

### Task
Check whether the revised specification conforms to the tutor specification contract.

If minor conformance fixes are needed, apply them directly to `07_revised_tutor_specification.md` and record them here.

Do not introduce new pedagogical redesigns at this stage.

### Required Artifact
Create `analysis_outputs/08_contract_alignment_check.md` with:
- Required-item checklist
- Any conformance issues found
- Any fixes applied
- Final conformance verdict
- Gate note

---

## Stage 9 — Final Summary

### Allowed Sources
- all prior stage artifacts

### Forbidden Sources
- raw transcripts
- raw prompts
- raw diagnostic logs
- raw specifications
- raw contracts

### Task
Produce a concise synthesis of the whole workflow.

Address:
- where challenge level stalled in the session
- how many missed escalation opportunities were found and their grade impact
- whether missed escalations reflect diagnosis failure, arbitration failure, or expression failure
- what prompt language was missing or misleading
- what specification gaps drove the saturation
- what the revised specification adds
- whether the revision conforms to the contract
- what to check in the next session to confirm the fix worked

### Required Artifact
Create `analysis_outputs/09_final_summary.md` with:
- Challenge saturation finding
- Missed escalation summary
- Diagnostic classification verdict
- Prompt gap summary
- Specification gap summary
- Main specification changes
- Contract conformance verdict
- Verification checks for the next session

---

## File Discovery Guidance

At minimum, locate equivalents of:
- the session transcript (`messages.txt` or `chat_transcript.json`)
- the session bundle (`session_bundle.json`) for grade events and state
- the runtime tutor prompt
- the diagnostic/private artifact logs (`session_bundle.json` → `dialogue_turn_audits`)
- the tutor specification
- the tutor specification contract
- the lecture rubric (for topic weights)

If diagnostic logs are absent, still create Stage 5 and state the limitation clearly.

---

## Deliverable Standard

The workflow is complete only when:
- all 10 required files exist and are substantive
- each stage obeyed its source restrictions
- every behavioral claim is turn-qualified
- the missed escalation inventory is concrete and specific
- the diagnostic classification is applied to each logged missed escalation
- the revised specification contains explicit language addressing the grade saturation ceiling
- the contract alignment check is complete
- the final summary is self-contained

Return a final note listing the produced files in order.
