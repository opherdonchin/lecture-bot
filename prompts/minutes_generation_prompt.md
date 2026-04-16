# Prompt: Generate instructional minutes JSON for rubric generation

Use this prompt in a fresh chat. Upload exactly these lecture files before sending the prompt:

- lecture slides
- lecture handout
- lecture notebook
- lecture transcript

---

You are producing a canonical file called **instructional_minutes.json** for later use in **lecture mastery rubric generation**.

Your job is **not** to summarize the class as an event.
Your job is to extract the **instructional content actually imparted in the lecture**, especially where the oral teaching deepened understanding beyond the static materials.

The downstream rubric will use this file to identify:

- what concepts were actually explained
- what distinctions were sharpened orally
- what confusions were resolved
- what notebook / figure / formula / code interpretations were given orally
- what warnings were given against common mistakes
- what seemed central versus incidental
- what kinds of understanding should later count as stronger or weaker evidence of mastery

## Output format

Return **JSON only**.
Do not return markdown.
Do not wrap the JSON in code fences.
Do not add commentary before or after the JSON.

## Why this file exists

This file is meant to support a later **mastery rubric**, not to serve as lecture notes or transcript cleanup.

That means the file should preserve:

- conceptual deepening
- orally sharpened distinctions
- resolved confusions in generalized form
- orally given interpretations of figures, formulas, plots, code, and examples
- mastery-relevant takeaways

And it should suppress:

- event chronology for its own sake
- logistics
- greetings
- jokes
- transcript garbage
- repetitive restatement
- local classroom management
- who said what
- attendance-dependent details
- exact wording unless the wording itself matters conceptually

## Source roles

Treat the uploaded sources as serving different roles.

- **Slides**: intended lecture structure, sequence, section boundaries, named concepts, figures, examples, and declared emphasis
- **Handout**: compact conceptual reconstruction of the lecture
- **Notebook**: concrete demonstrations, code, plots, distributions, formulas, and worked examples
- **Transcript**: oral clarification, elaboration, distinctions, student-triggered clarifications, warnings, and interpretation

Follow the **lecture flow and scope** primarily from the slides and handout.
Use the notebook to understand what was concretely demonstrated.
Use the transcript to extract what was **actually explained orally beyond the static materials**.

Do not let transcript noise override lecture structure.

## Core principles

1. Use only the uploaded materials.
2. Follow the lecture’s actual section order.
3. Distinguish clearly between:
   - what was already present in the static materials
   - what was added or sharpened orally
4. Generalize useful student questions into conceptual clarifications.
5. Prefer conceptual value over transcript fidelity.
6. Do not create trivia.
7. Keep the file maximally useful for later rubric writing.
8. If the transcript is garbled or uncertain, omit or downweight that content rather than guessing.
9. If something was only mentioned briefly and not really explained, say so.
10. If the notebook materially deepened a topic, preserve that.

## Important mastery-oriented lens

The later rubric will care about evidence of understanding along lines such as:

- criterion: what makes the concept what it is
- distinction: how it differs from nearby confusions
- explanation: why a claim or classification is correct
- interpretation: what a figure / formula / code block / plot means
- transfer: how the idea applies in a nearby case
- warning / correction: what students are likely to get wrong

