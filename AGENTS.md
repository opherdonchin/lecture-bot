# Agent instructions — lecture-bot

## What this project is

Lecture-bot is a lecture-specific tutoring bot for university courses. A
student picks a lecture, holds a short graded chat with an OpenAI-backed
tutor grounded in that lecture's materials, and can request a current grade
or final report. A separate admin app prepares lecture packages, reviews and
exports sessions, and prepares Moodle grade imports. The [README](README.md)
describes routes, commands, configuration and the lecture-package format.

## How we work

Development follows lecture-bot's HILD process. **Read
[HILD/process.md](HILD/process.md) first**; it defines scope agreements,
review tracks, explanations, durable state, decisions and autonomy. Current
goals and next steps are in [HILD/plan.md](HILD/plan.md). Do not restate
process rules here.

## Where things live

- `app/`: the student app (`main.py`), the admin app (`admin_main.py`) and
  their modules, templates and static files.
- `scripts/`: conversion, build, export, Moodle and deployment scripts.
- `tests/`: the pytest suite. `tests/hild/` tests the HILD scripts.
- `docs/`: authoritative product, tutor and grading design; start at
  [docs/README.md](docs/README.md).
- `prompts/`: the runtime tutor prompt, its private-artifact schema and the
  generation and analysis prompts. `prompts/archive/` and `docs/archive/` are
  deliberate histories of the runtime prompt and specification; keep them.
- `example_content/`: the public example lecture package.
- `deploy/`: example systemd units and the remote-workflow configuration.
- `HILD/`: process, plan, journal, decisions, templates and HILD scripts.

## Project rules

1. **The repository is public.** Never commit student IDs, names, session
   text, grades, rosters, Moodle exports, credentials, API keys or
   unpublished course materials. The same applies to journals, PR
   explanations, issues and the wiki. Describe evidence from student
   sessions in aggregate and keep the underlying data in the private
   instance folders.
2. **The repository is the source; servers are targets.** The repository is
   authoritative for code, prompts and docs. Each course instance owns its
   lectures, database, submissions, exports and logs, which live outside the
   clone (`/srv/...` on the server, `~/lecture-bot-instances/<course>/` on a
   development machine). Do not copy instance data into the repository.
3. **Publish to production only from a clean, merged `main`.**
   `pixi run publish-prod` rsyncs the working tree as it stands, so running
   it from a branch or a dirty tree deploys unreviewed code. Publishing has
   external effects; do it only when the researcher asks.
4. **Run commands through Pixi from the repository root**, using the tasks in
   [pixi.toml](pixi.toml) and the [README](README.md). Run `pixi run test`
   before proposing a change for review.

## Python import style

**Always use `import module as alias`; never `from module import name`.**
This makes it immediately clear which module each name comes from.

```python
# Correct
import json as j
import pathlib as pathlib_

import fastapi as fa
import pydantic as pd
import sqlalchemy as sa
import sqlalchemy.orm as sqlalchemy_orm

import app.models as models
import app.config as config_module

# Wrong
from json import loads
from fastapi import FastAPI, HTTPException
from app.models import SessionModel
```

Alias conventions:

- Standard library: short or descriptive aliases (`json` → `j`,
  `pathlib` → `pathlib_`, `functools` → `functools_`, `dataclasses` → `dc`,
  `sys` → `sys_module`).
- Third-party packages: descriptive aliases (`fastapi` → `fa`,
  `pydantic` → `pd`, `sqlalchemy` → `sa`, `pptx` → `pptx_module`).
- Local modules: the module name or purpose (`app.config` → `config_module`,
  `scripts.convert_ipynb_to_md` → `convert_ipynb`).

Also use type hints on function parameters and return values, and give
public functions and classes docstrings.

Copied HILD tooling (`HILD/scripts/`, `tests/hild/`) keeps its upstream
style so that its provenance stays recognizable.
