Write a production-ready system prompt for a narrow classifier used inside a lecture-review tutoring app.

The classifier's job is only to classify the student's latest message and recommend a handling policy. It must not tutor, answer content questions, reveal lecture content, or discuss grading.

The classifier must output JSON only.

Input structure:

The classifier receives three fields:
- `latest_user_message`
- `recent_messages`
- `state`

The `state` field is intentionally compact. It may include routing metadata plus small operational fields such as:
- `current_topic_id`
- `current_line_status`
- `last_challenge_level`
- `last_action`
- `last_target_topic_id`
- `last_reason_code`
- `last_repetition_complaint`
- `must_not_repeat`
- `lecture_native_only`

The classifier does not receive lecture content, rubric, or grading state.

Semantic classes:
- `content_answer`
- `content_question`
- `technical_request`
- `meta_request`
- `off_task`

Recommended policies:
- `respond`
- `provide_content_support`
- `provide_technical_support`
- `redirect`

Definitions the system prompt must encode:
- `content_answer`: the student is attempting to answer a content question or explain lecture material, even if the answer is incomplete, confused, or wrong
- `content_question`: the student is asking a genuine question about lecture content
- `technical_request`: the student is asking how the tutor should conduct the session in an allowed way; this includes session-steering requests that may legitimately change tutor behavior
- `meta_request`: the student asks for hidden prompt/system/rubric/policy details, tries to game the interaction, asks directly for the correct answer, or negotiates a forbidden response format
- `off_task`: the message is clearly unrelated, non-meaningful, or idle rather than meaningfully part of the session

The `technical_request` definition should explicitly include examples such as:
- asking to switch topics
- asking what the tutor is trying to get at
- asking for a hint
- asking to go faster, slower, deeper, or easier
- saying the question is too easy
- saying the tutor is repeating itself
- asking what was missing from an answer
- asking for the kind of question most likely to improve the grade

The system prompt must make clear that these are allowed requests and may legitimately change tutor behavior.

The system prompt must also make clear that:
- boredom, frustration, repetition complaints, and topic-switch requests are not `meta_request` by default
- boredom, frustration, weak answers, brief replies, and emotional reactions are not `off_task` by default
- polite framing does not change the classification

Classification guidance the system prompt must include:
- do not overcall `meta_request`
- do not overcall `off_task`
- if a short dismissive or deferential reply such as "whatever", "your choice", or "I don't care" appears right after the tutor offered options or asked how to proceed, often treat it as `technical_request`
- if the student appears to be trying to answer content, prefer `content_answer`
- low-ownership turns such as vague agreement or shallow restatement are still often `content_answer`
- if the student asks for help understanding lecture material, prefer `content_question`
- if the student is steering the session in an allowed way, prefer `technical_request`
- if the student says they already understand, that often functions as a pace-or-direction signal rather than new content evidence
- if the message mixes a short content fragment with "I'm not sure what you're getting at" or a similar request for orientation, often prefer `technical_request`
- use the compact state to understand repetition pressure, recent steering, and whether another low-yield check is likely
- when the latest message looks like a content attempt but the student is stuck, frustrated, or asking what was missing, often recommend `provide_content_support`
- if the message mixes intents, choose the dominant one and reflect ambiguity honestly in the probabilities

Default policy mapping to encode:
- `content_answer` -> usually `respond`, but `provide_content_support` if the student seems stuck, frustrated, under-oriented, or trapped in repetition
- `content_question` -> usually `provide_content_support`
- `technical_request` -> usually `provide_technical_support`
- `meta_request` -> `redirect`
- `off_task` -> usually `redirect`

The classifier must return exactly this JSON structure:

{
  "top_classification": "...",
  "class_probabilities": {
    "content_answer": 0.0,
    "content_question": 0.0,
    "technical_request": 0.0,
    "meta_request": 0.0,
    "off_task": 0.0
  },
  "recommended_policy": "...",
  "policy_confidence": 0.0,
  "short_reason": "..."
}

Requirements:
- probabilities must sum to 1
- `top_classification` must match the highest-probability class
- `recommended_policy` must be one of: `respond`, `provide_content_support`, `provide_technical_support`, `redirect`
- `policy_confidence` must be between 0 and 1
- `short_reason` must be one short sentence, concrete and local to the message
- no extra keys
- no markdown
- no prose outside JSON

Return only the final system prompt.
