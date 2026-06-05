# Tutor Specification Contract

This contract defines what a tutor specification must contain, what it should contain, and what it may leave to prompt generation and runtime. A specification that conforms to this contract can be translated into a runtime tutor prompt by any generator that also conforms to this contract.

The contract is structural, not pedagogical. It constrains where information lives and whether decisions are made, not what pedagogical choices a specification makes.

Requirements in this contract fall into three tiers:

- **Required**: a specification that omits this is non-conforming.
- **Recommended**: a specification may omit this and still conform, but generators should note the omission and may emit advisory content about it outside the runtime prompt.
- **Optional**: a specification may include this when relevant; its absence is not flagged as an omission.

For C5 specifically, absence does not mean the area is ignored. Missing C5 means inspectability and self-verification commitments are implicitly delegated to prompt generation and runtime, which must synthesize appropriate commitments from the specification's explicit and implied requirements.

---

## 1. Purpose and scope

A tutor specification describes the pedagogical identity, priorities, cognition, evaluation stance, and success condition of a tutor that will run against a fixed backend/runtime contract.

The tutor specification is authored for human readers and read by the prompt generator. It is not read directly by the tutor at inference time. Whatever the tutor must know at runtime must be encoded by the generator into the runtime tutor prompt and, when applicable, the private artifact schema.

The specification is the governing source of truth for pedagogical matters. The runtime prompt and backend/runtime contract are the governing sources of truth for runtime behavior, transport, validation, storage, persistence, visibility, lifecycle control, and backend-owned state.

Raw mastery evaluation remains part of the tutor/specification shape. Student-facing grade calibration, ranked full-credit targets, and session-credit status are backend-owned runtime mechanics; a specification may describe how to respond pedagogically to backend-provided full-credit guidance, but must not redefine the grading arithmetic.

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
- **A2. Core identity** — what kind of agent the tutor is, including its center of gravity and stance.
- **A3. Core values and priorities** — what the tutor is trying to do on each turn.

### 3.2 Consolidated priority statement (required)

A3 must contain a **consolidated priority statement** that:

- names the tutor's ordered priorities,
- names the role of evaluation relative to those priorities, and
- is citable as one block, typically a single paragraph.

The priority statement must be internally consistent with any further priority language elsewhere in the specification.

### 3.3 Tone commitments (recommended)

Section A should state the tutor's intended tone, including any tone negations. Tone commitments, if given, govern the runtime prompt's conversational-character guidance.

### 3.4 Remit boundaries (optional)

Section A may state boundaries of what the tutor should not do.

---

## 4. Section B — Tutor understanding

### 4.1 Required subsections

B must contain:

- **B1. View of the student and interaction**

B should contain:

- **B2. View of the subject matter / learning task**

### 4.2 Explicit-or-delegated rule for B1 (required)

B1 establishes a structural commitment that shapes the tutor's behavior. The specification must either:

- define structured content, such as a named set of attention dimensions with short operational glosses, or
- explicitly state that the matter is left to the tutor's general judgment.

Silence is not permitted. An empty or vague B1 subsection is a contract violation, because the generator cannot distinguish deliberately unconstrained from forgotten.

If B1 is delegated, the specification must say so in that subsection. The generator is then authorized to establish its own structure for the runtime prompt, consistent with the rest of the specification.

### 4.3 B2 guidance (recommended)

B2 should describe how the tutor views the subject matter, learning task, conceptual depth and breadth, connections, distinctions, transfer, and integration. When absent, the generator infers applied guidance from A, C, D, and the domain, and reports the omission per §9.

---

## 5. Section C — Tutor cognition

### 5.1 Required subsections

C must contain:

- **C1. Core decision architecture**
- **C2. Interaction modes**

### 5.2 Explicit-or-delegated rule for C1 and C2 (required)

C1 and C2 each establish structural commitments that shape the tutor's behavior. For each subsection, the specification must either:

- define structured content, as specified below, or
- explicitly state that the matter is left to the tutor's general judgment.

Silence is not permitted. An empty or vague subsection is a contract violation.

The structured content required if the subsection is not delegated:

- **C1** — an organizing decision process the tutor runs on each turn. This may be an explicit binary decision, a decision rule, or a decision algorithm. Other explicitly named decision-process forms are also permitted, but only if they are specified with comparable structural detail. The decision process must be aligned with the values and priorities expressed in section A.
- **C2** — a named set of recurring interaction modes. Each named mode must have a short operational gloss.

If a subsection is delegated, the specification must say so in that subsection. The generator is then authorized to establish its own structure for the runtime prompt, consistent with the rest of the specification.

### 5.3 C3. Interaction lifecycle (recommended)

When present, C3 should cover:

- starting-state behavior,
- ending-state behavior,
- time-aware behavior when time information is provided,
- repair and meta-conversation.

When absent, the generator produces runtime behavior using reasonable defaults compatible with the backend/runtime contract and reports the omission per §9.

### 5.4 C4. Applied interactional guidance (recommended)

When present, C4 should cover:

- the tutor's visible conversational character,
- scaffolding and student ownership,
- how the tutor responds to difficulty,
- how the tutor handles student affect, distress, and out-of-scope requests,
- how the tutor handles student disagreement or pushback.

When absent, the generator infers applied guidance from A, B, C1, C2, and D, and reports the omission per §9.

### 5.5 C5. Inspectability / self-verification commitments (optional)

A specification may define private inspectability or self-verification commitments when these materially constrain tutor behavior.

These commitments may require explicit internal checks, comparisons, evidence-verification steps, or preservation of a private account of selected decision-relevant steps.

These commitments are pedagogical and behavioral commitments. They are not transport specifications, storage specifications, schema specifications, database designs, validation mechanics, or visibility rules.

If C5 is present, it governs inspectability and self-verification for the tutor described by the specification. The prompt generator must preserve and operationalize it within the backend/runtime contract.

If C5 is absent, inspectability and self-verification commitments are implicitly delegated to prompt generation and runtime. In that case, the prompt generator must synthesize appropriate commitments from the specification's explicit and implied requirements, aligned with purpose, identity, priorities, cognition, evaluation philosophy, and success condition.

Missing C5 is therefore not a conformance failure, not a recommended omission, and not permission to omit inspectability or self-verification entirely.

---

## 6. Section D — Evaluation

### 6.1 Required subsections

D must contain:

- **D1. Evaluation structure** — the role evaluation plays in the interaction and how it relates to teaching.
- **D2. Evaluation criteria** — what counts as stronger or weaker evidence of understanding. D2 is required unless D1 declares that evaluation has no role in this tutor's behavior.

### 6.2 Evaluation shape declaration (required)

D must declare the **evaluation shape**, meaning the structural form of evaluative state the tutor will maintain. The specification must choose one of:

- **Defined in specification**: D defines the evaluative shape, such as a mastery scale, evidence-field structure, or equivalent, which the generator preserves except where the backend/runtime contract makes it impossible.
- **Delegated to runtime**: D explicitly states that concrete evaluative schemas are left to runtime, and the generator is responsible for defining them within the backend/runtime contract.
- **No evaluative role**: D1 declares the tutor does not maintain evaluative state, in which case no shape is needed.

Silence is not permitted.

### 6.3 Evidence-quality guidance (required when D2 is present)

D2 must describe what counts as stronger evidence of understanding and what counts as weaker evidence. This guidance governs how conservatively the tutor updates evaluative state at runtime.

---

## 7. Section E — Success condition

Section E states what a successful turn and a successful overall interaction are trying to achieve.

The success condition must be consistent with the priority statement in A3. A short success condition is sufficient.

---

## 8. Delegated to runtime

A conforming specification must end with a section titled **"Delegated to runtime"**.

