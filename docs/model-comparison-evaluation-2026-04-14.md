# Model Comparison Evaluation

## Scope

This note compares three exported sessions:

1. `session_123b2ad2_lecture_02_gpt-4.1-mini_2026-04-13-172804.md`
2. `session_8389a8ee_lecture_01_gpt-5.4_2026-04-13-201112.md`
3. `session_be93b570_lecture_02_gpt-5.4-mini_2026-04-13-204439.md`

The comparison is based primarily on the transcripts. I also checked the stored classifier/policy logs plus the current prompt and control files that shape routing and response generation.

One important limitation remains: the app does not persist the fully rendered tutor prompt or a per-turn state snapshot. So for these sessions we can recover:

- the classifier output
- the recommended policy
- the effective policy
- the prompt family implied by that policy

but not the exact full prompt string that was sent to the dialogue model on each turn.

## High-Level Summary

- `gpt-4.1-mini` produced the weakest session. It was the most repetitive, the least perceptive about mastery, and the most likely to keep drilling after the student had already shown understanding.
- `gpt-5.4` improved local conversational judgment. It was better at brief clarification, acknowledging nuances, and repairing small mistakes. But it did not solve the core pedagogical flatness problem.
- `gpt-5.4-mini` produced the strongest overall score and better topic coverage than the earlier runs, but it still showed severe procedural looping, low-ceiling drilling, and some odd or confusing content moves.

The main conclusion is that model choice matters, but it is not the dominant remaining bottleneck. The biggest persistent failures still look structural: weak session-steering policy, insufficient anti-repetition memory, poor difficulty escalation, and inadequate protection against wasting time on already-mastered material.

## What We Can Reconstruct Reliably

From the database and the current code path in [bot_engine.py](/home/opher/Repositories/lecture-bot/app/bot_engine.py:401), we can reconstruct:

- the classifier JSON for each turn
- the policy decision JSON for each turn
- the effective policy used to choose the tutor prompt family

The prompt family mapping is defined in [bot_engine.py](/home/opher/Repositories/lecture-bot/app/bot_engine.py:41):

- `respond` -> `respond_prompt.md`
- `provide_content_support` -> `provide_content_support_prompt.md`
- `provide_technical_support` -> `provide_technical_support_prompt.md`
- `redirect` -> `redirect_prompt.md`
- `seek_clarification` -> `clarification_prompt.md`

What we cannot reconstruct exactly from storage alone:

- the exact rendered prompt text for a given turn
- the exact state snapshot used to render that prompt
- the exact dialogue model if the app default changed over time and was not separately persisted

## Routing Evidence From The Sessions

### `gpt-4.1-mini` session

Some of the relevant routing was reasonable:

- turn `8` (`"Nope. Is there something here you are worried I don't understand? Anything missing?"`) was classified as `technical_request` and routed to `provide_technical_support`
- turn `10` (`"Let's just keep it moving. Go ahead and ask something."`) was also classified as `technical_request` and routed to `provide_technical_support`

That matters because the weak behavior in those regions cannot be blamed on a missed technical-support route alone. The model still chose low-value next moves inside the technically correct prompt family.

### `gpt-5.4` session

The main weakness late in the session was not obviously a routing failure either:

- turn `21` (`"Don't you have any hard questions?"`) was classified as `technical_request` and routed to `provide_technical_support`
- turn `23` (`"I'm fine with moving on."`) was also classified as `technical_request` and routed to `provide_technical_support`

So the system did notice the student's request for harder questions and for moving on. The fact that the tutor still spent too long on low-yield event/outcome distinctions points to limitations in prompt behavior, state quality, or dialogue-model judgment within that route.

### `gpt-5.4-mini` session

The early Bayes-rule loop is especially revealing:

- turns `1` through `10` were repeatedly classified as `technical_request` and routed to `provide_technical_support`
- examples include `"Are there other topics we could try?"`, `"Why did we skip it?"`, `"Go go go"`, and the sarcastic loop-complaint

This shows that the system was broadly recognizing the session-steering nature of the exchange. The failure was not primarily that the classifier missed the signal. The failure was that technical-support mode kept narrating the next move instead of decisively taking it.

## Session-by-Session Findings

### 1. `gpt-4.1-mini` session

This session had both content-handling failures and tutoring-judgment failures.

What went wrong:

- The tutor made an outright contradictory evaluation on the Beta update check. The student answered `6 and 9`, and the tutor said that was right while also stating the posterior was `Beta(6, 5)`. That is a basic trust-breaking error.
- The tutor repeatedly failed to recognize mastery in pseudo-count updating. After the student gave a strong explanation, the tutor kept looking for more confirmation instead of moving on.
- The tutor asked for a fresh example, then pivoted away to a topic-switch menu, then came back with another easy update question. That sequence felt indecisive and incoherent rather than adaptive.
- The tutor got stuck re-asking the same sampling-vs-grid point multiple times after the student had already given the key idea.

Representative examples:

- `200` to `202`: correct student answer, incorrect tutor follow-up.
- `207` to `214`: mastery is shown, but the tutor still behaves as though competence is uncertain.
- `233` to `240`: the student says the key idea, the tutor keeps demanding a slightly different restatement.

Takeaway:

This run shows the baseline failure pattern very clearly: weak local reliability, weak mastery detection, weak topic-allocation judgment, and high repetition.

### 2. `gpt-5.4` session

This session is better than the `gpt-4.1-mini` run, but only in limited ways.

What improved:

- The tutor was better at light clarification. For example, it responded to the student's density nuance and gave a compact correction that was locally useful.
- It was somewhat better at acknowledging its own mistake when the event/outcome wording became inconsistent.
- It moved across more topics than the `gpt-4.1-mini` run, which at least partially reduced the "one topic all session" problem.

What still went wrong:

- The tutor still spent too much time on low-ceiling, quiz-like prompts.
- It still failed to escalate difficulty even after the student explicitly asked for harder questions.
- It still wasted time on repetition, especially on the event/outcome distinction.
- It introduced inconsistency on its own by first framing singletons as outcomes in context, then later insisting `{3}` should be treated as an event in the harder check.
- The session had a non-model bug: the stored grade was `82.0`, but the closing message announced `80 / 100`.

Representative examples:

- `252` to `256`: reasonably good local clarification and transition.
- `276` to `290`: repeated time sink on event/outcome distinctions, ending in tutor-created inconsistency.
- `285` to `292`: even after the student asks for harder questions, the tutor takes too long to move to something genuinely more useful.

Takeaway:

`gpt-5.4` improved local fluency and repair, but not enough to fix the main system problem. The interaction still often felt like a cautious quiz generator rather than a strong adaptive tutor.

### 3. `gpt-5.4-mini` session

This session had the strongest final outcome but still exposed serious non-model weaknesses.

What improved:

- The tutor eventually covered a useful set of topics and reached a much stronger overall session outcome.
- Once the conversation entered normal content mode, the flow was generally more efficient than the `gpt-4.1-mini` session.
- The opening message content was cleaner and more readable in storage.

What still went wrong:

- The early session got trapped in an extended meta loop. The tutor kept paraphrasing "use Bayes rule as the bridge into priors and Beta distributions" instead of simply asking a question.
- The tutor still used several low-value, low-ceiling follow-up drills after correct answers.
- It introduced a pseudo-count convention shift by `1` that may be mathematically defensible in some framings, but was risky and likely mismatched to the class framing the student was using.
- It produced at least one strange corrupted output fragment in the `Beta(1,1)` explanation.
- It introduced jargon the student explicitly said was not in the materials (`unnormalized posterior`, `posterior kernel`) and then spent time checking that jargon rather than the concept itself.

Representative examples:

- `301` to `319`: long procedural loop instead of decisive forward motion.
- `339` to `349`: content becomes fussy, convention-heavy, and arguably less pedagogically aligned than the student's simpler framing.
- `355` to `359`: time spent on terminology that does not appear to be central to the lecture materials.

Takeaway:

`gpt-5.4-mini` can produce a better overall session than both earlier models, but it still exposes the same underlying system weaknesses. The meta-loop is especially important because it is not a mere style issue; it burns large chunks of the session clock.

## What Model Changes Do Fix

These improvements appear to be at least partly model-sensitive:

- Better directness in local clarification.
  `gpt-5.4` and `gpt-5.4-mini` are generally better than `gpt-4.1-mini` at answering "what do you mean?" or lightly reframing a concept without totally falling apart.

- Better local repair after small misunderstandings.
  The larger models are somewhat better at acknowledging a nuance, correcting one point, and moving on.

- Better surface fluency and transitions.
  The stronger models sound less clumsy turn to turn, even when they are still making weak pedagogical choices.

