# lecture-bot

A lecture-specific tutoring bot for university courses. Students choose a lecture, start a short chat session, discuss the lecture material with an OpenAI-backed tutor, and can request a current grade or final report.

## Current Behavior

- Student-facing FastAPI app in `app/main.py`.
- Browser chat UI in `app/templates/chat.html` and `app/static/chat.js`.
- OpenAI-backed tutoring turns in `app/bot_engine.py`.
- Backend-owned session state, weighted grade computation, grade events, dialogue-turn audit rows, and private artifact logs stored through SQLAlchemy.
- Current-grade and final-report endpoints compute from the best demonstrated topic mastery stored in backend state. Final report text is OpenAI-backed with a local fallback.
- Separate admin FastAPI app in `app/admin_main.py` for lecture setup and upload workflow.

## Stack

- Python 3.12, FastAPI, Uvicorn, SQLAlchemy, SQLite
- Pixi for environment and task management
- Vanilla JavaScript and Jinja2 templates
- OpenAI Python SDK for tutoring replies, report text, and optional lecture-artifact generation

## Quickstart

Run commands from the repository root so `.env`, `lectures/`, `data/`, `app/`, and `prompts/` resolve as expected.

```bash
pixi install
cp .env.example .env
pixi run init-db
pixi run dev
```

Then open <http://127.0.0.1:8000/bot/>.

For real tutoring behavior, set `OPENAI_API_KEY` in `.env` or the process environment. Without a valid key, dialogue and report generation use fallback paths and lecture-artifact generation fails.

## Commands

| Command | Purpose |
|---|---|
| `pixi run dev` | Initialize the SQLite schema if needed, then start the student app with auto-reload on `0.0.0.0:8000` and local dev path `/bot`. |
| `pixi run admin-dev` | Initialize the SQLite schema if needed, then start the admin app with auto-reload on `0.0.0.0:8001` and local dev path `/bot-admin`. |
| `pixi run stats-dev` | Initialize the SQLite schema if needed, then start the student app with auto-reload and path `/stats`. |
| `pixi run stats-admin-dev` | Initialize the SQLite schema if needed, then start the admin app with auto-reload and path `/stats-admin`. |
| `pixi run serve` | Start the student app for production-style use through `scripts/serve_student.sh`, using exported env vars or `.env` defaults. |
| `pixi run admin-serve` | Start the admin app for production-style use through `scripts/serve_admin.sh`, using exported env vars or `.env` defaults. |
| `pixi run stop` | Stop a process listening on port `8000`. |
| `pixi run admin-stop` | Stop a process listening on port `8001`. |
| `pixi run test` | Run the pytest suite. |
| `pixi run init-db` | Create the configured database tables. |
| `pixi run python scripts/build_lecture_package.py <lecture_id> --force` | Build or rebuild a lecture package from source files. |
| `pixi run python scripts/grade_moodle.py ...` | Run the Moodle grading helper script. |

Production startup should use the committed Pixi tasks or their underlying scripts:

```bash
pixi run serve
pixi run admin-serve
```

Use the admin process only when the admin UI is needed. The production-style serve scripts read host, port, and root path from exported environment variables or repo-root `.env` defaults and pass the matching Uvicorn `--root-path` internally. The local dev tasks force `/bot` and `/bot-admin` so they work consistently on a plain machine without matching the production prefix. Prefix configuration is summarized below in "Path Prefix Status"; see [docs/deployment_ubuntu.md](docs/deployment_ubuntu.md) for Ubuntu, systemd, and Nginx notes.

For a map of the docs directory, see [docs/README.md](docs/README.md).

## Student Routes

The student app is defined in `app/main.py`.

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Chat UI. |
| `/favicon.ico` | GET | Bot SVG favicon. |
| `/static/...` | GET | CSS, JavaScript, and SVG assets. |
| `/health` | GET | Health check. |
| `/lectures` | GET | List lecture IDs found under `LECTURES_DIR` with `lecture_config.json`. |
| `/start_session` | POST | Start a tutoring session for `student_id` and `lecture_id`. |
| `/send_message` | POST | Send a chat turn, call the tutor model, update state, validate/log private artifacts when configured, and persist messages/audit rows. |
| `/get_grade` | POST | Return current backend-computed grade, topic coverage labels, and timing fields. |
| `/generate_report` | POST | Generate final report text from the authoritative grade snapshot. |
| `/restart_session` | POST | End an existing session and create a new one for the same student/lecture. |

