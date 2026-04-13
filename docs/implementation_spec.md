# Implementation Spec (v1)

This document defines the exact behavior of the lecture-bot system.
All implementation should follow this specification.

---

## 0. Technologies and implementation conventions

### Core stack
- Python 3.12
- FastAPI for the web application
- SQLAlchemy 2.x for ORM/database access
- SQLite for v1 persistence
- Pixi for environment and task management
- Uvicorn as the ASGI server
- Nginx + systemd for deployment on the Fedora server

### API style
- Use a simple RPC-style API for v1.
- Primary workflow endpoints:
  - `POST /start_session`
  - `POST /send_message`
- Internal data model should still remain resource-oriented.

### UI conventions
- Main interaction is a chat UI.
- Minimal control buttons are preferred for:
  - Get current grade
  - Generate final report
  - Restart session
- Avoid quiz-style UI elements.
- Keep the interaction conversational.
- Do not add progress bars or other rigid progress UI in this pass.

### Persistence conventions
- Store sessions, messages, session state, and optional grade events in SQLite.
- The database is runtime state for the current semester, not long-term archival storage.
- Logs, exports, databases, roster files, and secrets remain local and are never committed.

### LLM integration conventions
- Use real OpenAI API calls from the beginning.
- Separate:
  - dialogue prompt path for ordinary tutoring turns
  - grading/report prompt path for current-grade and final-report actions
- Pass the full rubric and full concatenated lecture text to the model in v1.

### Grading conventions
- Use weighted best-topic scoring:
  - 55
  - 25
  - 13
  - 4
  - 3
- Grade is the sum of the best demonstrated five topic scores, rounded down.
- Do not redesign this formula in this pass.
- Recalibrate within-topic mastery semantics separately from the top-level weighting.
- The stored grade field is the current grade.
- Grade/report requests may be logged as grade events.
- Within-topic mastery calibration should follow `docs/policy_routing_spec.md` and `docs/session_calibration.md`.

### Lecture package conventions
Each lecture package should ultimately contain:
- `lecture_config.json`
- `rubric.md`
- `slides.md`
- `handout.md`
- `notebook.md`
- optional `bot_notes.md`

Source files such as `.pptx`, `.qmd`, and `.ipynb` may also be present.  
The app reads only processed markdown/text outputs.

### File conversion conventions
- `lecture_config.json` defines source/target file mappings under `files`.
- Conversion/build logic lives in `scripts/`.
- A master build script should generate processed lecture files from raw sources.
- v1 conversion is text-only and does not attempt figure understanding.

### Repository conventions
- Repository code/spec may remain public.
- Never commit:
  - `.env`
  - API keys
  - OAuth secrets
  - student roster / ID files
  - local databases
  - runtime logs
  - exports

### Coding conventions
- Prefer simple modules and explicit code over abstraction.
- Keep prototype velocity high.
- Add tests where they materially help implementation stay aligned with the spec.
- If behavior is unclear, update the spec before implementing.

## 1. API (RPC-style)

### 1.1 Start Session

POST /start_session

Request:

```json
{
  "student_id": "string",
  "lecture_id": "string"
}
```

Response:

```json
{
  "session_id": "string",
  "message": "string"
}
```

Behavior:

* Create session
* Initialize state
* Sample rubric topics
* Open with a brief conversational choice among 2-3 sampled lecture topics

---

### 1.2 Send Message

POST /send_message

Request:

```json
{
  "session_id": "string",
  "message": "string"
}
```

Response:

```json
{
  "message": "string",
  "session_active": true
}
```

Behavior:

* Check timeout
* Append message
* Run bot engine
* Update state
* Enter a soft closing mode after about 25 minutes, without abruptly ending the session

---

## 2. Control Actions

Triggered via UI buttons (preferred) or commands.

### 2.1 Get Current Grade

Returns:

```json
{
  "grade": 0-100,
  "explanation": "string",
  "missing_topics": ["string"]
}
```

Uses dedicated grading prompt.
The grade explanation should briefly identify the strongest topic so far and the next most promising improvement area when the grading payload supports it.

---

### 2.2 Generate Final Report

Returns:

```json
{
  "report_text": "string",
  "report_json": {
    "session_id": "string",
    "student_id": "string",
    "timestamp": "ISO",
    "final_grade": number
  }
}
```

Uses dedicated grading/report prompt.
The report text should explicitly mention:

* the student's strongest topic so far
* the next best topic to improve
* whether the student would likely benefit more from deepening covered topics or moving to uncovered ones

---

### 2.3 Restart Session

* Ends current session
* Creates new session

---

## 3. Session State

Stored per session:

```json
{
  "topics_sampled": [],
  "topics_covered": [],
  "mastery": {},
  "evidence_notes": {},
  "turn_count": 0
}
```

> **Note (step-1 migration):** The `confidence` field from the original design has been removed.
> Confidence is now expressed through the mastery score itself (see `docs/policy_routing_spec.md`).
> A new `evidence_notes` field (per-topic string tags) has been added.
> Backend-owned prompt context may also include sampled topic labels, approximate elapsed session time, and a `closing_mode` flag. Those are prompt inputs rather than model-owned state fields.

---

## 4. Grading Model

Topic-weighted scoring:

* 55
* 25
* 13
* 4
* 3

Rules:

* Select best 5 topics
* Score each independently
* Sum and round down

---

## 5. Bot Engine Contract

### Input

* system prompt
* rubric (full)
* lecture content (full)
* session state
* recent messages
* backend-owned prompt context such as sampled topic labels and approximate elapsed time / `closing_mode`

### Output

```json
{
  "assistant_message": "string",
  "updated_state": {}
}
```

Responsibilities:

* Ask next question
* Evaluate answer
* Update mastery
* Choose the next tutoring move heuristically rather than by a rigid ladder
* Adjust challenge up or down when the student's signals warrant it
* Give compact orienting information when repeated probing would be low-yield
* Move topic if needed
* Offer topic choices naturally when opening or re-engaging
* Shift into conversational closing mode after about 25 minutes
* Count the student's final message toward grading/reporting

---

## 6. Data Model

### sessions

* session_id
* student_id
* lecture_id
* started_at
* ended_at
* current_grade

### messages

* id
* session_id
* role
* content
* timestamp

### session_state

* session_id
* state_json

### grade_events (optional)

* session_id
* timestamp
* type
* grade

---

## 7. Constraints

* No authentication
* No tokens
* No resume
* Text-only
* Full rubric each turn
* Keep the interaction conversational
* Do not add UI buttons beyond the existing minimal control set in this pass
* Do not add progress bars
* Do not treat topic number as an input to within-topic scoring

---

## 8. Extensions (future)

* Token system
* Admin UI
* Multi-lecture routing
* Figure handling
* REST API
