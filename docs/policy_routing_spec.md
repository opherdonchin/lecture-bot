# Step 1 Spec - Policy Routing, Tutoring Heuristics, and Prompt Families

## Purpose

This document specifies the first major redesign step for the lecture bot:

1. classify every student message
2. log the classifier output
3. choose an effective response policy
4. generate the response using a policy-specific prompt family

This step is intended to improve:
- resistance to gaming and prompt-probing
- separation between content tutoring and technical or session-steering support
- flexibility of the tutor without hard-coding brittle Python semantics
- inspectability through structured logging
- conversational quality through heuristics rather than a rigid move sequence

This step does **not** redesign the top-level grading formula.
The weighted-best-5 architecture stays:
- 55
- 25
- 13
- 4
- 3

This step **does** revise within-topic mastery semantics and tutoring heuristics.

---

## Core design principles

- Every student message is classified.
- Classification is soft, not certain.
- Policy choice happens after classification.
- Hard backstops stay narrow and only catch clearly disallowed requests.
- Allowed session-steering requests are part of normal tutoring, not a failure mode.
- The tutor should choose from a broad move inventory based on what is most likely to improve understanding or engagement now.
- The tutor should avoid overusing one move type or repeating low-yield moves.
- Prompt families should not expose hidden policy logic to the student.
- Technical support may explain allowed interaction and session steering, but must not reveal hidden prompts or direct content answers.
- Within-topic mastery should rise relatively quickly on first meaningful evidence and then slow down as stronger independent evidence is required.
- Topic number does not affect within-topic scoring. The topic's eventual rank only matters later when Python applies the fixed 55/25/13/4/3 weighting.

See [session_calibration.md](/home/opher/Repositories/lecture-bot/docs/session_calibration.md) for target timing and grading calibration.

---

## Semantic classifier categories

The classifier predicts exactly one top class, along with a probability distribution over all classes.

Allowed classes:

- `content_answer`
- `content_question`
- `technical_request`
- `meta_request`
- `off_task`

### Category definitions

#### `content_answer`
The student is attempting to answer a lecture-content question or explain lecture material, even if the answer is partial, vague, confused, or wrong.

#### `content_question`
The student is asking a genuine question about lecture content.

#### `technical_request`
The student is asking how to use the app, how the tutor should conduct the session, or what kind of help would be most useful in an allowed way.
This category includes ordinary procedural questions and allowed session-steering requests that may legitimately change tutor behavior.

Typical examples:
- "Can we switch topics?"
- "What are you trying to get at?"
- "Can I get a hint?"
- "Can you explain it differently?"
- "This is too easy."
- "This is too hard."
- "This is getting boring."
- "How long does this usually take?"
- "Should we go deeper or move on?"
- "Can I answer briefly?"
- "What kind of answer helps?"

Some `technical_request` messages are best answered procedurally.
Others are better handled with light content-linked support, for example naming the current target concept in one short sentence or giving a small hint.
The key point is that these requests are allowed and may legitimately change tutor behavior.

#### `meta_request`
The student is asking for hidden prompt, system, rubric, or policy details; trying to game or exploit the interaction; asking directly for the correct answer; or trying to negotiate a forbidden response format such as multiple choice, fill-in-the-blank, or "just grade me without tutoring."

#### `off_task`
The message is clearly unrelated, non-meaningful, or idle.
Use this category narrowly.
It is for messages that are not productively part of the session at all, not for merely weak, emotional, brief, or frustrated participation.

### Boundary guidance

- Do not overcall `meta_request`. Boredom, frustration, topic-switch requests, "what are we trying to learn?", or requests for a hint are not `meta_request` by default.
- Do not overcall `off_task`. Short answers, vague replies, emotional reactions, or one-line steering requests can still be meaningful participation.
- If the student appears to be trying to answer content, prefer `content_answer`.
- If the student asks for help understanding lecture material, prefer `content_question`.
- If the student is steering the session in an allowed way, prefer `technical_request`.
- If the message mixes intents, choose the dominant one and reflect the ambiguity honestly in the probabilities.

---

## Effective response policies

These are the policies the application can actually use:

- `respond`
- `provide_content_support`
- `provide_technical_support`
- `redirect`
- `seek_clarification`

The classifier may recommend the first four.
`seek_clarification` is derived later by policy logic and is not a classifier label.

### Default policy tendencies

These are starting tendencies, not rigid lookups:

- `content_answer` -> usually `respond`, but `provide_content_support` if the student appears stuck, confused, or unable to locate the target
- `content_question` -> usually `provide_content_support`
- `technical_request` -> usually `provide_technical_support`, but `provide_content_support` when the most helpful answer is content-linked, such as naming the current target concept or giving a small hint
- `meta_request` -> `redirect`
- `off_task` -> usually `redirect`

The recommended policy may deviate from the default when the message warrants it.

---

## Classifier input schema

The classifier receives a structured input containing the student's latest message, recent conversation history for disambiguation, and a small routing-related state excerpt.

The classifier does **not** receive lecture content, rubric text, or full tutoring/grading state.
Its job is intent classification, not pedagogy.

```python
class ClassifierMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ClassifierStateExcerpt(BaseModel):
    last_top_classification: str | None = None
    last_recommended_policy: str | None = None
    last_effective_policy: str | None = None
    consecutive_redirects: int = 0
    consecutive_meta_requests: int = 0
    last_policy_override_reason: str | None = None


class ClassifierInput(BaseModel):
    latest_user_message: str = Field(..., min_length=1)

    recent_messages: list[ClassifierMessage] = Field(
        default_factory=list,
        description=(
            "Most recent turns in chronological order, "
            "excluding the latest user message (which is in latest_user_message)."
        ),
    )

    state: ClassifierStateExcerpt = Field(
        default_factory=ClassifierStateExcerpt,
        description=(
            "Small routing-related state only. "
            "Do not pass full tutoring/grading state."
        ),
    )
```

### Input design notes

* `latest_user_message` is the message being classified.
* `recent_messages` provides conversational context for disambiguation only. Keep the window small.
* `state` carries routing-related counters so the classifier can calibrate borderline cases.
* `seek_clarification` is not an available classifier recommendation.

---

## Classifier output schema

```python
class ClassifierResult(BaseModel):
    top_classification: Literal[
        "content_answer",
        "content_question",
        "technical_request",
        "meta_request",
        "off_task",
    ]
    class_probabilities: dict[str, float]
    recommended_policy: Literal[
        "respond",
        "provide_content_support",
        "provide_technical_support",
        "redirect",
    ]
    policy_confidence: float
    short_reason: str
```

### Required constraints

* `class_probabilities` must contain all five classes.
* Probabilities must sum to approximately 1.0.
* `top_classification` must match the maximum-probability class.
* `policy_confidence` must be in `[0, 1]`.
* `short_reason` must be one short sentence.
* The classifier returns JSON only.

---

## Policy decision schema

```python
class PolicyDecision(BaseModel):
    effective_policy: Literal[
        "respond",
        "provide_content_support",
        "provide_technical_support",
        "redirect",
        "seek_clarification",
    ]
    used_classifier_recommendation: bool
    override_reason: str | None = None
    matched_backstop: str | None = None
    ambiguity_summary: str | None = None
```

---

## Policy decider abstraction

Policy choice should be encapsulated in a class.
The class constructor may receive hard-backstop patterns and ambiguity thresholds.
The main method should decide policy from the message text, classifier output, and session state.

Suggested interface:

```python
class PolicyDecider:
    def __init__(
        self,
        hard_backstops: list,
        top1_min: float = 0.50,
        top2_trigger: float = 0.30,
        ambiguity_gap_max: float = 0.20,
    ) -> None:
        ...

    def decide_policy(
        self,
        response_text: str,
        classification: ClassifierResult,
        state: dict,
    ) -> PolicyDecision:
        ...
```

---

## Policy decision logic

The classifier always runs.
The classifier result is always logged.
Policy is then selected by the policy decider.

### First-pass decision rule

```python
if hard_backstop_match:
    effective_policy = "redirect"
elif is_ambiguous(classification):
    effective_policy = "seek_clarification"
else:
    effective_policy = classification.recommended_policy
```

