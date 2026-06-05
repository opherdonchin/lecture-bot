# Implementation Spec

This document describes the current lecture-bot implementation. The README is the operational quick reference; this file is the compact architecture/spec view.

## 1. Stack

- Python 3.12
- FastAPI and Uvicorn
- SQLAlchemy with SQLite
- Pydantic and pydantic-settings
- Pixi for the development and deployment environment
- Jinja2 templates plus vanilla JavaScript
- OpenAI Python SDK for tutor replies, final report prose, and optional lecture artifact generation

## 2. Applications

The project runs two separate FastAPI apps.

| App | Entrypoint | Default root path | Production root path | Port |
|---|---|---:|---:|---:|
| Student chat | `app.main:app` | `/bot` | `/stats` | `8000` |
| Admin UI | `app.admin_main:app` | `/bot-admin` | `/stats-admin` | `8001` |

Root paths are configured with:

- `LECTURE_BOT_STUDENT_ROOT_PATH`
- `LECTURE_BOT_ADMIN_ROOT_PATH`

The production launch tasks call `scripts/serve_student.sh` and `scripts/serve_admin.sh`, which pass the matching Uvicorn `--root-path`.

## 3. Student API

The student app exposes a browser chat UI plus RPC-style JSON endpoints.

| Endpoint | Method | Behavior |
|---|---|---|
| `/` | GET | Render the chat UI. |
| `/health` | GET | Return `{"status": "ok"}`. |
| `/lectures` | GET | List lecture IDs with a `lecture_config.json`. |
| `/start_session` | POST | Load the lecture package, create a session, sample focus topics, persist the backend opening message. |
| `/send_message` | POST | Validate session, enforce timeout, reject non-English student text, call the tutor model, sanitize state, validate/log any private artifact, persist messages and audit row. |
| `/submit_note` | POST | Record a student note with session/turn/latest-message context without adding a move, changing state, or exposing the text to the tutor. |
| `/get_grade` | POST | Compute current grade from backend-owned best mastery state and return timing, reply count, and the latest tutor response. |
| `/generate_report` | POST | Build the same authoritative grade snapshot and ask OpenAI for report prose, with a local fallback and timing/move metadata. |
| `/restart_session` | POST | End the current session and create a fresh one for the same student and lecture. |

## 4. Admin App

The admin app is protected by HTTP Basic Auth using `ADMIN_USERNAME` and `ADMIN_PASSWORD`.

Current admin capabilities:

- list, create, and reopen lecture folders under `LECTURES_DIR`
- edit lecture metadata
- upload and delete lecture files
- select source files for slides, handout, notebook, and transcript
- run local conversion to processed text/markdown artifacts
- download manual prompt text and support bundles for minutes and rubric generation
- upload generated `minutes.json` and `rubric.md`
- refresh `topics` in `lecture_config.json` from uploaded rubric headings

## 5. Lecture Packages

Runtime lecture packages live under `LECTURES_DIR`, normally `lectures/`.

Each usable lecture directory requires:

- `lecture_config.json`
- `rubric.md`
- `slides.md`
- `handout.md`
- `minutes.json`

Optional runtime context:

- `bot_notes.md`

Build/admin workflows may also use:

- `notebook.md`
- `transcript.md`
- raw `.pptx`, `.qmd`, `.ipynb`, `.vtt`, `.md`, `.txt`, and sometimes `.pdf` sources

The runtime tutor context is assembled from configured context sections, currently limited by `app.bot_engine._RUNTIME_CONTEXT_KEYS` to `bot_notes`, `slides`, `handout`, and `minutes`.

## 6. Session State

Initial state is created in `app/session_manager.py`.

```json
{
  "topics_sampled": [],
  "topics_covered": [],
  "mastery": {},
  "best_mastery": {},
  "evidence_notes": {},
  "current_topic_id": null,
  "tutor_comment": "",
  "current_grade": 0.0,
  "timeout_warning_sent": false,
  "turn_count": 0
}
```

Field ownership:

- Backend-owned: `topics_sampled`, `best_mastery`, `current_grade`, `timeout_warning_sent`, `turn_count`
- Tutor-updated through sanitized model output: `mastery`, `evidence_notes`
- Backend-derived: `topics_covered`, derived from topics whose mastery is at least a meaningful foothold
- Tutor-local support: `current_topic_id`, `tutor_comment`

Private artifacts are not part of `session_state`. When a session has a fixed private artifact schema, each ordinary tutoring turn logs the returned private artifact in a separate table.