## Admin App

The admin app is separate from the student app and is defined in `app/admin_main.py`.

It requires HTTP Basic Auth. Configure credentials with:

```env
ADMIN_USERNAME=
ADMIN_PASSWORD=
```

If either value is missing, admin requests return HTTP 500. Wrong credentials return HTTP 401.

Admin routes include:

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Admin index. |
| `/lectures` | GET/POST | List lecture folders or create a lecture folder. |
| `/lectures/{lecture_id}` | GET | Lecture setup page. |
| `/lectures/{lecture_id}/metadata` | POST | Update title, course, and active flag. |
| `/lectures/{lecture_id}/sources` | POST | Select source files for slides, handout, notebook, and transcript. |
| `/lectures/{lecture_id}/upload` | POST | Upload a file into the lecture folder. |
| `/lectures/{lecture_id}/delete` | POST | Delete a non-config file from the lecture folder. |
| `/lectures/{lecture_id}/build/local` | POST | Convert selected local sources to markdown/text artifacts. |
| `/lectures/{lecture_id}/prompt/{stage}.txt` | GET | Download manual prompt text for `minutes` or `rubric`. |
| `/lectures/{lecture_id}/bundle/{stage}.zip` | GET | Download support files for manual artifact generation. |
| `/lectures/{lecture_id}/generated/{kind}` | POST | Upload generated `minutes.json` or `rubric.md`; rubric upload refreshes `topics`. |

Admin uploads write directly under the configured `LECTURES_DIR`. With the default configuration, that means repo-relative `lectures/<lecture_id>/`.

## Environment Variables

Settings are loaded by `pydantic-settings` from real environment variables and from `.env` in the current working directory. In normal use, run from the repository root and keep `.env` there.

Use [.env.example](.env.example) as the committed starting point for local or deployment environment files. Do not commit `.env` or secret values.

| Variable | Required? | Purpose |
|---|---:|---|
| `OPENAI_API_KEY` | Required for real tutor/report calls and generated lecture artifacts | API key used by the OpenAI SDK. |
| `OPENAI_MODEL` | No | Model name. Defaults to `gpt-5.4-mini`. |
| `LECTURE_BOT_STUDENT_ROOT_PATH` | No | Public root path for generated student URLs. Defaults to `/bot`; production can use `/stats`. |
| `LECTURE_BOT_ADMIN_ROOT_PATH` | No | Public root path for generated admin URLs. Defaults to `/bot-admin`; production can use `/stats-admin`. |
| `DATABASE_URL` | No | SQLAlchemy URL. Defaults to `sqlite:///data/lecture_bot.db`. |
| `LECTURES_DIR` | No | Directory for lecture packages. Defaults to `lectures`. |
| `ADMIN_USERNAME` | Required for admin app | HTTP Basic Auth username. |
| `ADMIN_PASSWORD` | Required for admin app | HTTP Basic Auth password. |
| `SESSION_TIMEOUT_MINUTES` | No | Session duration. Defaults to `20`. |
| `SESSION_WARNING_MINUTES` | No | Final-window timing threshold. Defaults to `5`. |
| `RECENT_MESSAGE_LIMIT` | No | Number of recent messages sent to the tutor model. Defaults to `10`. |
| `MAX_DIALOGUE_CONTEXT_CHARS` | No | Context character cap for dialogue prompts. Defaults to `45000`. |
| `MAX_GRADING_CONTEXT_CHARS` | No | Context character cap for grading/report context. Defaults to `70000`. |
| `SAMPLED_TOPIC_COUNT` | No | Number of sampled focus topics per session. Defaults to `5`. |
| `OPENING_TOPIC_CHOICE_COUNT` | No | Number of sampled topics shown in the opening prompt. Defaults to `3`. |
| `APP_NAME`, `APP_ENV` | No | Metadata/environment labels; not used for routing. |

