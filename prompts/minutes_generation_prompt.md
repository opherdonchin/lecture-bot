# Prompt: Generate selective instructional minutes JSON for rubric generation

Use this prompt in a fresh chat. Upload exactly these lecture files before sending the prompt:

- lecture slides
- lecture handout
- lecture notebook
- lecture transcript

---

You are producing a canonical file called **instructional_minutes.json** for later use in **lecture mastery rubric generation** and **runtime tutoring context**.

Your job is not to summarize the lecture in full.
Your job is to produce **selective teaching notes** that capture only the oral material that should actually change how the lecture is assessed or tutored.

Think of this file as:

- a compact record of orally sharpened distinctions
- a record of confusions that were actually resolved in class
- a record of warnings against common mistakes
- a record of oral interpretations of figures, formulas, code, plots, or worked examples that matter conceptually
- a record of what felt central versus incidental

Do not turn this into:

- a second handout
- a cleaned-up transcript
- a detailed lecture reconstruction
- a turn-by-turn chronology

## Output format

Return JSON only.
Do not return markdown.
Do not wrap the JSON in code fences.
Do not add commentary before or after the JSON.

## Source roles

Treat the uploaded sources as serving different roles.

- **Slides**: lecture structure, sequence, section boundaries, named concepts, figures, examples, and declared emphasis
- **Handout**: compact conceptual reconstruction of the lecture
- **Notebook**: demonstrations, code, plots, formulas, and worked examples that may need interpretation
- **Transcript**: oral clarification, emphasis, warnings, distinctions, student-triggered clarifications, and interpretation

Follow the lecture's actual structure mainly from the slides and handout.
Use the notebook only to understand demonstrations and interpretation targets.
Use the transcript only to extract oral teaching that materially changes what should count as understanding.

Do not let transcript noise override lecture structure.

## Core principles

1. Use only the uploaded materials.
2. Be selective.
3. Prefer conceptual value over transcript fidelity.
4. Preserve oral teaching only when it materially sharpens assessment or tutoring.
5. Generalize useful student questions into conceptual clarifications.
6. Omit weak, garbled, or uncertain transcript content rather than guessing.
7. If a topic was mostly static and not orally deepened, let that show.
8. If something was only mentioned briefly, treat it as brief.
9. Avoid trivia, anecdotes, greetings, logistics, and local classroom management.
10. Keep the file compact enough to be useful at runtime.

## Important boundedness rules

- Include at most **8 sections**.
- Use short, information-dense bullets.
- Keep most arrays to **0–4 items**.
- Use empty arrays instead of padding with weak content.
- If an oral point does not clearly affect mastery or tutoring, omit it.

## Mastery-oriented lens

The downstream rubric and tutor will care especially about:

- criterion: what makes the concept what it is
- distinction: how it differs from nearby confusions
- explanation: what the student should be able to explain in their own words
- interpretation: what a figure / formula / plot / code block means
- warning / correction: where students can sound right while still being wrong

You are not assigning grades.
You are extracting the oral material that should influence what counts as weak, partial, and strong evidence.

## Required output schema

Return a JSON object with exactly this top-level structure:

{
  "lecture_metadata": {
    "title": "",
    "lecture_identifier": "",
    "main_purpose": "",
    "source_files": {
      "slides": "",
      "handout": "",
      "notebook": "",
      "transcript": ""
    }
  },
  "teaching_notes": {
    "central_arc": [],
    "sections": [
      {
        "section_id": "",
        "section_title": "",
        "importance": "",
        "teaching_goal": "",
        "orally_sharpened_distinctions": [],
        "resolved_confusions": [],
        "warnings_common_mistakes": [],
        "oral_interpretations": [
          {
            "kind": "",
            "item": "",
            "takeaway": ""
          }
        ],
        "high_value_checks": [],
        "incidental_or_do_not_assess": []
      }
    ],
    "cross_section_priorities": {
      "highest_value_distinctions": [],
      "sound_right_but_wrong_risks": [],
      "important_interpretations": [],
      "brief_or_incidental_topics": []
    }
  },
  "rubric_handoff": {
    "static_materials_sufficient_for": [],
    "minutes_matter_most_for": [],
    "do_not_turn_into_direct_questions": []
  }
}

## Field semantics

### teaching_notes.central_arc
3–6 bullets describing the lecture's main conceptual movement.
Keep this high-level and selective.

### teaching_notes.sections
Use the lecture's real sections, not arbitrary transcript chunks.
Include only sections where selective teaching notes are genuinely useful.

### sections[].importance
Use one of:

- "core"
- "important"
- "brief"

### sections[].teaching_goal
One short sentence naming what this part of the lecture was trying to help students understand.

### sections[].orally_sharpened_distinctions
Only distinctions that were materially clearer because of oral teaching.

### sections[].resolved_confusions
Generalized misunderstandings that were corrected.
Do not preserve raw dialogue.

### sections[].warnings_common_mistakes
Warnings that should influence later tutoring or rubric design.

### sections[].oral_interpretations
Use only when oral explanation materially helped interpret:

- a figure
- a formula
- a code block
- a plot
- a worked example
- a notebook demonstration

Allowed `kind` values:

- "figure"
- "formula"
- "code"
- "plot"
- "example"
- "notebook_demo"

### sections[].high_value_checks
Short bullets describing the most valuable things a later tutor or rubric writer might actually check from this section.
These are not full questions.
They are evidence targets.

### sections[].incidental_or_do_not_assess
Items that may be contextually useful but should not become direct tutoring or rubric targets.

### teaching_notes.cross_section_priorities
Use this to surface the highest-value lecture-wide tutoring implications:

- distinctions that matter a lot
- places students can sound right without understanding
- interpretations of figures/code/formulas that deserve attention
- topics that were brief enough to downweight

### rubric_handoff
Use this to tell the later rubric writer:

- where slides/handout are already enough
- where oral minutes really matter
- what should not become direct assessment prompts

## Additional instructions

- Preserve the lecture's actual sequence.
- Do not quote long transcript passages.
- Do not include who said what unless unavoidable.
- Do not create extra fields.
- Use empty arrays rather than speculative content.
- If the notebook mattered only as a setup for oral interpretation, capture the interpretation, not the notebook in full.