You are **not** assigning grades or mastery levels.
But you **are** extracting the material that would let a later rubric writer define weak, partial, and strong evidence of mastery.

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
  "lecture_wide_summary": {
    "conceptual_arc": [],
    "main_oral_deepenings": [],
    "most_central_for_rubric": [],
    "likely_not_assessable_directly": []
  },
  "sections": [
    {
      "section_id": "",
      "section_title": "",
      "time_range": {
        "start": "",
        "end": ""
      },
      "importance": "",
      "static_match": [],
      "oral_additions": [],
      "sharpened_distinctions": [],
      "resolved_confusions": [],
      "oral_interpretations": [
        {
          "kind": "",
          "item": "",
          "takeaway": ""
        }
      ],
      "warnings_common_mistakes": [],
      "what_seemed_central": [],
      "what_seemed_incidental": [],
      "mastery_support": {
        "criterion_points": [],
        "distinction_points": [],
        "explanation_points": [],
        "interpretation_points": [],
        "transfer_hooks": [],
        "near_misses": []
      },
      "assessable_takeaways": [],
      "not_for_direct_assessment": []
    }
  ],
  "cross_section_synthesis": {
    "concepts_substantially_deepened_orally": [],
    "distinctions_likely_to_separate_weak_from_strong_understanding": [],
    "confusions_that_should_probably_become_near_misses_in_the_rubric": [],
    "figure_formula_code_plot_interpretations_that_should_influence_the_rubric": [],
    "topics_that_were_brief_or_incidental": [],
    "candidate_high_value_targets_for_short_review": []
  },
  "rubric_handoff_notes": {
    "where_static_materials_are_sufficient": [],
    "where_minutes_are_essential": [],
    "where_notebook_material_matters_for_mastery": [],
    "where_students_could_sound_right_without_understanding": [],
    "cautions_for_the_rubric_writer": []
  }
}

## Field semantics

### lecture_wide_summary.conceptual_arc
3–8 bullets describing the overall conceptual movement of the lecture.

### lecture_wide_summary.main_oral_deepenings
Only include content where the oral teaching materially sharpened, clarified, or extended the static materials.

### sections[].importance
Use one of:
- "core"
- "important"
- "brief"

This should reflect actual lecture emphasis, not just slide count.

### sections[].static_match
What this section clearly covered in the slides / handout / notebook even without the transcript.

### sections[].oral_additions
What was genuinely added or materially clarified orally beyond the static materials.

### sections[].sharpened_distinctions
Distinctions that became clearer in speech than they would be from the static files alone.

Examples:
- reality vs data vs model
- precision vs validity vs reliability
- proxy vs true quantity
- aleatory vs epistemic uncertainty
- PDF vs CDF
- kurtosis vs simple spread

Do not force these exact examples if they are not actually supported by the uploaded files.

### sections[].resolved_confusions
Generalized misunderstandings that were corrected.
Do not preserve them as transcript dialogue.
State them as conceptual clarifications.

### sections[].oral_interpretations
Use this only when the instructor’s oral explanation materially helped interpret:
- a figure
- a formula
- a code block
- a plot
- a worked example

Each entry should contain:
- "kind": one of "figure", "formula", "code", "plot", "example", "notebook_demo"
- "item": brief identifier
- "takeaway": what the oral explanation helped the student understand

### sections[].mastery_support
This is the most important part for later rubric generation.

Populate it with short, concrete bullets:

- **criterion_points**: what students must understand to have the basic idea right
- **distinction_points**: nearby confusions they must separate
- **explanation_points**: what they should be able to explain in their own words
- **interpretation_points**: what they should be able to interpret from figure / code / formula / plot material
- **transfer_hooks**: nearby cases or checks that could test stronger understanding
- **near_misses**: ways students could sound right while still being wrong or shallow

### sections[].assessable_takeaways
2–6 bullets stating what a later rubric writer should probably treat as assessable understanding from this section.

### sections[].not_for_direct_assessment
Brief items that may be useful context but should probably not become direct rubric targets.

## Additional instructions

- Align section boundaries to the lecture’s real sections, not to arbitrary transcript chunks.
- Merge transcript material into section-level understanding rather than preserving turn-by-turn dialogue.
- Preserve timestamps at the section level only.
- Use short, information-dense bullets.
- Use empty arrays rather than inventing content.
- Do not include any field not in the schema.
- Do not quote long stretches of transcript.
- Do not include raw Q&A unless the conceptual point cannot be preserved otherwise.
- Do not include “student asked…” unless that context is necessary; prefer the generalized clarification itself.
- If the transcript contains uncertainty or ASR errors, omit those details.
- If a topic was mostly static and not orally deepened, let that show.
- If the oral teaching made a major difference to later mastery assessment, make that explicit.

## Final rule

This file should be the **best possible handoff artifact for later rubric generation**.

That means it should be:
- section-aligned
- concept-first
- mastery-relevant
- faithful to the uploaded materials
- stripped of transcript noise
- structured enough that a later system can reliably use it
