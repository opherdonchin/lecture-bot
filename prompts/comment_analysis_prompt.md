MULTI-SESSION STUDENT COMMENT ANALYSIS PROMPT

You are being asked to run a disciplined analysis of student-submitted comments that were recorded outside actual tutor conversations in a multi-session export.

These comments are not chat turns. They did not affect the tutor's runtime context, tutor state, grading, or visible conversation. Treat them as student-authored annotations about sessions, usually tied to a moment in a conversation by metadata such as `turn_index`, `latest_message_id`, `latest_assistant_message_id`, `created_at`, and a state snapshot.

Your job is to explain what comments were offered across sessions, what they appear to mean, how they relate to conversation context, whether they form cross-session themes, and what a maintainer, instructor, prompt author, specification author, or product owner should consider doing about them.

## Core Principle

Treat comments as external user-experience signals, not as conversation turns.

Comment evidence can be powerful when it is anchored to visible conversation behavior, especially when similar comments recur across sessions. But a comment is not automatically correct, not automatically actionable, and not evidence of student mastery.

All comment and turn references must be session-qualified.

Use this format for turn references:

`session_id=<id>, turn=<n>`

Use this format for comments:

`session_id=<id>, comment=<n>`

Never write an unqualified reference such as "turn 17" or "comment 2" in a multi-session analysis.

## Goal

Given an export that includes:
- multiple tutor conversation transcripts
- student-submitted comments, usually in per-session `conversation/session_notes.json` files
- session state snapshots attached to those comments, if present
- diagnostic logs / private artifacts, if present
- one or more runtime tutor prompts
- a tutor specification and relevant contracts, if present

produce a user-facing comment analysis that answers:

1. What comments did students submit across sessions?
2. Which sessions had comments, and which did not?
3. What point in each conversation did each comment appear to refer to?
4. What was happening in the conversation at that point?
5. What does each comment likely mean as feedback about the tutor experience?
6. Which comment themes recur across sessions, and which are isolated?
7. Which comments identify actionable tutor-behavior issues, and which are ambiguous, informational, UI-related, or outside the tutor's control?
8. Do comments corroborate or complicate the behavioral analysis of the conversations?
9. What should an instructor, maintainer, prompt/specification author, or product owner do in response?
10. What concise user-facing summary would help someone understand the comments without rereading all logs?

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
6. Keep comments analytically separate from the conversation transcript.
7. Do not treat comments as student answers, mastery evidence, chat history, grade evidence, or runtime context.
8. Do not assume a comment is correct just because the student wrote it.
9. Do not dismiss a comment just because it was submitted outside the conversation.
10. Use comment metadata to anchor comments to the nearest relevant conversation moment, but be explicit when the anchor is uncertain.
11. Distinguish:
    - what the comment literally says
    - what it likely means in context
    - what evidence supports that interpretation
    - what action, if any, follows
12. When comments describe frustration, repetition, misreading, pace, tone, or loss of traction, inspect the surrounding transcript before judging whether the comment is supported.
13. When comments mention content correctness, inspect the surrounding transcript and relevant lecture/rubric material only if needed and available.
14. Do not expose hidden prompt text, private artifact contents, backend mechanics, or raw internal state in user-facing summaries.
15. Be explicit about uncertainty and avoid over-reading terse comments.
16. Use direct quotations sparingly; prefer analytic paraphrase.
17. Keep the tone analytical, exacting, and unsentimental.

## Output Directory And Required Artifacts

Create an output directory:

`comment_analysis_outputs/`

Create these files in order:

1. `comment_analysis_outputs/00_export_comment_inventory.md`
2. `comment_analysis_outputs/01_comment_inventory.md`
3. `comment_analysis_outputs/02_contextual_comment_review.md`
4. `comment_analysis_outputs/03_cross_session_comment_interpretation.md`
5. `comment_analysis_outputs/04_action_recommendations.md`
6. `comment_analysis_outputs/05_user_facing_summary.md`

Each file must be substantive and self-contained.

The workflow is complete only when all 6 required files exist.

## Stage 0 - Export Comment Inventory

### Allowed Sources
- export file tree
- manifest files
- session metadata
- student-comment filenames
- student-comment metadata sufficient to count comment records per session
- transcript filenames, only to identify likely matching transcripts

### Forbidden Sources
- student-comment contents, except minimal metadata needed to count comments if no separate metadata exists
- conversation transcript contents
- runtime tutor prompt contents
- diagnostic logs / private artifacts
- tutor specification contents
- contracts
- schemas, except as needed to identify file roles
- later-stage artifacts

