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
| `pixi run admin-dev` | Start the admin lecture-setup app on port 8001 |
| `pixi run admin-stop` | Stop the admin lecture-setup app |
| `pixi run test` | Run test suite |
| `pixi run init-db` | Initialise SQLite database |
| `pixi run build-lecture -- <lecture_id> --force` | Build lecture markdown, minutes, and rubric artifacts |

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

## Lecture Build Pipeline

`lecture_config.json` is the pipeline manifest for each lecture. The `files` map can now describe:

- converted sources: `slides`, `handout`, `notebook`, `transcript`
- generated artifacts: `minutes`, `rubric`

Example:

```json
{
  "files": {
    "slides": { "source": "Lecture 3.pptx", "target": "slides.md" },
    "handout": { "source": "Lecture 3 handout.qmd", "target": "handout.md" },
    "notebook": { "source": "Lecture03.ipynb", "target": "notebook.md" },
    "transcript": { "source": "Lecture03.vtt", "target": "transcript.md" },
    "minutes": { "target": "minutes.json" },
    "rubric": { "target": "rubric.md" }
  }
}
```

Running `pixi run build-lecture -- lecture_03 --force` will:

- convert the source files to markdown
- convert the WebVTT transcript into a cleaner markdown transcript
- generate `minutes.json` from slides, handout, notebook, and transcript
- generate `rubric.md` from slides, handout, notebook, and minutes
- refresh `topics` inside `lecture_config.json` from the resulting rubric

## Admin App

The repo also includes a separate lecture-admin app for manual lecture setup. It is intended to be started only when needed:

```bash
pixi run admin-dev
```

Set admin credentials in `.env`:

```env
ADMIN_USERNAME=your_name
ADMIN_PASSWORD=your_password
```

The admin app lets you:

- create or reopen lecture folders
- upload and delete files inside a lecture folder
- choose which files are the selected source files
- build the local markdown artifacts
- download the exact prompt text and support bundle for the manual ChatGPT steps
- upload `minutes.json` and `rubric.md` back into the correct lecture folder
- refresh `topics` in `lecture_config.json` from the uploaded rubric