Do not commit `.env` or secret values.

## Lecture Packages

`LECTURES_DIR` contains a root `config.json` plus one directory per lecture. The public repository currently tracks only `lectures/config.json` and `lectures/.gitkeep`; actual lecture packages are private runtime material and must be copied in after cloning.

The default runtime context in `lectures/config.json` expects:

- optional `bot_notes.md`
- required `slides.md`
- required `handout.md`
- required `minutes.json`

Each usable lecture directory also requires:

- `lecture_config.json`
- `rubric.md`

The build/admin pipeline can additionally use raw source files:

- slides: `.pptx`
- handout: `.qmd`, `.md`, `.txt`, or `.pdf` in the admin app; `.qmd` in the script pipeline
- notebook: `.ipynb`
- transcript: `.vtt`

Both flows are supported:

- Copy a complete lecture package directly into `LECTURES_DIR`.
- Use the admin UI to create a lecture folder, upload/select source files, build local markdown artifacts, download manual prompts/bundles, and upload generated `minutes.json` and `rubric.md`.

The script pipeline can also generate `minutes.json` and `rubric.md` through OpenAI:

```bash
pixi run python scripts/build_lecture_package.py lecture_03 --force
```

That generated path requires `OPENAI_API_KEY`.

## Runtime Files

Default repo-relative runtime locations:

| Path | Used For | Production note |
|---|---|---|
| `data/lecture_bot.db` | SQLite database | Keep private; mount or symlink to persistent storage. |
| `lectures/` | Lecture packages and admin uploads | Private course material; mount or symlink to persistent storage. |
| `prompts/*_private_artifact_schema.json` | Generated private artifact schemas accompanying runtime tutor prompts | Public only if they contain no course or student data. |
| `exports/` | Session/investigation exports from scripts | Private; do not publish. |
| `app.log`, `admin.log` | Legacy/dev log files used by local background runs | Avoid for production secrets; prefer journald or private `logs/`. |

If `DATABASE_URL` points to a SQLite file outside `data/`, create its parent directory before running `pixi run init-db`.

## Public / Private Split

Safe for the public repo:

- application code
- prompts
- generated private artifact schemas that contain no course or student data
- docs
- tests
- `lectures/config.json`

Keep private and copy after cloning `main`:

- `.env` and API keys
- admin credentials
- SQLite databases
- student rosters and Moodle exports
- runtime logs and investigation/session exports
- uploaded lecture source files
- processed lecture packages if they include private course content

## Path Prefix Status

The app supports configurable path prefixes while keeping the student and admin FastAPI apps separate.

Committed defaults:

- student app: `/bot`
- admin app: `/bot-admin`

Production override example:

- student app: `/stats`
- admin app: `/stats-admin`

Configure prefixes with `LECTURE_BOT_STUDENT_ROOT_PATH` and `LECTURE_BOT_ADMIN_ROOT_PATH`. The canonical production commands launch Uvicorn with the matching `--root-path` automatically:

```bash
LECTURE_BOT_STUDENT_ROOT_PATH=/stats pixi run serve
LECTURE_BOT_ADMIN_ROOT_PATH=/stats-admin pixi run admin-serve
```

## Tests

Run:

```bash
pixi run test
```

The tests use temporary SQLite databases and fixture lecture packages. They mock OpenAI calls for dialogue/report tests and do not prove that the configured API key, model name, account quota, or network path works.

Current coverage includes:

- root page and health endpoint
- lecture loading and context-file requirements
- session creation, restart, timeout behavior, message persistence, and audit rows
- session-fixed private artifact schema snapshots and per-turn artifact logging
- backend weighted grade computation and report response structure
- OpenAI fallback behavior for failed dialogue/report calls
- admin Basic Auth, lecture creation, source selection, local build, and generated-artifact upload
- conversion/build helpers for `.pptx`, `.qmd`, `.ipynb`, `.vtt`, generated minutes, and generated rubric paths

The tests do not currently verify deployment under `/stats`, Nginx behavior, systemd units, Moodle upload end-to-end behavior, or real OpenAI responses.