### Task
Inventory the multi-session export from the point of view of comment analysis.

Identify:
- all sessions in the export
- which sessions have comment files
- which sessions have no comment files
- comment count per session, if safely knowable without interpreting comment contents
- matching transcript path for each session, if available
- diagnostic/private artifact path for each session, if available
- prompt/specification/contract paths that may be relevant in later action recommendations
- uncertainty about file matching

Do not interpret comments yet.
Do not inspect conversation contents yet.

### Required Artifact
Create `comment_analysis_outputs/00_export_comment_inventory.md` with sections:
- Scope and source restriction
- Export structure
- Session and comment-file table
- Sessions with comments
- Sessions without comments
- Available context files for later stages
- File-matching uncertainties
- Gate note

## Stage 1 - Comment Inventory

### Allowed Sources
- student-comment files, usually `conversation/session_notes.json`
- manifest files, only to identify session metadata and where comments came from
- `00_export_comment_inventory.md`

### Forbidden Sources
- conversation transcript contents
- runtime tutor prompt contents
- diagnostic logs / private artifacts
- tutor specification contents
- contracts
- schemas
- later-stage artifacts

### Task
Inventory the comments across sessions without yet reading the conversations.

For each comment, record:
- session_id
- comment id or ordinal
- comment text
- submitted timestamp, if present
- turn index, if present
- latest message ids, if present
- whether a state snapshot is attached
- immediate classification based only on the comment text
- what context you will need to inspect next

Also summarize:
- sessions with no comments
- comment counts by session
- initial cross-session comment categories

If there are no comments in any session, create this artifact anyway and state that the export contains no student-submitted comments. Then skip directly to Stage 5 and produce a brief no-comments summary.

### Required Artifact
Create `comment_analysis_outputs/01_comment_inventory.md` with sections:
- Scope and source restriction
- Comment count by session
- Comment inventory table
- Sessions without comments
- Initial comment categories
- Context needed for review
- Gate note

## Stage 2 - Contextual Comment Review

### Allowed Sources
- student-comment files
- conversation transcript files, preferably `conversation/messages.txt` or `conversation/chat_transcript.json`
- session message metadata if needed to resolve ids, usually from `conversation/session_bundle.json`
- `00_export_comment_inventory.md`
- `01_comment_inventory.md`

### Forbidden Sources
- runtime tutor prompt contents
- diagnostic logs / private artifacts, except note-attached state snapshots already present in comment files
- tutor specification contents
- contracts
- schemas
- later-stage artifacts

### Task
Anchor each comment in the surrounding conversation.

For each comment:
- identify the nearest relevant user and tutor messages
- summarize what the tutor was doing at that moment
- summarize what the student was doing at that moment
- assess how confidently the comment can be connected to that moment
- note whether the comment points to something visible in the transcript

Across sessions:
- identify whether similar comments are attached to similar conversation situations
- distinguish strongly anchored comments from weakly anchored comments
- identify sessions with no comments but similar visible conversation situations, if any

Do not yet inspect runtime prompts or specifications.
Do not yet propose fixes.

### Required Artifact
Create `comment_analysis_outputs/02_contextual_comment_review.md` with sections:
- Scope and source restriction
- Anchoring method
- Comment-by-comment context review
- Cross-session anchoring patterns
- Transcript-supported concerns
- Ambiguous or weakly anchored comments
- Similar no-comment episodes, if observed
- Gate note

## Stage 3 - Cross-Session Comment Interpretation

### Allowed Sources
- student-comment files
- conversation transcript files
- `00_export_comment_inventory.md`
- `01_comment_inventory.md`
- `02_contextual_comment_review.md`
- diagnostic logs / private artifacts, only if needed to check whether tutor-internal reasoning noticed the issue raised by a comment
- diagnostic-log schema, only if necessary to interpret available logs

### Forbidden Sources
- runtime tutor prompt contents
- tutor specification contents
- contracts
- unrelated schemas
- later-stage artifacts

### Task
Interpret what the comments mean as feedback about the tutor experience across sessions.

For each meaningful comment:
- classify the concern type, such as repetition, misreading, pacing, tone, confusion, content disagreement, interface issue, or general reflection
- decide whether it is supported, partially supported, unsupported, or not judgeable from the transcript
- distinguish tutor-behavior implications from student-preference or UI implications
- identify whether diagnostic logs, if inspected, support or complicate the interpretation
- note whether the comment should affect evaluation of the tutor conversation