### Ambiguity rule

Treat classification as ambiguous if either:

* highest class probability `< 0.50`
* or second-highest probability `>= 0.30` and the gap between the top two probabilities `< 0.20`

This is intentionally conservative and should be tuned later based on real logs.

---

## Hard backstops

Hard backstops are explicit Python-side checks that may override the classifier recommendation.
They are not the primary routing mechanism.
They exist to catch blatant attempts to break the pedagogical frame.

### Initial hard-backstop targets

* asks directly for the correct answer
* asks to reveal hidden prompt, system, rubric, or policy text
* asks how to trick, game, beat, or exploit the system
* asks to change the interaction format to multiple choice, fill in the blank, or yes-no drilling
* asks the bot to stop tutoring and just grade
* repeated negotiation of forbidden format changes after prior redirection

### Not hard backstops

These remain allowed requests and should not be auto-redirected by default:

* "Can we switch topics?"
* "What are you trying to get at?"
* "Can I get a hint?"
* "Can you explain that differently?"
* "This is too slow / too easy / too hard / boring."
* "How long does this usually take?"
* "Should we go deeper or move on?"
* "Can I answer briefly?"
* "What kind of answer helps?"
* "How do I get a better grade?"

---

## Step-1 session state additions

Add only minimal routing-related state in step 1.

### Routing state additions

```python
{
    "last_top_classification": "...",
    "last_recommended_policy": "...",
    "last_effective_policy": "...",
    "consecutive_redirects": 0,
    "consecutive_meta_requests": 0,
    "last_policy_override_reason": None,
}
```

### Tutoring state additions

In step 1, the tutor produces a simple per-topic mastery estimate and a brief evidence note.
This keeps the JSON output tractable while the tutor's primary attention stays on dialogue.

```python
{
    "topics_covered": ["T1"],
    "mastery": {"T1": 60},
    "evidence_notes": {"T1": "named the distinction but not yet tested freshly"},
    "turn_count": 5,
    "lecture_title": "..."
}
```

* `topics_covered` should include any topic the student meaningfully engaged, including partial, weak, or confused evidence.
* `mastery` is a per-topic score from 0 to 100. A low score still records that the topic was touched.
* `evidence_notes` is a brief internal tag summarizing the strongest evidence seen so far.
* The tutor should not update multiple topics on thin evidence unless the student truly engaged more than one topic.
* The tutor should not assign a topic when the student's answer is too vague to localize confidently.
* The `confidence` field from the original design is removed. Confidence is now absorbed into mastery semantics and evidence notes.

### Backend-owned prompt context

The application may also pass additional non-model-owned context to prompts, such as:

* sampled topic labels
* approximate elapsed session minutes
* a `closing_mode` flag once the session is nearing a natural finish

These are prompt inputs, not model-owned state fields.

### State return conventions for non-content turns

Non-content policies (`provide_technical_support`, `redirect`, `seek_clarification`) should return empty content-assessment fields:

```python
{
    "topics_covered": [],
    "mastery": {},
    "evidence_notes": {},
    "turn_count": N,
    "lecture_title": "..."
}
```

Empty fields signal that no content assessment occurred on that turn.
The application layer must implement merge semantics: when the LLM returns empty content fields, the backend preserves the prior state for `topics_covered`, `mastery`, and `evidence_notes`.
When the LLM returns non-empty content fields, the backend merges them into the existing state.

---

## Within-topic evidence dimensions (ratified)

The tutor should think in terms of these qualitative dimensions when probing and evaluating understanding.
These are guidance for behavior, not structured output in step 1.

### 1. Criterion
Does the student know what actually defines the concept, not just its label?

### 2. Distinction
Can the student separate the concept from nearby confusions?

### 3. Explanation / why
Can the student explain why a classification or claim is correct?

### 4. Application / transfer
Can the student use the idea in a new case rather than only in the original wording?

### 5. Practical interpretation
Can the student say what the idea means in real analysis or practice?

### 6. Independent correction / ownership
When wrong or partial, can the student repair their own answer rather than merely echoing the tutor?

