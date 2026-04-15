# Working note: grading calibration and internal mastery ladder

## Status

This is the current working calibration for the lecture-bot grading design.

It is not yet a full implementation spec. It is a design note capturing the grading geometry we currently intend to build prompt behavior around.

The current idea is to make the prompt aware of two grading tables:

* a **within-topic mastery table**
* a **cross-topic breadth table**

The tutor should use these as internal anchors while balancing:

* breadth
* depth
* educational value
* student engagement

---

## Core grading geometry

### Cross-topic weighting

Working cross-topic scale:

* 0.55
* 0.25
* 0.12
* 0.05
* 0.02
* 0.01

Interpretation:

* the first mastered topic matters a great deal
* the second and third still matter substantially
* later breadth still counts, but progressively less
* this gives a bit more breathing room than the earlier 5-topic version while preserving the same overall shape

### Within-topic shape

Within-topic grading should be strongly concave.

That means:

* early progress on a topic earns points quickly
* later progress on the same topic earns points more slowly
* this creates an ongoing breadth/depth tradeoff
* after moderate mastery on one topic, opening a second or third topic can be more valuable than continuing to drill the first one
* later in the session, once several topics have meaningful evidence, revisiting and deepening earlier topics can again become attractive

---

## Working internal mastery ladder

This is the current working cumulative mastery ladder for a single topic, assuming a sequence of fully correct, student-owned answers of increasing difficulty / subtlety / transfer.

### Cumulative score after k successful answers on one topic

| Successful answers on topic | Cumulative mastery |
| --------------------------: | -----------------: |
|                           1 |                 45 |
|                           2 |                 70 |
|                           3 |                 84 |
|                           4 |                 92 |
|                           5 |                 96 |
|                           6 |                 98 |
|                           7 |                 99 |
|                           8 |                100 |

### Marginal gain per additional successful answer

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

Its purpose is to create the desired tradeoff:

* first contact and early understanding should count for a lot
* later refinement should still count, but much more slowly
* very high mastery should be reachable, but only with sustained strong evidence

---

## Breadth table

The tutor should also have an internal sense of how much lecture-wide coverage has been established.

| Number of topics mastered | Lecture-wide mastery description                   | Maximum grade |
| ------------------------: | -------------------------------------------------- | ------------: |
|                         1 | Strong foothold in one central lecture idea        |            55 |
|                         2 | Meaningful early coverage across the lecture       |            80 |
|                         3 | Solid grounding across the core lecture terrain    |            92 |
|                         4 | Broad and competent coverage of the lecture        |            97 |
|                         5 | Very broad coverage with only small gaps remaining |            99 |
|                         6 | Full lecture mastery for session purposes          |           100 |

Notes:

* These are internal anchors, not student-facing labels.
* “Mastered” here means meaningfully banked at a solid level, not merely touched.
* The table is meant to help the tutor feel the value of early breadth without forcing hard arithmetic every turn.

---

## Interpretation of the 8 within-topic levels

These are not rigid prompt steps. They are an internal grading anchor.

A rough interpretation is:

1. first meaningful contact / correct basic criterion
2. stronger grasp / clear distinction or usable explanation
3. solid explanation in own words
4. strong answer with fresh check or guided transfer
5. robust answer with more independent use
6. high-confidence independent understanding
7. unusually strong / transferable understanding
8. near-complete mastery on that topic for session purposes

The tutor should not mechanically walk through these levels. This is a scoring anchor, not a move ladder.

---

## How the two tables should work together

The tutor should not think in terms of raw evidence alone.

It should think in terms of the joint value of:

* deepening the current topic
* opening a new topic
* revisiting an earlier topic

The two tables jointly encode this:

* early depth matters because a topic can move quickly from 0 to 45 to 70 to 84
* early breadth matters because the first, second, and third meaningfully mastered topics add a lot of lecture-wide value
* later depth matters less because the within-topic ladder flattens sharply
* later breadth matters less because the cross-topic breadth table also flattens sharply

This means the tutor should naturally face a recurring question:

* is the next best move to deepen the current topic,
* to open another topic,
* or to return and strengthen an earlier one?

That tradeoff should be decided using both educational judgment and the internal grading geometry.

---

## Prompt-design implication

The prompt should likely include both internal tables, with short verbal descriptions.

The tutor should then be instructed to balance:

* likely gain in topic mastery
* likely gain in lecture-wide coverage
* educational value of the move
* student engagement and momentum

The goal is not for the tutor to act like a calculator.
The goal is for it to have a clearer internal model of why:

* opening a second or third topic can be very valuable,
* overdrilling a topic after moderate mastery can be wasteful,
* and returning later to deepen an earlier topic can again become the best move.

---

## Important caution

These tables are internal design anchors.

They do **not** mean:

* the tutor should expose numbers to the student
* the tutor should talk about weights or grading arithmetic explicitly
* the tutor should use a rigid scripted sequence of moves

They **do** mean:

* prompt logic should encode the intended breadth/depth tradeoff more concretely
* state updates should use the mastery ladder as a rough internal guide
* later prompt work should express when to stay, when to switch, and when to revisit earlier topics in a way that is aligned with these two tables

---

## Current working decision

For now, use:

* cross-topic scale: **0.55, 0.25, 0.12, 0.05, 0.02, 0.01**
* within-topic cumulative mastery ladder: **45, 70, 84, 92, 96, 98, 99, 100**
* breadth table anchored at maximum grades: **55, 80, 92, 97, 99, 100**

This is the current calibration to design prompts around unless later testing shows that it is too generous, too harsh, or induces the wrong switching behavior.
