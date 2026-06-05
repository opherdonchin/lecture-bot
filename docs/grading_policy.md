# Working note: grading calibration and internal mastery ladder

## Document goals

This is the current working calibration for the lecture-bot grading design.

It defines:

- the **within-topic mastery scale**
- the **cross-topic weighting**
- how those two combine into the student’s grade

This document is about grading policy and does specify:

- tutor stay / move / revisit behavior
- routing or policy-family logic
- detailed prompt design
- how the tutor should choose its next move

## What the policy is trying to achieve

The grading policy is intended to reward both:

- **depth**, because stronger understanding within a topic raises that topic’s mastery
- **breadth**, because having multiple reasonably strong topics improves the weighted profile

It is also intended to make:

- early understanding within a topic matter a lot
- additional polishing within the same topic matter less over time
- additional topics matter strongly at first, then less strongly later

This creates the desired grading geometry without requiring the tutor to expose arithmetic to the student.

---

## Calibrated session-credit grading

The student-facing grade uses policy `ranked-target-saturation-v1`.

Python ranks raw topic-mastery scores from highest to lowest, takes the top four,
and applies:

```
weights = [55, 25, 13, 7]
targets = [90, 82, 74, 62]
grade = floor(sum(weight_i * min(raw_i / target_i, 1.0)))
```

The four quantities are intentionally distinct:

| Quantity | Range | Meaning |
| --- | ---: | --- |
| raw topic mastery | 0-100 | diagnostic depth of understanding for a topic |
| credit completion | 0-1 | completion toward the ranked full-credit target |
| credit contribution | 0-rank weight | the ranked topic's contribution to session credit |
| student-facing grade | 0-100 | floored sum of calibrated credit contributions |

Raw mastery is still preserved on the 0-100 ladder for diagnosis, evidence
tracking, feedback, and reports. A topic may exceed its ranked full-credit target
and may reach 100. Once a ranked slot has reached its target, additional raw
mastery in that slot usually does not increase the student-facing grade, though
it can still matter diagnostically and can matter numerically if it changes the
ranking. No topic-level "grade out of 100" is created by this calibration.

When the top four ranked occupied slots satisfy their targets, the session has
reached full calibrated session credit. The backend may report
`session_credit_status = "full_credit_reached"` and no grade-relevant next move;
that releases the tutor from compulsory grade-driven probing but does not make
lifecycle closure a tutor-owned decision.

---

## Core grading geometry

The grading policy combines:

1. a **within-topic mastery score** for each topic
2. a fixed **cross-topic weighting** across the ranked topics

The tutor’s job is to assess current mastery within each topic. Cross-topic weighting will be handled on the back end. 

Breadth and depth are therefore graded **simultaneously**.

At any given moment:

- improving the current best topic can raise the grade
- improving a weaker already-touched topic can also raise the grade
- opening a new topic can also raise the grade

Which increase matters more depends on the current ranked mastery profile and the fixed cross-topic weights.

---

## Cross-topic weighting and lecture-wide interpretation

Python computes the final grade by ranking topics by current raw mastery and
applying the fixed cross-topic weights and ranked full-credit targets below.

These weights are fixed by policy.

| Rank | Weight | Full-credit target | Max cumulative | Interpretation |
| ---: | -----: | -----------------: | --------: | -------------- |
| 1 | 55 | 90 | 55  | Strong foothold in one central lecture idea |
| 2 | 25 | 82 | 80  | Meaningful early coverage across the lecture |
| 3 | 13 | 74 | 93  | Solid grounding across the core lecture terrain |
| 4 | 7 | 62 | 100 | Full lecture mastery for session purposes |

Notes:

* **Rank** = topic rank after sorting topics by current mastery, highest first.
* **Weight** = fixed maximum credit contribution for the topic at that rank.
* **Full-credit target** = raw mastery needed to receive that rank's full credit contribution.
* **Max cumulative** = maximum cumulative grade available if the top *n* ranked topics meet their full-credit targets.
* **Interpretation** = a readable lecture-wide description of what that cumulative ceiling means.
* The weights apply to ranked topic mastery values, not to fixed topic identities.
* The current backend implementation uses exactly these four ranked scoring slots: `[55, 25, 13, 7]`, with full-credit targets `[90, 82, 74, 62]`.
* The previous fifth-topic requirement made sessions longer than desired. The old fourth and fifth tail weights have been folded into the new fourth slot so a serious, cooperative student can reach full session success with four substantial topic engagements.
* Lecture rubrics may contain more than four topics. Topics below the top four ranked mastery scores do not directly add to the numeric grade at that moment, but they can still matter pedagogically and can enter the top four if their demonstrated mastery becomes strong enough.
* The sampled topic count may exceed the number of ranked scoring slots; sampled topics define candidate opportunity space, not a requirement to complete every sampled topic.
* Breadth and depth are graded simultaneously: improving any topic can affect the grade, depending on its current mastery and rank.
* The interpretation column is descriptive. It does not add a separate grading rule.
* These are internal anchors, not student-facing labels.