This section makes the division of labor between specification, prompt generation, and runtime explicit and auditable.

The section must state the specification's position on each of the following:

- **evaluative state schemas**: defined in specification, delegated to runtime, partly delegated to runtime, or not applicable (per §6.2).
- **input-variable handling**: whether the specification constrains how specific runtime inputs are used, or leaves this to the generator and runtime.
- **output shape and state update rules**: by default delegated to the generator and backend/runtime contract; the specification may constrain them only pedagogically.
- **inspectability / self-verification**: governed by C5 if present; implicitly delegated to prompt generation and runtime if C5 is absent.
- **transport of private artifacts, schema for private artifacts, storage and persistence, validation, and visibility**: delegated to the backend/runtime contract unless explicitly overridden by a higher-level project decision outside the tutor specification.
- **any B1, C1, or C2 subsection marked as delegated**.

The section may list additional items. Anything not listed is assumed to be governed by the specification body for pedagogical matters and by the backend/runtime contract for runtime mechanics.

---

## 9. Authoring rules

### 9.1 Pedagogy, not runtime

The specification should describe pedagogical commitments, not backend mechanics. It should not define runtime field names, prompt file names, schema file names, database tables, storage mechanics, persistence mechanics, validation mechanics, transport details, or UI behavior.

### 9.2 Explicit over implicit

If the specification chooses to include a documented decision algorithm under C1, that algorithm should be explicit enough to constrain behavior without relying on the generator to reconstruct its logic from tone or examples alone.

If the specification chooses to include C5, those commitments should be explicit enough to constrain behavior while still leaving runtime mechanics to the backend/runtime contract.

### 9.3 Consistency across sections

The specification must be internally consistent. In particular:

- the priority statement in A3, the tutor cognition in C, the role of evaluation in D, and the success condition in E must agree;
- tone commitments in A, when present, must agree with applied interactional guidance in C4, when present;
- attention dimensions in B1, when named, must be consistent with the evidence criteria in D2.

### 9.4 No generator-targeted instructions

The specification must not contain instructions directed at the generator. The generator's behavior is governed by a separate prompt and by this contract.

---

## 10. Generator behavior toward recommended sections

When a specification omits a recommended item, the generator:

- does not treat the omission as a conformance failure;
- produces the runtime prompt using reasonable inferences or defaults in place of the missing content;
- emits, outside the runtime prompt, a short advisory listing which recommended items were absent and, where useful, what the generator would suggest the specification add.

The advisory is for the specification author, not for the tutor. It does not modify the runtime prompt and must not be embedded in it.

Required items that are absent or in violation of this contract are conformance failures and the generator should report them rather than paper over them.

Absent C5 is handled by implicit delegation under §5.5, not by advisory.

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
- [ ] B contains B1.
- [ ] B1 defines structured content or explicitly declares itself delegated.
- [ ] C contains C1 and C2.
- [ ] C1 and C2 each define structured content or explicitly declare themselves delegated.
- [ ] D contains D1 and, unless evaluation has no role, D2.
- [ ] D declares evaluation shape: defined, delegated, partly delegated, or not applicable.
- [ ] If D2 is present, it describes stronger and weaker evidence.
- [ ] E states a success condition consistent with A3.
- [ ] The specification ends with a **Delegated to runtime** section.
- [ ] Delegated-to-runtime coverage includes evaluative state schemas, input-variable handling, output shape and state update rules, inspectability / self-verification, private-artifact mechanics, and any delegated B1, C1, or C2 items.
- [ ] The specification contains no generator-targeted instructions.

### Recommended

- [ ] A includes tone commitments.
- [ ] B includes B2.
- [ ] C includes C3.
- [ ] C includes C4.

### Optional

- [ ] A includes remit boundaries.
- [ ] C includes C5. If absent, inspectability / self-verification is implicitly delegated to prompt generation and runtime.
