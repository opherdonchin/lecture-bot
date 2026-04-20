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
- Nginx + systemd for deployment; current target is Ubuntu 24.04 LTS

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
- The stored grade field is the current grade.
- Grade/report requests may be logged as grade events.

### Lecture package conventions
Each runtime lecture package must contain:
- `lecture_config.json`
- `rubric.md`
- `slides.md`
- `handout.md`
- `minutes.json`
- optional `bot_notes.md`

The build/admin pipeline may also produce or use:
- `notebook.md`
- `transcript.md`
- raw source files such as `.pptx`, `.qmd`, `.ipynb`, `.vtt`, and sometimes `.pdf`

Source files such as `.pptx`, `.qmd`, and `.ipynb` may also be present.  
The app reads only processed markdown/text outputs.

### File conversion conventions
- `lecture_config.json` defines source/target file mappings under `files`.
- Conversion/build logic lives in `scripts/`.
- A master build script should generate processed lecture files from raw sources.
- v1 conversion is text-only and does not attempt figure understanding.

### Deployment conventions

- The current student app entrypoint is `app.main:app`.
- The current admin app entrypoint is `app.admin_main:app`.
- Current launch is direct Uvicorn, for example `pixi run uvicorn app.main:app --host 127.0.0.1 --port 8000`.
- The intended public paths are `/stats` for students and `/stats/stats-admin` for admin.
- Current code still uses root-relative frontend URLs and does not cleanly support those path prefixes without code changes.

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

Uses backend-owned best mastery state and Python weighted grade computation. The older dedicated grading-prompt path remains in `app/bot_engine.py` but is not used by the current `/get_grade` endpoint.

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

Uses the same authoritative backend grade snapshot, then asks the report-generation path to write report text. If the OpenAI report call fails, the backend returns a local fallback report.

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
  "turn_count": 0,
  "confidence": 0.0
}
```

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
* Move topic if needed

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

* Student app: no authentication
* Admin app: HTTP Basic Auth configured by `ADMIN_USERNAME` and `ADMIN_PASSWORD`
* No tokens
* No resume
* Text-only
* Full rubric each turn

---

## 8. Current Admin UI

The repository includes a separate admin FastAPI app in `app/admin_main.py`.

Current admin capabilities:

* list, create, and reopen lecture folders under `LECTURES_DIR`
* upload and delete files in a lecture folder
* select source files for slides, handout, notebook, and transcript
* run local conversion to `slides.md`, `handout.md`, `notebook.md`, and `transcript.md`
* download manual prompt text and support bundles for minutes/rubric generation
* upload `minutes.json` and `rubric.md`
* refresh `topics` in `lecture_config.json` from uploaded rubric headings

## 9. Extensions (future)

* Token system
* Path-prefix-aware deployment under `/stats`
* Multi-lecture routing
* Figure handling
* REST API