## 7. Tutor Runtime

The default runtime tutor prompt is `prompts/tutor_prompt.md`, selected by `Settings.tutor_prompt_template`.

The active private artifact schema, when present, is loaded from the generated schema file accompanying the active prompt. At session creation, the backend snapshots that schema text into `sessions.private_artifact_schema_json`. If no schema file exists for the active prompt, the session field is null and ordinary turns do not use private artifacts. Prompt history and schema history are not stored.

For each ordinary student turn, the backend:

1. loads recent messages,
2. computes timing context,
3. builds lecture context with deterministic truncation,
4. renders the tutor prompt plus injected runtime JSON, including `private_artifact_schema_json` when the session has one,
5. calls OpenAI with `response_format={"type": "json_object"}`,
6. sanitizes the returned assistant message,
7. sanitizes and merges state updates,
8. validates `private_artifact` when a session schema exists,
9. retries the tutor call once with a repair instruction if `private_artifact` is missing or invalid,
10. uses controlled fallback mode if the repair attempt still fails,
11. records a dialogue audit row,
12. logs the valid private artifact, or the post-repair validation failure,
13. persists the student and assistant messages.

The model is expected to return:

```json
{
  "assistant_message": "string",
  "updated_state": {
    "mastery": {},
    "evidence_notes": {},
    "topics_covered": []
  },
  "private_artifact": {}
}
```

`private_artifact` is required only when the session has `private_artifact_schema_json`. It is private/backend-facing, validated against the session schema, logged per turn, and never merged into tutoring state, messages, grading state, or lifecycle state. Missing or invalid private artifacts trigger one bounded repair attempt before the turn is accepted. If repair still fails, the backend uses controlled fallback mode, records the validation failure in the private artifact log, and does not expose the invalid model reply as the accepted student-facing turn.

The backend is conservative: unknown topic IDs are ignored, mastery values are clamped to `0..100`, backend-owned fields are preserved, and `topics_covered` is not trusted as authoritative.

## 8. Grading

Current-grade and final-report endpoints do not ask the model to compute the grade.

The backend computes grades by:

1. maintaining best demonstrated mastery per topic,
2. ranking topic mastery scores from highest to lowest,
3. applying fixed ranked-topic weights `[55, 25, 13, 7]` and full-credit targets `[90, 82, 74, 62]` to the top four ranked scoring slots,
4. flooring the calibrated saturated sum `weight * min(raw / target, 1)`.

The sampled topic count can be larger than the number of scoring slots. Sampling defines the candidate opportunity space for the session; it is not a requirement that every sampled topic be completed for full credit.

`grade_events` store accepted grade/report snapshots. The authoritative payload helper checks accepted `grade` and `report` events so both endpoints see the same best demonstrated grade.

## 9. Reports

`/generate_report` uses the authoritative backend grade snapshot, then calls the OpenAI report path to write student-facing prose. If the OpenAI report call fails or returns malformed output, the backend returns local fallback report text using the authoritative grade.

The report JSON includes:

- session and lecture identifiers
- start timestamp and report timestamp
- final grade
- elapsed, remaining, and total session minutes

## 10. Error Handling

Expected client and resource errors become 4xx responses. OpenAI auth/API/parse failures use explicit fallback paths for dialogue and report generation. Internal invariant violations are allowed to surface as 500s rather than being disguised as successful tutoring behavior.

See [`error_policy.md`](error_policy.md) for details.

## 11. Persistence

Core tables are defined in `app/models.py`:

- `sessions`
- `messages`
- `session_state`
- `grade_events`
- `dialogue_turn_audits`
- `private_artifact_logs`
- `session_notes`

`sessions.private_artifact_schema_json` is nullable. Non-null values are fixed for that session and written once at session creation.

`private_artifact_logs` stores one row per ordinary tutoring turn when the session has a private artifact schema. The log stores the artifact JSON text and a nullable validation error. Artifact internals are not decomposed into relational columns.

`session_notes` stores student-submitted notes separately from `messages`. Each note includes the current turn index, latest message IDs, and a state snapshot so it can be attached to the correct point in a session without affecting tutoring history or grading.

The SQLite database is runtime state, not a long-term archive. Databases, logs, private lecture material, exports, rosters, and `.env` files must not be committed.

## 12. Tests

Run:

```bash
pixi run test
```

Tests use temporary SQLite databases and fixture lecture packages. OpenAI calls are mocked in normal tests; passing tests do not prove API credentials, model availability, DNS, Nginx, systemd, or Moodle end-to-end behavior.
