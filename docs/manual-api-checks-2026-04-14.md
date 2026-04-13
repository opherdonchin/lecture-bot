# Manual API Checks

App run locally with:

```bash
pixi run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Port `8000` was already in use in this workspace, so `8001` was used for the live checks.

## Live issue found and fixed

The first live run exposed a real observability bug:

- `log_dialogue_turn_audit()` tried to migrate the audit table with `Engine.execute`
- on the running app this raised `AttributeError`
- result: the new audit fields were not persisted even though tests passed

This was fixed in [app/session_manager.py](/home/opher/Repositories/lecture-bot/app/session_manager.py:92) by running the `ALTER TABLE` statements through a real connection.

## Session A: behavior and grading checks

Session id:

- `8aab3aac-a2f7-47b8-9040-0619b1e1230a`

### Start session

Request:

```bash
curl -s http://127.0.0.1:8001/start_session \
  -H "Content-Type: application/json" \
  -d '{"student_id":"999999999","lecture_id":"lecture_01"}'
```

Observed:

- opening message used the new bullet-list format

### Steering request

Student:

```text
Ask me the kind of question that is most likely to improve my grade.
```

Assistant:

```text
A datum can be a vector-valued observation, and the data are finite. Suppose a brain-scan study records age, education, and normalized brain volume for each person: what is one reason that changing the measurement or representation of those variables can change the conclusion?
```

Result:

- good: it re-entered content immediately
- good: no move narration
- mixed: it answered with content directly, but did not give a short explicit steering acknowledgment first

### Repetition complaint

Student:

```text
You are repeating yourself. What exactly was missing from my answer?
```

Assistant:

```text
You had the right idea, but you didn’t name the key distinction: changing what you measure or how you represent it can change the conclusion because data are finite observations, not the reality itself. What is one concrete example of a measurement choice that would change the conclusion?
```

Result:

- good: it named the missing distinction
- good: it did not re-ask the same question verbatim
- acceptable: it transformed the follow-up rather than staying procedural

### Harder-question request

Student:

```text
That is too easy. Ask me something harder that actually gets points.
```

Assistant:

```text
A measurement choice can change the conclusion because data are finite observations, not reality itself. In the brain-scan example, what is one concrete way that using raw cerebellar volume versus normalized cerebellar volume could lead you to a different conclusion?
```

Result:

- weak: still not clearly higher-ceiling
- the wording changed, but the question stayed close to the same local line

### Topic switch

Student:

```text
Let us switch topics.
```

Assistant:

```text
Switching to imperfection in data. A pulse oximeter was tested mostly on white skin and then used on darker skin; is that sampling bias, measurement error, missing data, or a proxy measure?
```

Result:

- good: switched cleanly in one turn
- good: returned immediately to content

### Grade and report

After a few strong answers:

`/get_grade` returned:

```json
{"grade":72.0,...}
```

`/generate_report` returned:

```json
{"report_json":{"final_grade":72.0},...}
```

Result:

- good: report and report JSON agreed on the final grade for this run

## Session B: audit-field verification after the fix

Session id:

- `aebc9d01-8266-4912-8d61-85ab8bb9accd`

### Steering request

Student:

```text
Ask me the kind of question that is most likely to improve my grade.
```

Assistant:

```text
A data table from a brain scan study includes age, education, gender, and normalized brain volume for each person. Which of these are continuous, categorical, and ordinal?
```

Result:

- good: immediate return to content
- weak: still a fairly low-ceiling question for an efficiency request

### Harder-question request

Student:

```text
That is too easy. Ask me something harder that actually gets points.
```

Assistant:

```text
A brain-scan dataset records age, education, gender, handedness, TIV, and normalized brain volume for each person: which are continuous, which are categorical, and which are ordinal?
```

Result:

- weak: backend chose `challenge_level = 5`, but the model still produced a low-level classification question

### Topic switch

Student:

```text
Let us switch topics.
```

Assistant:

```text
Reality, data, and models are distinct: reality is what exists, data are the finite measurements we get from it, and models are the framework we use to reason from those measurements. A brain-scan study measures cerebellar volume from scans; what is the model doing that the data alone cannot do?
```

Result:

- good: clean topic switch
- good: stronger conceptual question than the earlier types-of-data line

### Audit row check

After the audit fix, the stored rows included the new fields:

```text
turn 0: provide_technical_support | tutor_prompt.md | technical_request | challenge_level=5 | target_topic_id=T1 | ended_with_content_question=1 | switched_topics=1
turn 1: provide_technical_support | tutor_prompt.md | technical_request | challenge_level=5 | current_topic_id=T1 | target_topic_id=T1 | ended_with_content_question=1
turn 2: provide_technical_support | tutor_prompt.md | technical_request | challenge_level=4 | current_topic_id=T6 | target_topic_id=T1 | ended_with_content_question=1 | switched_topics=1
```

That confirmed:

- unified tutor prompt in use
- mode hint persisted
- action hints persisted
- challenge level persisted
- switch behavior persisted

### Additional grading check

This session showed the monotone authoritative-grade behavior:

- first `/get_grade`: `50.0`
- after `/generate_report`: `final_grade = 86.0`
- later `/get_grade`: `86.0`

This is consistent with the current design: later accepted grading events can raise the authoritative grade, but not lower it.

## Overall manual verdict

What improved clearly:

- less procedural stalling
- immediate return to content after steering requests
- clean topic switching
- audit data now rich enough for loop diagnosis

What still needs work:

- stronger real difficulty escalation on “harder / gets points”
- tighter stop conditions after a clearly sufficient answer
- fewer disguised repeats on the same conceptual point