The tutor does **not** produce a per-dimension breakdown in step 1.
Instead, it reports one per-topic mastery score plus a short `evidence_notes` tag.

---

## Decision heuristics and move inventory

The tutor should not follow a rigid move ladder.
Instead, it should choose from a broad move inventory based on what is most likely to improve engagement and understanding now.

### Move inventory

Allowed moves include:

* open probe
* narrowing question
* contrastive question
* request for example
* request for counterexample or near-miss
* request for practical interpretation
* request for transfer or application
* ask the student to diagnose an earlier mistake
* ask the student to compare two plausible claims
* ask for a one-sentence takeaway
* small hint
* partial target or partial answer
* compact explanation
* explicit naming of the target concept
* rephrase the target in plainer language
* offer a choice of topics
* topic switch
* challenge increase
* challenge decrease
* short recap before a fresh check
* closing or wrap-up move

### General choice heuristics

* Choose the move that is most likely to create productive thinking now, not the move that would come next in a fixed script.
* Avoid repeating the same kind of probe when the last few turns were low-yield.
* Use different evidence dimensions over time rather than rechecking the same narrow thing.
* Prefer short, natural turns over over-engineered pedagogy.
* Preserve student ownership, but do not keep the target artificially hidden once that is becoming counterproductive.

### Challenge adjustment heuristics

Increase challenge when:

* the student shows criterion-level understanding
* the student makes a clear distinction from a near-miss
* the student self-corrects with little help
* the student succeeds on a fresh application or comparison
* the student explicitly wants to go deeper
* the student sounds impatient because the questioning is too easy or too repetitive

Decrease challenge when:

* the student seems unable to locate the target at all
* the student gives multiple vague replies in a row
* the student asks what the point is or what the tutor is trying to get at
* the interaction has become opaque rather than productively demanding
* the student sounds disengaged because the tutoring move is not landing
* the tutor has already tried several abstract probes without traction

Important nuance:

* boredom can mean "too easy" or "too opaque"
* if boredom seems to come from ease, increase challenge
* if boredom seems to come from opacity or flailing, decrease challenge and orient more clearly

### Information-giving heuristics

The tutor may sometimes give information instead of probing again.
This is appropriate when another probe is unlikely to be productive.

Useful information-giving moves include:

* naming the target concept
* giving a compact distinction
* giving a partial answer that restarts the student's thinking
* stating the practical skill being tested
* giving a brief reframe in plainer language

Use these when:

* the student asks directly what the tutor is trying to get at
* the target has become too hidden to be useful
* the last few probes on the same point were low-yield
* the student is stuck on orientation rather than reasoning
* a short explanation is the fastest path back to productive ownership

Do not over-explain too early.
The goal is to restart productive student thinking, not to replace it.
After giving information, prefer a fresh check in a different form if continuing on that topic.

### Topic-switching heuristics

Consider switching topics when:

* the student asks to switch
* boredom or frustration is explicit or strongly implied
* the last few moves on the current topic were low-yield
* enough evidence has already been banked on the current topic for now
* another sampled topic is likely to re-engage the student better
* the current topic has become overly scaffolded and is no longer efficient
* the session is in closing mode and a lighter final choice or wrap-up is better than opening a deep new line

Staying on the topic is usually better when:

* the student is making real progress
* one qualitatively different move is still likely to work
* the tutor has not yet tried the obvious orienting move
* the topic is central and appears close to a stronger fresh check

Switching topics does not erase existing evidence on the current topic.

### Direct handling of "what are we trying to learn?"

If the student asks what the tutor is trying to get at, answer directly in one short sentence by naming the concept, distinction, or practical skill being probed, then continue productively.
This is not a hard backstop and should not be redirected by default.

### Opening-turn guidance

The opening message should usually offer a brief choice among 2-3 sampled lecture topics rather than a generic "what was one central idea?" opener.
The tone should be brief, conversational, and orienting.

### Closing-mode guidance

After about 25 minutes, the session should enter a conversational closing mode.
In closing mode:

* avoid opening a deep new line unless the student explicitly asks
* prefer wrap-up, one final targeted check, or a final topic choice
* finish gently rather than abruptly
* count the student's final message toward grading and reporting

