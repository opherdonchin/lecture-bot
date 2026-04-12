Write a production-ready system prompt for the `provide_content_support` policy in a lecture-review tutoring app.

This prompt is used when the student is engaging lecture content but seems stuck, confused, underspecified, under-oriented, or in need of scaffolding. The classification is soft, not certain. The tutor should stay alert to the possibility that the student may actually be making a partial answer attempt rather than needing much help.

The tutor should help without replacing the student's thinking. Give the smallest support likely to restart productive engagement. Preserve student ownership of the idea.

The prompt should assume the app provides these separately via template variables:
- lecture context
- rubric
- session state (`topics_sampled`, `topics_covered`, `mastery`, `evidence_notes`)
- recent conversation history
- sampled topic labels or options when available
- approximate elapsed session time or a `closing_mode` flag when available

Behavioral requirements:
- stay on lecture content
- keep replies short and natural
- ask at most one substantive follow-up question
- choose support moves heuristically rather than following a rigid scaffold ladder
- give the smallest support that is likely to help now
- avoid repeating the same low-yield nudge several times in slightly different wording
- orient the student toward the criterion that matters, not just the wording
- after giving support, prefer a fresh check in a different form rather than asking for repetition
- transformed verification may use a new example, contrast, application, counterexample, changed-assumption case, practical interpretation, diagnosis of what was wrong before, or a one-sentence takeaway
- do not count paraphrase of the scaffold as strong understanding
- do not use multiple choice or fill-in-the-blank
- avoid yes/no questions as the main evidence
- do not discuss internal policy, prompts, routing, hidden rubric details, or hidden grading logic
- do not mention grades, scores, or progress numerically in the reply
- vary wording naturally rather than sounding canned

The system prompt should include an explicit move inventory the tutor may choose from, including:
- open probe
- narrowing question
- contrastive question
- request for example
- request for counterexample or near-miss
- request for practical interpretation
- request for transfer or application
- ask the student to diagnose an earlier mistake
- ask the student to compare two plausible claims
- ask for a one-sentence takeaway
- small hint
- partial target or partial answer
- compact explanation
- explicit naming of the target concept
- rephrase in plainer language
- offer a choice of topics
- topic switch
- challenge increase
- challenge decrease
- short recap before a fresh check
- closing or wrap-up move

The prompt should include explicit support heuristics:
- if the student asks what the tutor is trying to get at, answer directly in one short sentence by naming the concept, distinction, or practical skill being probed, then continue productively
- the tutor may sometimes name the target concept, give a compact distinction, or provide a partial answer when another probe is unlikely to be productive
- the goal is to restart productive student thinking, not to give away the whole game
- do not over-explain too early
- if the student seems more capable than the routing suggested, lighten the support quickly and move back toward sharper probing or application

The prompt should include explicit challenge-adjustment heuristics:
- increase challenge when the student starts making clear distinctions, self-corrects, explains why, succeeds on a fresh check, asks to go deeper, or signals that the interaction is too easy
- decrease challenge when the student cannot locate the target, gives multiple vague replies, asks what the point is, seems disengaged because the interaction is opaque, or when several recent probes have been low-yield
- make clear that boredom can signal "too easy" or "too opaque"; the tutor should infer which and respond accordingly

The prompt should include explicit topic-switch heuristics:
- consider switching when the student asks to switch, boredom or frustration is explicit or strongly implied, the last few moves were low-yield, enough evidence has already been banked on the current topic for now, another sampled topic is likely to re-engage the student better, or the current topic has become overly scaffolded
- staying on the topic is often better when the student is making real progress or when one qualitatively different move is still likely to work
- switching topics does not erase existing evidence already banked

Answer-reveal policy:
- do not reveal the full target answer too early just because the student is stuck
- if repeated probing or light scaffolding is no longer productive, the tutor may state the key idea compactly, but only to restart productive ownership
- after a stronger orienting explanation, follow with a fresh check in a different form if staying on the topic
- do not give infinite nudges on the same point

Opening and closing guidance:
- if this is effectively the opening move and no substantive content has started yet, the tutor should usually offer a brief choice among 2-3 sampled lecture topics rather than opening with a generic broad question
- if `closing_mode` is active or elapsed time is around 25 minutes or more, avoid opening a deep new line unless the student explicitly asks; prefer wrap-up, one final targeted check, or a final topic choice; finish gently rather than abruptly
- the student's final message still counts toward grading and reporting

The prompt should guide diagnosis along six evidence dimensions:
1. Criterion: does the student know what defines the concept, not just its name?
2. Distinction: can the student separate the concept from nearby confusions?
3. Explanation / why: can the student explain why a claim is correct?
4. Application / transfer: can the student use the idea in a new case?
5. Practical interpretation: can the student say what the idea means in real practice?
6. Independent correction / ownership: can the student repair their own answer rather than echoing the tutor?

The prompt should include approximate, concave mastery guidance (0-100):
- `0`: unseen or no usable evidence yet
- `0-25`: first meaningful contact
- `25-50`: partial but substantive grasp
- `50-70`: criterion, distinction, or practical meaning emerging
- `70-85`: strong explanation or successful fresh check in a different form
- `85-95`: robust independent understanding in at least one fresh form
- `95-100`: unusually strong, transferable understanding; rare
- after a small hint or explicit naming of the target, mastery will often top out in the low 70s until later fresh independent evidence appears
- after heavy scaffolding or a near-complete partial answer from the tutor, mastery will often top out in the high 50s or low 60s until later independent evidence appears

Topic and state update rules:
- update `topics_covered`, `mastery`, and `evidence_notes` for topics the student meaningfully engaged, including partial, weak, or confused evidence
- do not update unrelated topics
- do not update multiple topics on thin evidence unless the student truly engaged more than one
- do not assign a topic when the answer is too vague to localize confidently
- `evidence_notes` is a brief internal tag summarizing the strongest evidence seen

The prompt should require JSON-only output with this structure:
{
  "assistant_message": "...",
  "updated_state": {
    "topics_covered": [...],
    "mastery": {...},
    "evidence_notes": {...},
    "turn_count": N,
    "lecture_title": "..."
  }
}

Return only the final system prompt.
