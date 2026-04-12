# Workflow — Generating and Installing Step-1 Prompt Files

This document gives a practical, execution-ordered workflow for producing the step-1 prompt files and placing them in the repository.

This is a human-facing procedure.
It is meant to be followed manually with the help of a chatbot or coding agent.

---

## Goal

Produce and install the following prompt-related files:

- `prompts/generation/classifier_system_prompt_generator.md`
- `prompts/generation/respond_system_prompt_generator.md`
- `prompts/generation/provide_content_support_system_prompt_generator.md`
- `prompts/generation/provide_technical_support_system_prompt_generator.md`
- `prompts/generation/redirect_system_prompt_generator.md`
- `prompts/generation/seek_clarification_system_prompt_generator.md`

Then use those prompt-generation prompts to generate the actual system prompts that will later be consumed by the application.

---

## Recommended execution order

1. Create the new directories in the repo.
2. Add the step-1 specification document.
3. Add the six prompt-generation prompt files.
4. Use a chatbot to generate the six actual system prompts.
5. Save those generated system prompts into a separate location for later integration.
6. Only after the prompts look good, ask the coding agent to wire them into the app.

---

## Directory setup

Create these directories if they do not already exist:

```text
lecture-bot-main/docs/workflows/
lecture-bot-main/prompts/generation/
lecture-bot-main/prompts/generated/
```

Use `prompts/generation/` for the prompt-generation prompts.
Use `prompts/generated/` for the actual generated system prompts.

---

## Step-by-step procedure

### Step 1 — Add the specification file

Create:

* `docs/policy_routing_spec.md`

Paste into it the contents from the repo documentation bundle.

This file is the source of truth for step 1.

---

### Step 2 — Add the prompt-generation prompt files

Create these files:

* `prompts/generation/classifier_system_prompt_generator.md`
* `prompts/generation/respond_system_prompt_generator.md`
* `prompts/generation/provide_content_support_system_prompt_generator.md`
* `prompts/generation/provide_technical_support_system_prompt_generator.md`
* `prompts/generation/redirect_system_prompt_generator.md`
* `prompts/generation/seek_clarification_system_prompt_generator.md`

Paste each file's corresponding content from the documentation bundle.

---

### Step 3 — Generate the actual system prompts

For each file in `prompts/generation/`, do the following in a chatbot:

1. Open the generator file.
2. Copy its entire contents.
3. Paste it into a fresh chatbot conversation.
4. Ask the chatbot to return only the final system prompt.
5. Save the result into `prompts/generated/` using the parallel filename:

Examples:

* generator: `prompts/generation/classifier_system_prompt_generator.md`

* generated output: `prompts/generated/classifier_system_prompt.md`

* generator: `prompts/generation/respond_system_prompt_generator.md`

* generated output: `prompts/generated/respond_system_prompt.md`

Do this for all six generator files.

---

### Step 4 — Review generated prompts manually

Before wiring anything into code, read all six generated system prompts.

Check especially for:

* classifier prompt stays narrow and returns JSON only
* respond prompt does not reveal answers too quickly
* content-support prompt scaffolds without inviting parroting
* technical-support prompt stays procedural and does not reveal content
* redirect prompt is brief and not punitive
* seek-clarification prompt asks only one short clarifying question

Do not skip this review.

---

### Step 5 — Ask the coding agent to install prompt loading support

After the six generated prompt files exist and look reasonable, ask the coding agent to do the code integration work.

At this stage, the coding agent should:

* add prompt-loading support from disk
* add classifier schema and policy-decision schema
* implement the policy decider class
* add the new logging table
* connect classifier → policy decision → prompt-family response generation
* add tests

Suggested coding-agent prompt:

> Read `docs/policy_routing_spec.md` and the files in `prompts/generated/`. Implement step 1 exactly as specified. Keep changes as small and local as possible. Add tests for classifier logging, policy decision overrides, and basic routing behavior. Do not implement later tutoring-move or scoring changes yet.

---

### Step 6 — Run a first local validation pass

After the coding agent finishes:

1. run tests
2. start the app locally
3. try a few messages of each type:

   * genuine content answer
   * genuine content question
   * technical request
   * meta request
   * off-task message
   * ambiguous mixed message
4. inspect logs / database records for classifier output and policy decision

---

## Exact file mapping

### Generator files

* `prompts/generation/classifier_system_prompt_generator.md`
* `prompts/generation/respond_system_prompt_generator.md`
* `prompts/generation/provide_content_support_system_prompt_generator.md`
* `prompts/generation/provide_technical_support_system_prompt_generator.md`
* `prompts/generation/redirect_system_prompt_generator.md`
* `prompts/generation/seek_clarification_system_prompt_generator.md`

### Generated output files

* `prompts/generated/classifier_system_prompt.md`
* `prompts/generated/respond_system_prompt.md`
* `prompts/generated/provide_content_support_system_prompt.md`
* `prompts/generated/provide_technical_support_system_prompt.md`
* `prompts/generated/redirect_system_prompt.md`
* `prompts/generated/seek_clarification_system_prompt.md`

---

## Practical chatbot instructions by step

### To generate a prompt from a generator file

Use this exact instruction in the chatbot after pasting the generator file:

> Return only the final system prompt. Do not add commentary, headings, or explanation.

### To ask the coding agent to integrate step 1 after prompt generation

Use this instruction:

> Read `docs/policy_routing_spec.md` and all files in `prompts/generated/`. Implement the step-1 routing/classification layer. Keep the existing app behavior intact except where the spec requires change. Add the smallest necessary database, schema, and bot engine changes. Add or update tests accordingly.

---

## Notes

* Do not ask the coding agent to generate the prompt text and wire it into the app in the same step.
* Generate prompts first.
* Review them.
* Then integrate.
* Keep multi-agent tuning for a later issue.