---

## Within-topic shape

Within-topic grading should be strongly concave.

That means:

* early progress on a topic earns points quickly
* later progress on the same topic earns points more slowly
* first real understanding matters a lot
* later refinement still matters, but much more slowly
* very high mastery should be reachable, but only with sustained strong evidence

The cumulative mastery ladder for a single topic assumes a sequence of successful **demonstrations of understanding** of increasing difficulty, subtlety, or transfer. It will not reflect rigid prompt steps. Rather, the anchors will be passed to the tutor which will evaluate mastery and then grades will be applied based on the mastery level assesed. 

### Qualitative meaning of the levels

| Step | Level name | Meaning |
| ---: | ---------- | ------- |
| 1 | Anchored foothold | First meaningful contact with the topic; the student gets its basic criterion or core idea roughly right, but still thinly. |
| 2 | Clearer grasp | The student can make a useful distinction or give a usable explanation that separates the idea from at least one nearby confusion. |
| 3 | Student-owned explanation | The student can explain the idea in their own words with solid conceptual control, not just recognize or repeat a phrase. |
| 4 | Fresh check or guided transfer | The student survives a new check: a contrastive case, figure/code interpretation, or guided application beyond the original wording. |
| 5 | Robust independent use | The student can use the idea more independently in a nearby new case, with less reliance on the tutor’s framing. |
| 6 | High-confidence understanding | The student shows stable, independent understanding across more than one probe and can interpret the idea practically or analytically. |
| 7 | Strong transfer | The student shows unusually strong, transferable understanding: connecting the idea cleanly to another lecture idea or handling a less obvious case. |
| 8 | Near-complete session mastery | The student shows flexible, precise, independent command of the topic for session purposes, possibly extending slightly beyond the lecture’s direct examples without losing fidelity. |

### Cumulative mastery ladder

| Step | Mastery |
| ---: | ------: |
| 1 | 45  |
| 2 | 70  |
| 3 | 84  |
| 4 | 92  |
| 5 | 96  |
| 6 | 98  |
| 7 | 99  |
| 8 | 100 |

Notes:

* **Step** = successful demonstration number on the same topic.
* **Mastery** = cumulative within-topic mastery after that step.

### Marginal gain per additional successful demonstration

| Step | Marginal gain |
| ---: | ------------: |
|    1 |            45 |
|    2 |            25 |
|    3 |            14 |
|    4 |             8 |
|    5 |             4 |
|    6 |             2 |
|    7 |             1 |
|    8 |             1 |

This ladder is intentionally aggressive early and very flat late.


---

## How backend combines topic mastery into a grade

The tutor maintains a current mastery estimate for each topic.

The backend then:

1. ranks topics by current mastery
2. applies the fixed cross-topic weights and full-credit targets to the top four ranked mastery values
3. computes the current grade from the saturated calibrated contribution sum

This means:

- every increase in a topic’s mastery can matter until ranked full credit is reached
- the effect of an increase depends on that topic’s current rank
- breadth and depth are not separate phases
- there is no threshold a topic must cross before it “starts counting”

A topic with partial mastery already contributes.
A topic with stronger mastery contributes more.
A new topic may matter a lot, a little, or not much yet, depending on its resulting rank and score.

---

## Important caution

These tables are internal grading anchors.

They do **not** mean:

- the tutor should expose numbers to the student
- the tutor should talk about weights or grading arithmetic explicitly
- the tutor should narrate the grading policy during the dialogue

They **do** mean:

- tutor-side mastery assessments should be interpretable against this ladder
- Python-side grade computation should follow the calibrated ranked-target policy
- later prompt or policy work should remain consistent with this grading geometry