- Better chance of ending with broader coverage.
  The `gpt-5.4-mini` run in particular covered Bayes rule, priors/Beta distributions, grid construction, normalization, and sampling limits in one session. That is meaningfully better than the `gpt-4.1-mini` run.

## What Model Changes Do Not Fix Well

These failures persisted across model changes and should be treated as system-level issues until proven otherwise:

- Repetition after demonstrated understanding.
  All three sessions contain clear examples of the tutor asking another near-duplicate question after the student already showed the relevant idea.

- Failure to allocate time strategically across topics.
  The tutor still tends to squeeze one concept for too long before moving on, even when breadth would be higher value.

- Weak difficulty escalation.
  Even when the student asks for harder or more valuable questions, the tutor often responds with another basic check.

- Meta steering loops.
  The `gpt-5.4-mini` session shows that a stronger model can still get trapped in a prompt/state/policy loop where it keeps narrating the next move instead of taking it.

- Content-policy mismatch with the actual course framing.
  The tutor still risks bringing in conventions or terminology that may be mathematically acceptable but are not aligned with the class materials.

- Inconsistent behavior created by the system rather than by the student.
  The `gpt-5.4` event/outcome sequence and the grade mismatch are examples of failures that should not be blamed on model size.

## Is There A Reason To Prefer `gpt-5.4` Over `gpt-5.4-mini`?

There is a reason, but it is not overwhelming.

Reasons to prefer `gpt-5.4`:

- It appears somewhat more stable in local conceptual repair.
- It is less likely to sound obviously lightweight when giving a clarification.
- It may be less prone than `gpt-5.4-mini` to bizarre procedural echoing, though the evidence here is limited.

Reasons not to prefer it as the default right now:

- It is significantly slower.
- The dominant remaining failures are not fixed by moving from `gpt-5.4-mini` to `gpt-5.4`.
- The `gpt-5.4-mini` run produced the strongest overall session outcome among these three.
- The worst remaining problems look like policy/state/prompt problems, so paying a large latency cost now is likely low leverage.

Recommendation:

- Use `gpt-5.4-mini` as the current working default for iteration.
- Keep `gpt-5.4` as a benchmark model for spot checks and regression comparisons.
- Revisit the larger model only after the non-model optimizations below are in place.

## What Still Needs Optimization Other Than Changing Models

### 1. Stronger anti-loop and anti-parroting behavior

The system needs a hard bias toward taking the next step once it has narrated the next step once. The `301` to `319` loop in the `gpt-5.4-mini` session should be prevented even if the model is confused by the student's sarcasm.

### 2. Stronger mastery recognition

When the student demonstrates the target concept, the tutor should either:

- raise difficulty
- ask for transfer/application
- switch to a fresh topic

It should not ask another structurally identical check.

### 3. Better breadth policy

The tutor should spend less time grinding one subtopic after workable evidence has been collected. This is especially important because the session clock is short and the grading setup rewards coverage enough that wasted turns are expensive.

### 4. Better difficulty escalation

The system needs an explicit notion of `easy check`, `medium check`, and `high-value discriminating question`, and it needs to shift upward when the student asks for harder or more useful questions.

### 5. Better alignment to lecture materials

The tutor should be less willing to introduce terminology or conventions that are not clearly part of the course framing. That includes both jargon and alternate mathematical conventions that may distract from the taught story.

### 6. Better observability

The current logs are good enough to recover classifier output and effective policy, but still not good enough for full prompt-level diagnosis. For stronger model comparisons, the system should also persist:

- prompt family used explicitly, not just infer it later
- dialogue model used
- rendered state synopsis or a compact per-turn state snapshot
- ideally the exact rendered system prompt for the tutor turn

Without that, it is still too easy to blur together prompt, state, and model failures.

## Bottom Line

The model swap helped, but not enough to justify treating model choice as the main lever.

- `gpt-4.1-mini` is clearly too weak for this tutoring style.
- `gpt-5.4` is better locally, but not enough better to justify its latency cost as the default.
- `gpt-5.4-mini` currently looks like the best iteration model because it is faster and can still produce a strong overall session, but it needs structural help.

The next serious gains are more likely to come from fixing:

1. anti-loop behavior
2. mastery detection
3. breadth-aware pacing
4. difficulty escalation
5. observability

than from moving further up the model ladder.
