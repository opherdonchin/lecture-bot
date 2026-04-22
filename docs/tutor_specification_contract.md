# Tutor Specification Contract

This contract defines what a tutor specification must contain, what it should contain, and what it may leave to the runtime prompt generator. A specification that conforms to this contract can be translated into a runtime tutor prompt by any generator that also conforms to this contract.

The contract is structural, not pedagogical. It constrains *where* information lives and *whether* decisions are made, not *what* pedagogical choices a specification makes.

Requirements in this contract fall into three tiers:

- **Required**: a specification that omits this is non-conforming.
- **Recommended**: a specification may omit this and still conform, but generators should note the omission and may emit advisory content about it outside the runtime prompt.
- **Optional**: a specification may include this when relevant; its absence is not flagged.

---

## 1. Purpose and scope

A tutor specification describes the pedagogical identity, priorities, and behavior of a tutor that will run against a fixed runtime contract.

The tutor specification is authored for human readers and read by the prompt generator. It is not read by the tutor at inference time. Whatever the tutor must know at runtime must be encoded by the generator into the runtime prompt.

The specification is the governing source of truth for pedagogical matters. The runtime prompt and runtime contract are the governing sources of truth for runtime behavior.

---

## 2. Required top-level structure

A conforming specification must contain five top-level sections, in this order, with these names:

- **A. Tutor foundations**
- **B. Tutor understanding**
- **C. Tutor cognition**
- **D. Evaluation**
- **E. Success condition**

and must end with:

- **A "Delegated to runtime" section** (see §8).

A specification may add further subsections within these top-level sections, but may not remove or rename them.

---

## 3. Section A — Tutor foundations

### 3.1 Required subsections

A must contain:

- **A1. Purpose** — what the tutor is for.
- **A2. Core identity** — what kind of agent the tutor is (teacher, coach, guide, examiner, or some combination), including its center of gravity and its stance.
- **A3. Core values and priorities** — what the tutor is trying to do on each turn.

### 3.2 Consolidated priority statement (required)

A3 must contain a **consolidated priority statement** that:

- names the tutor's ordered priorities,
- names the role of evaluation relative to those priorities, and
- is citable as one block (typically a single paragraph).

The priority statement must be internally consistent with any further priority language elsewhere in the specification.

### 3.3 Tone commitments (recommended)

Section A should state the tutor's intended tone, including any tone negations (things the tutor must not sound like). Tone commitments, if given, govern the runtime prompt's conversational-character guidance.

### 3.4 Remit boundaries (optional)

Section A may state boundaries of what the tutor should not do (for example: not teach new material outside the lecture, not give final answers on homework, not substitute for a human instructor on sensitive matters).

---

## 4. Section B — Tutor understanding

### 4.1 Required subsections

B must contain:

- **B1. View of the student and interaction**

### 4.2 Explicit-or-delegated rule for B1 (required)

B1 establishes a structural commitment that shapes the tutor's behavior. The specification must either:

- **define structured content**, as specified below, or
- **explicitly state that the matter is left to the tutor's general judgment**.

Silence is not permitted. An empty or vague B1 subsection is a contract violation, because the generator cannot distinguish "deliberately unconstrained" from "forgotten."

The structured content required if B1 is not delegated:

- **B1** — a named set of attention dimensions along which the tutor tracks the student and the interaction. Each named dimension must have a short operational gloss.

If B1 is delegated, the specification must say so in that subsection, in one sentence. The generator is then authorized to establish its own structure for the runtime prompt.

### 4.3 View of the subject matter (recommended)

B should contain:

- **B2. View of the subject matter / learning task**

B1 shapes the tutor's behavior toward depth, breadth, distinctions, and integration. When present, B1 governs those aspects of the runtime prompt. When absent, the generator may infer defaults from B3.2, D, and the tutor's domain.

### 4.3 Explicit-or-delegated rule (required)

C1 and C2 each establish a structural commitment that shapes the tutor's behavior. For each of these subsections, the specification must either:

- **define structured content**, as specified below, or
- **explicitly state that the matter is left to the tutor's general judgment**.

Silence is not permitted. An empty or vague subsection is a contract violation, because the generator cannot distinguish "deliberately unconstrained" from "forgotten."

The structured content required if the subsection is not delegated:

- **C1** — an organizing decision process the tutor runs on each turn. This may be an explicit binary decision, a decision rule, or a decision algorithm. Other explicitly named decision-process forms are also permitted, but only if they are specified with comparable structural detail. The decision process must be aligned with the values and priorities expressed in section A Tutor foundations.
- **C2** — a named set of recurring interaction modes. Each named mode must have a short operational gloss.

If a subsection is delegated, the specification must say so in that subsection, in one sentence. The generator is then authorized to establish its own structure for the runtime prompt.

### 4.4 B3.3 coverage (recommended)

When B3.3 is present, it should cover at least:

- the tutor's visible conversational character,
- scaffolding and student ownership,
- how the tutor responds to difficulty,
- how the tutor handles student affect, distress, and out-of-scope requests,
- how the tutor handles student disagreement or pushback.

When B3.3 is absent, the generator infers applied guidance from B3.1, B3.2, A's tone commitments (if present), and D, and reports the omission per §9.

### 4.5 B3.4 Interaction lifecycle (recommended)

When B3.4 is present, it should cover:

- starting-state behavior (how the tutor opens a session with no prior evidence or state),
- ending-state behavior (how the tutor handles session end or student signal of completion),
- repair and meta-conversation (how the tutor handles meta-questions, its own errors, or requests to explain its approach).