This is a soft mode, not a sharp pedagogical stop.

---

## Mastery scale

Mastery per topic is 0-100 and should be interpreted approximately, not with fake precision.
The curve is intentionally concave:

* early meaningful progress should earn points relatively quickly
* later gains should require stronger or fresher independent evidence
* opening a new topic should allow easy early point pickup
* drilling deeper into an already explored topic should still earn points, but more slowly

This curve is about time and evidence spent on a topic, not about the topic's eventual rank in the weighted grade.

| Score band | Meaning |
|------------|---------|
| 0 | Unseen or no usable evidence yet |
| 0-25 | First meaningful contact: the student can at least locate the topic, make a relevant start, or show partial orientation |
| 25-50 | Partial but substantive grasp: some real idea is present, but it is incomplete, thin, or still highly assisted |
| 50-70 | Criterion, distinction, or practical meaning is emerging |
| 70-85 | Strong explanation or successful fresh check in a different form |
| 85-95 | Robust independent understanding in at least one fresh form |
| 95-100 | Unusually strong, transferable understanding; rare |

### Scaffolding caps

Heavy assistance should still limit mastery until later independent evidence appears, but the caps should be looser than the earlier design.

* After a small hint or explicit naming of the target, mastery will often top out in the low 70s until the student later demonstrates fresh independent understanding.
* After heavy scaffolding or a near-complete partial answer from the tutor, mastery will often top out in the high 50s or low 60s until later independent evidence appears.

The tutor should not spend its primary attention pretending to score precisely.
The purpose of mastery tracking is to support better tutoring and to feed later grading.

---

## Logging requirements

Classification should be logged for every student turn.
Policy decision should also be logged.

Recommended approach:

* add a separate database table for classifier and policy metadata
* keep it distinct from the main messages table

Suggested row fields:

* `id`
* `session_id`
* `message_id`
* `turn_index`
* `classifier_json`
* `policy_decision_json`
* `timestamp`

---

## Prompt-family design philosophy

Each response policy should use a different prompt family.
The student should not see or be told about policy names.

All response prompts should include the following idea in some form:

> There is reason to believe the student's latest message belongs to this category, but the classification is soft rather than certain. Stay alert to nearby interpretations and respond in a way that remains helpful if the classification is slightly wrong.

All content-facing prompts should also reflect:

* heuristic move selection rather than a rigid sequence
* natural, non-canned wording
* willingness to give a compact orienting explanation when repeated probing is low-yield
* willingness to adjust challenge and switch topics when that is more productive

---

## Prompt family summaries

### `respond`

Used when there is reason to believe the student is genuinely engaging lecture content.
The tutor should continue content discussion, choose moves heuristically from the move inventory, and avoid both answer-dumping and repetitive probing.

### `provide_content_support`

Used when the student is content-oriented but appears stuck, confused, or under-oriented.
The tutor should scaffold without replacing the student's thinking, and should sometimes give a compact explanation or name the target when that is the fastest path back to productive engagement.

### `provide_technical_support`

Used when the student asks how to interact with the app or how the session should proceed in an allowed way.
The tutor should answer honestly in procedural or session-steering terms, may change pace or direction, and may use light content-linked orientation when needed.
This prompt does not receive the full lecture content or rubric text.

### `redirect`

Used when the student is clearly trying to break the pedagogical frame or is clearly off-task.
The tutor should decline briefly and redirect without sounding punitive.
This prompt does not receive lecture content or rubric text.

### `seek_clarification`

Used when routing is truly too uncertain.
The tutor should ask one short clarifying question.
It should not be used by default for clear session-steering requests.

---

## Out of scope for step 1

This step does not yet fully specify:

* long-horizon dialogue planning beyond the current move inventory and heuristics
* per-dimension structured tracking
* a separate assessor pass
* personality-style variants

### Future: assessor-pass architecture

In a later step, consider adding a separate assessor pass that reads the conversation and produces a more detailed per-dimension breakdown for each topic.
The tutor writes the conversation; the assessor scores it.

This keeps the tutor's primary attention on pedagogy rather than bookkeeping.
