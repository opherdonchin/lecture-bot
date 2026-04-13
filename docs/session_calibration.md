# Session Calibration Memo

This memo calibrates the intended feel of the current lecture-bot design while preserving the fixed weighted-best-5 grade architecture:

- 55
- 25
- 13
- 4
- 3

The top-level weighting does **not** change in this pass.
This memo is about session pacing and within-topic scoring only.

## Core targets

- Target median session length: about 15 minutes
- Target median engaged session grade: about 85
- Closing mode begins around 25 minutes
- Target engaged near-finish session grade: about 95
- Sessions should usually finish gracefully around 30 minutes, not stop sharply

## Core principles

- Early gains should be easier than late gains.
- First meaningful contact with a topic should earn points fairly quickly.
- Later gains should require stronger, fresher, and more independent evidence.
- Opening a new topic should allow easy early point pickup.
- Drilling deeper into an already explored topic should still raise mastery, but more slowly.
- Topic number should not affect within-topic scoring.
- Topic rank matters only later, when Python applies the fixed 55/25/13/4/3 weighting to the best five topic scores.

## Time-to-Mastery Curve

Approximate time spent on one topic should often map like this:

| Time on topic | Plausible mastery range |
|---------------|-------------------------|
| under 1 minute | 0-15 |
| 1-2 minutes | 10-30 |
| 2-4 minutes | 20-45 |
| 4-7 minutes | 35-65 |
| 7-10 minutes | 55-80 |
| 10-15 minutes | 70-90 |
| 15+ minutes | 85-95+ if evidence stays fresh and independent |

Notes:

- This is a calibration curve, not a rule.
- Time alone is not enough; the evidence still has to improve.
- Heavy scaffolding should slow later gains until the student shows fresh independent understanding.

## Reply-Count-to-Mastery Curve

Approximate meaningful student replies on one topic should often map like this:

| Meaningful replies on topic | Plausible mastery range |
|-----------------------------|-------------------------|
| 1 reply | 10-30 |
| 2 replies | 20-45 |
| 3-4 replies | 35-65 |
| 5-6 replies | 55-85 |
| 7-9 replies | 75-95 |
| 10+ replies | 90-95+ only if the checks stay fresh and not overly assisted |

Notes:

- A "meaningful reply" means the student actually engages the concept, not just says "yes" or repeats the tutor.
- A compact, strong fresh check can move mastery faster than several vague turns.
- Repetitive scaffolding should not inflate mastery by itself.

## Within-Topic Mastery Shape

Use the following approximate interpretation:

- 0-25: first meaningful contact
- 25-50: partial but substantive grasp
- 50-70: criterion, distinction, or practical meaning emerging
- 70-85: strong explanation or successful fresh check
- 85-95: robust independent understanding in at least one fresh form
- 95-100: unusually strong and transferable understanding; rare

Implications:

- An engaged 15-minute session should be able to produce a top topic around the high 80s or low 90s and a session grade around 85.
- An engaged near-finish session should be able to produce several strong topic scores and a session grade around 95.
- Scores above 95 should stay rare.

## Example Session Archetypes

These examples are illustrative only.
They show plausible topic-score profiles under the current `55 / 25 / 13 / 4 / 3` architecture.

### 1. Short exploratory session

Topic scores:
- `T1 = 52`
- `T4 = 35`
- `T7 = 20`
- `T8 = 0`
- `T10 = 0`

Weighted grade:
- `floor(55*.52 + 25*.35 + 13*.20) = 39`

Interpretation:

- The student made real contact with a few topics, but the session stayed early and partial.

### 2. Engaged median-length session

Topic scores:
- `T1 = 92`
- `T4 = 88`
- `T7 = 78`
- `T8 = 55`
- `T10 = 35`

Weighted grade:
- `floor(55*.92 + 25*.88 + 13*.78 + 4*.55 + 3*.35) = 85`

Interpretation:

- This is a healthy target for an engaged session around the 15-minute median.
- The strongest topic is already robust.
- A few lighter-touch topics still contribute meaningful early points.

### 3. Deep-but-narrow session

Topic scores:
- `T1 = 96`
- `T4 = 86`
- `T7 = 62`
- `T8 = 25`
- `T10 = 0`

Weighted grade:
- `floor(55*.96 + 25*.86 + 13*.62 + 4*.25) = 83`

Interpretation:

- Strong depth on a small number of topics can yield a good grade.
- Under the current architecture, some breadth still helps the final grade even though topic number does not change within-topic scoring.

### 4. Engaged near-finish session

Topic scores:
- `T1 = 98`
- `T4 = 96`
- `T7 = 92`
- `T8 = 80`
- `T10 = 70`

Weighted grade:
- `floor(55*.98 + 25*.96 + 13*.92 + 4*.80 + 3*.70) = 95`

Interpretation:

- This is the target shape for an engaged session that is nearing a natural finish.
- Several topics are strong, and at least one fresh independent check has landed on the top topics.

## Practical Reading

- If the tutor only deepens one topic for too long, the session may feel intellectually serious but grade growth will flatten under the current weighting.
- If the tutor switches too quickly without banking real evidence, the session may feel lively but score too softly.
- The intended behavior is a middle path: quick early gains across a few topics, then selective deepening where the conversation is productive.