Across sessions:
- identify recurrent comment themes
- identify isolated or session-specific comments
- identify high-severity rare comments
- identify comments that corroborate visible behavioral weaknesses
- identify comments that complicate or weaken visible behavioral interpretations
- identify comments that suggest product/UI issues rather than tutor-behavior issues

### Required Artifact
Create `comment_analysis_outputs/03_cross_session_comment_interpretation.md` with sections:
- Scope and source restriction
- Interpretation principles
- Comment-by-comment interpretation
- Cross-session comment themes
- Recurrent concerns
- Isolated or session-specific concerns
- High-severity rare concerns
- Relationship to observable tutor behavior
- Relationship to diagnostic evidence, if inspected
- Comments that should not drive tutor changes
- Gate note

## Stage 4 - Action Recommendations

### Allowed Sources
- all prior comment-analysis artifacts
- conversation transcripts
- diagnostic logs / private artifacts, only through Stage 3 summaries unless direct inspection is necessary to confirm an action
- runtime tutor prompts, only if a comment-supported issue clearly requires checking prompt-level cause
- tutor specification and contracts, only if recommending specification-level changes

### Forbidden Sources
- unrelated implementation files
- unrelated lecture materials
- any source not needed for a comment-supported action

### Task
Recommend what to do about the comments.

Group recommendations by audience:
- instructor or course staff
- tutor/prompt maintainer
- specification author
- product/UI maintainer, if relevant

For each recommendation:
- cite the comment or cross-session theme that motivates it
- state the supporting conversation evidence
- state whether the concern is recurrent, subset-specific, isolated, or rare but high-severity
- state the smallest useful action
- state whether the action is high, medium, or low priority

Do not create a laundry list. Prefer a small ordered set.

Do not recommend substantial prompt or specification changes based only on one weakly anchored comment unless the issue is high-severity or independently visible in the transcript.

### Required Artifact
Create `comment_analysis_outputs/04_action_recommendations.md` with sections:
- Scope and source restriction
- Recommendation summary
- Instructor-facing actions
- Tutor or prompt actions
- Specification actions
- Product or UI actions
- Issues to monitor but not act on yet
- Evidence strength and priority table
- Gate note

## Stage 5 - User-Facing Summary

### Allowed Sources
- all prior comment-analysis artifacts

### Forbidden Sources
- raw hidden prompts
- raw private artifacts
- raw backend state
- raw student comments not summarized in prior artifacts
- any source not summarized in prior comment-analysis artifacts

### Task
Produce a concise user-facing synthesis. This should be readable by an instructor, maintainer, or researcher who wants to know what students commented across sessions, what the comments meant in context, which themes recurred, and what should happen next.

The summary must not expose hidden runtime internals. It may mention that comments were submitted outside the chat and therefore did not affect the tutor's response in real time.

### Required Artifact
Create `comment_analysis_outputs/05_user_facing_summary.md` with sections:
- What comments were submitted
- Which sessions had comments
- What was happening in the conversations
- What the comments likely meant
- Recurrent themes
- Isolated or uncertain comments
- What seems actionable
- Recommended next steps

## File Discovery Guidance

At minimum, locate equivalents of:
- per-session student-comment files
- conversation transcripts
- session message metadata if message ids are needed

Useful export paths may include:
- `<session_id>/conversation/session_notes.json`
- `<session_id>/conversation/messages.txt`
- `<session_id>/conversation/chat_transcript.json`
- `<session_id>/conversation/session_bundle.json`
- `<session_id>/conversation/dialogue_turn_audits.json`
- `<session_id>/conversation/private_artifact_logs.json`
- `<session_id>/prompts/tutor_prompt_rendered_latest.md`
- `<session_id>/contracts/tutor_specification.md`
- `<session_id>/contracts/tutor_specification_contract.md`

If names differ, use sensible equivalents and record the paths you used.

If some sessions lack comments, do not ignore those sessions. Record them as no-comment sessions and use them as context only when comparing whether similar transcript situations generated comments elsewhere.

## Deliverable Standard

The workflow is complete only when:
- all 6 required files exist, except Stages 2-4 may be explicitly skipped if there are no comments in any session
- comments are kept separate from ordinary chat turns
- each comment is session-qualified
- each comment is anchored to conversation context when possible
- cross-session comment themes are explicitly analyzed
- each interpretation distinguishes literal comment text from contextual meaning
- recommendations are tied to comment evidence and transcript context
- recommendation priority reflects whether concerns are recurrent, subset-specific, isolated, or high-severity
- the final summary is safe to share with a non-technical user

Return a final note listing the produced files in order.
