# lecture-bot

A conversational tutoring bot for university lectures. Students start a session for a given lecture, chat with the bot about the material, and receive a grade based on demonstrated understanding.

## Stack

- Python 3.12, FastAPI, SQLAlchemy, SQLite
- Pixi for environment and task management
- Vanilla JS + Jinja2 for the browser UI
- OpenAI for bot responses and grading (integration pending)

## Quickstart

```bash
pixi install
pixi run init-db
pixi run dev
```

Then open http://127.0.0.1:8000/.

## Tasks

| Command | Purpose |
|---|---|
| `pixi run dev` | Start dev server with auto-reload |
| `pixi run test` | Run test suite |
| `pixi run init-db` | Initialise SQLite database |

## Project structure

```
app/          FastAPI application (main.py, models, session manager, bot engine)
app/static/   Frontend JS and CSS
app/templates/ Jinja2 HTML templates
prompts/      Prompt templates loaded at runtime
lectures/     Lecture packages (config, rubric, slides, handout, notebook)
scripts/      DB init and lecture build/conversion utilities
tests/        Pytest test suite
docs/         Implementation spec and project plan
data/         Runtime SQLite database (not committed)
```

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Chat UI |
| `/health` | GET | Health check |
| `/start_session` | POST | Start a new tutoring session |
| `/send_message` | POST | Send a chat message |
| `/get_grade` | POST | Get current grade estimate |
| `/generate_report` | POST | Generate final session report |
| `/restart_session` | POST | End current session and start a new one |

## Status

- [x] Session management and persistence
- [x] Chat UI in browser
- [x] Bot stub (echo responses)
- [ ] OpenAI integration
- [ ] Grading logic