When B3.4 is absent, the generator produces runtime behavior using reasonable defaults and reports the omission per §9.

---

## 5. Section C — Evaluation

### 6.1 Required subsections

D must contain:

- **D1. Evaluation structure** — the role evaluation plays in the interaction and how it relates to teaching.
- **D2. Evaluation criteria** — what counts as stronger or weaker evidence of understanding. D2 is required unless D1 declares that evaluation has no role in this tutor's behavior.

### 6.2 Evaluation shape declaration (required)

D must declare the **evaluation shape**, meaning the structural form of evaluative state the tutor will maintain. The specification must choose one of:

- **Defined in specification**: D defines a schema for evaluative state (for example, a mastery scale, evidence-field structure, or equivalent), which the generator passes through unchanged.
- **Delegated to runtime**: D explicitly states that schemas for evaluative state are left to the runtime prompt, and the generator is responsible for defining them.
- **No evaluative role**: D1 declares the tutor does not maintain evaluative state, in which case no shape is needed.

Silence is not permitted.

### 6.3 Evidence-quality guidance (required when D2 is present)

D2 must describe, qualitatively or structurally, what counts as stronger evidence of understanding and what counts as weaker evidence. This guidance governs how conservatively the tutor updates evaluative state at runtime.

---

## 7. Section E — Success condition

Section E states what a successful turn and a successful overall interaction are trying to achieve.

The success condition must be consistent with the priority statement in A3. A short success condition (one or two sentences) is sufficient.

---

## 8. Delegated to runtime

A conforming specification must end with a section titled **"Delegated to runtime"**.

This section makes the division of labor between specification and generator explicit and auditable.

The section must state the specification's position on each of the following:

- **evaluative state schemas**: defined in specification, delegated to runtime, or not applicable (per §6.2).
- **input-variable handling**: whether the specification constrains how specific runtime inputs (for example rubric text, lecture context) are used, or leaves this to the generator.
- **output shape and state update rules**: by default delegated to the generator and runtime contract; the specification may override if it has reason to.
- **any B2, B3.1, or B3.2 subsection marked as delegated under §4.3**.

The section may list additional items. Anything not listed is assumed to be governed by the specification body.

---

## 9. Authoring rules

### 9.1 Pedagogy, not runtime

### 8.1 Pedagogy, not runtime

### 9.2 Explicit over implicit

### 8.2 Explicit over implicit

If the specification chooses to include a documented decision algorithm under C1, that algorithm should be explicit enough to constrain behavior without relying on the generator to reconstruct its logic from tone or examples alone.

### 9.3 Consistency across sections

The specification must be internally consistent. In particular:

- the priority statement in A3, the role of evaluation in C1, and the success condition in D must agree;
- tone commitments in A, when present, must agree with conversational guidance in B3.3, when present;
- attention dimensions in B2, when named, must be consistent with the evidence criteria in C2.

### 9.4 No generator-targeted instructions

The specification must not contain instructions directed at the generator. The generator's behavior is governed by a separate contract.

---

## 10. Generator behavior toward recommended sections

When a specification omits a recommended item, the generator:

- does not treat the omission as a conformance failure;
- produces the runtime prompt using reasonable inferences or defaults in place of the missing content;
- emits, outside the runtime prompt, a short advisory listing which recommended items were absent and, where useful, what the generator would suggest the specification add.

The advisory is for the specification author, not for the tutor. It does not modify the runtime prompt and must not be embedded in it.

Required items that are absent or in violation of this contract are conformance failures and the generator should report them as such rather than paper over them.

---

## 11. What this contract does not require

This contract does not constrain:

- the tutor's pedagogical philosophy,
- the specific attention dimensions, modes, or decision rules chosen,
- the specific evaluation schema, if one is defined,
- the length or literary style of the specification,
- the tutor's subject domain.

---

## 12. Conformance checklist

A specification conforms to this contract if and only if all required items below are satisfied. Recommended items are listed for generator advisory purposes; optional items are listed for reference.

### Required

- [ ] Top-level sections A, B, C, D, E are present, named, and in order.
- [ ] A contains A1, A2, A3.
- [ ] A3 contains a consolidated priority statement citable as one block.
- [ ] B contains B2 and B3; B3 contains B3.1 and B3.2.
- [ ] B2, B3.1, and B3.2 each define structured content or explicitly declare themselves delegated.
- [ ] C contains C1; C contains C2 unless C1 declares evaluation to have no role.
- [ ] C declares evaluation shape: defined, delegated, or not applicable.
- [ ] If C2 is present, it describes stronger and weaker evidence.
- [ ] D states a success condition consistent with A3.
- [ ] A "Delegated to runtime" section is present and covers the items in §7.
- [ ] The specification contains no generator-targeted instructions.
- [ ] The specification is internally consistent per §9.3.

### Recommended (not required; generator should advise if absent)

- [ ] A states tone commitments, including any tone negations.
- [ ] B contains B1.
- [ ] B contains B3.3 covering conversational character, scaffolding and student ownership, response to difficulty, student affect and distress, and student disagreement.
- [ ] B contains B3.4 covering starting-state, ending-state, and repair and meta-conversation.
- [ ] Language and register are stated where non-default.

### Optional

- [ ] A states remit boundaries.
- [ ] The specification states its relation to other agents or tools.
- [ ] The specification carries a version identifier.
