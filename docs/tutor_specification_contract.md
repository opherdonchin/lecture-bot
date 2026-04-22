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

The specification is the governing source of truth for pedagogical matters. The runtime prompt is the governing source of truth for runtime behavior.

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

B2 shapes the tutor's behavior toward depth, breadth, distinctions, and integration. When present, B2 governs those aspects of the runtime prompt. When absent, the generator may infer defaults from C, E, and the tutor's domain.

---

## 5. Section C — Tutor cognition

### 5.1 Required subsections

C must contain:

- **C1. Core decision architecture** (required)
- **C2. Interaction modes** (required)

C may also contain:

- **C3. Interaction lifecycle** (recommended)
- **C4. Applied interactional guidance** (recommended)

C1 and C2 may not be merged with each other or with any other subsection. C3 and C4, when present, must remain distinct from each other and from C1 and C2.

### 5.2 Explicit-or-delegated rule for C1 and C2 (required)

C1 and C2 each establish a structural commitment that shapes the tutor's behavior. For each of these subsections, the specification must either:

- **define structured content**, as specified below, or
- **explicitly state that the matter is left to the tutor's general judgment**.

Silence is not permitted. An empty or vague subsection is a contract violation, because the generator cannot distinguish "deliberately unconstrained" from "forgotten."

The structured content required if the subsection is not delegated:

- **C1** — an organizing decision process the tutor runs on each turn. This may be an explicit binary decision, a decision rule, or a decision algorithm. Other explicitly named decision-process forms are also permitted, but only if they are specified with comparable structural detail. The decision process must be aligned with the values and priorities expressed in section A Tutor foundations.
- **C2** — a named set of recurring interaction modes. Each named mode must have a short operational gloss.

If a subsection is delegated, the specification must say so in that subsection, in one sentence. The generator is then authorized to establish its own structure for the runtime prompt.

### 5.3 Admissible C1 forms and minimum requirements

When C1 is defined rather than delegated, it must describe at least one explicit decision-process form from the list in §5.2. If more than one form is used, the relationship among them must be stated explicitly.

The three most natural default forms are:

- **Explicit binary decision** — C1 states a two-way choice the tutor makes on each turn. The specification must name the two alternatives, state what that choice governs, and indicate what considerations or evidence bear on the choice.
- **Decision rule** — C1 states one or more if-then style rules. The specification must state the operative condition or conditions and the resulting tutor choice, orientation, or response tendency. If more than one rule is used, precedence or tie-breaking must be stated.
- **Decision algorithm** — C1 states a documented ordered series of cognitive or decision steps. This is the form to use when the specification means an explicit series of cognitive or decision steps. The steps must be ordered, operational, and decision-relevant. If the algorithm contains branches, loops, or checkpoints, the triggers for those should be stated.

Other explicitly named decision-process forms are also allowed, but they are optional rather than default. For example, a specification may instead use a multi-way decision, a weighted or comparative heuristic, or a state-based selector. If it does, that alternative form must be described with comparable structural detail. At minimum, the specification must state what is being decided, what the available options or outputs are, what considerations or evidence bear on the choice, and how the choice affects the tutor's behavior.

If C1 combines more than one form, the specification must state how they relate. For example, a binary decision may sit at the top of a decision algorithm, or a decision rule may govern when a later algorithmic sequence is invoked.

These C1 forms are pedagogical behavior specifications. They do **not** by themselves define a runtime output shape, require exposure of private reasoning, or authorize hidden-trace emission. Whether any such structure is externalized at runtime is governed separately by the backend/runtime contract.

### 5.4 C3 Interaction lifecycle (recommended)

When C3 is present, it should cover:

- starting-state behavior (how the tutor opens a session with no prior evidence or state),
- ending-state behavior (how the tutor handles session end or student signal of completion),
- repair and meta-conversation (how the tutor handles meta-questions, its own errors, or requests to explain its approach).

When C3 is absent, the generator produces runtime behavior using reasonable defaults and reports the omission per §10.

### 5.5 C4 coverage (recommended)

When C4 is present, it should cover at least:

- the tutor's visible conversational character,
- scaffolding and student ownership,
- how the tutor responds to difficulty,
- how the tutor handles student affect, distress, and out-of-scope requests,
- how the tutor handles student disagreement or pushback.

When C4 is absent, the generator infers applied guidance from C1, C2, A's tone commitments (if present), and E, and reports the omission per §10.

---

## 6. Section D — Evaluation

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
- **any B1, C1, or C2 subsection marked as delegated under §§4.2 or 5.2**.

The section may list additional items. Anything not listed is assumed to be governed by the specification body.

---

## 9. Authoring rules

### 9.1 Pedagogy, not runtime

The specification describes pedagogy, identity, and priorities. It does not describe JSON shapes, input variable names, state update rules, or output formatting unless overriding a runtime default under §8.

### 9.2 Explicit over implicit

Where the specification makes a commitment, it should make it explicit enough that the generator does not have to reconstruct it from mood. Named taxonomies should be named. Priority orderings should be stated as orderings. Decision processes should be stated in their chosen form.

If the specification chooses to include a documented decision algorithm under C1, that algorithm should be explicit enough to constrain behavior without relying on the generator to reconstruct its logic from tone or examples alone.

### 9.3 Consistency across sections

The specification must be internally consistent. In particular:

- the priority statement in A3, the role of evaluation in D1, and the success condition in E must agree;
- tone commitments in A, when present, must agree with conversational guidance in C4, when present;
- attention dimensions in B1, when named, must be consistent with the evidence criteria in D2;
- the decision process in C1 must be aligned with the values and priorities stated in A;
- documented decision processes in C1, when present, must be consistent with the stated interaction modes in C2 and must not silently contradict the tutor's priority ordering.

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
- the specific attention dimensions, modes, or decision processes chosen,
- the specific admissible form used for C1, beyond the structural requirements in §5.3,
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
- [ ] C contains C1 and C2.
- [ ] B1, C1, and C2 each define structured content or explicitly declare themselves delegated.
- [ ] If C1 is defined rather than delegated, it uses at least one admissible form and satisfies the relevant minimum requirements in §5.3.
- [ ] D contains D1; D contains D2 unless D1 declares evaluation to have no role.
- [ ] D declares evaluation shape: defined, delegated, or not applicable.
- [ ] If D2 is present, it describes stronger and weaker evidence.
- [ ] E states a success condition consistent with A3.
- [ ] A "Delegated to runtime" section is present and covers the items in §8.
- [ ] The specification contains no generator-targeted instructions.
- [ ] The specification is internally consistent per §9.3.

### Recommended (not required; generator should advise if absent)

- [ ] A states tone commitments, including any tone negations.
- [ ] B contains B2.
- [ ] C contains C3 covering starting-state, ending-state, and repair and meta-conversation.
- [ ] C contains C4 covering conversational character, scaffolding and student ownership, response to difficulty, student affect and distress, and student disagreement.
- [ ] Language and register are stated where non-default.

### Optional

- [ ] A states remit boundaries.
- [ ] C1 includes a documented decision algorithm or other multi-step decision procedure in addition to, or instead of, a simpler organizing process.
- [ ] The specification states its relation to other agents or tools.
- [ ] The specification carries a version identifier.
