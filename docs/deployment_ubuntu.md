# Ubuntu 24.04 Deployment Notes

This document describes the current repository state for a clean Ubuntu 24.04 LTS server. The apps support configurable path prefixes, with repo defaults at `/bot` and `/bot-admin` and the intended production override at `/stats` and `/stats-admin`.

## Current Verdict

- Student app entrypoint: `app.main:app`.
- Admin app entrypoint: `app.admin_main:app`.
- Canonical production startup is through `pixi run serve` and `pixi run admin-serve`.
- Those tasks call committed scripts that launch Uvicorn with the matching `--root-path`.
- Example systemd unit templates are committed under `deploy/systemd/`.
- Prefix-aware URLs are configured through `LECTURE_BOT_STUDENT_ROOT_PATH` and `LECTURE_BOT_ADMIN_ROOT_PATH`.

## Server Packages

Install the system packages needed by the Python package set and lecture conversion workflow:

```bash
sudo apt update
sudo apt install -y curl git nginx sqlite3 lsof poppler-utils
```

`poppler-utils` provides `pdftotext`, which the admin handout conversion path uses for uploaded PDFs. Install Pixi using the official installer for your server account, then ensure the `pixi` binary is on the PATH used by systemd.

## Clone And Private Material

Clone the public repository from `main`:

```bash
git clone <repo-url> lecture-bot
cd lecture-bot
pixi install
```

Start from the committed environment template, then copy private runtime material after cloning:

```bash
cp .env.example .env
```

- `.env`
- lecture packages under `lectures/<lecture_id>/`
- any existing production SQLite database, if migrating one
- Moodle roster/export files, if using grading scripts

The public repo only tracks `lectures/config.json` and `lectures/.gitkeep`; actual lecture folders are private course material.

## Environment

Create `.env` in the repository root from [.env.example](../.env.example), or set equivalent environment variables in systemd.

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
DATABASE_URL=sqlite:///data/lecture_bot.db
LECTURES_DIR=lectures
ADMIN_USERNAME=
ADMIN_PASSWORD=
LECTURE_BOT_STUDENT_ROOT_PATH=/bot
LECTURE_BOT_ADMIN_ROOT_PATH=/bot-admin
```

`pydantic-settings` loads `.env` relative to the current working directory, so set `WorkingDirectory` to the repository root in systemd.

For production, prefer persistent paths outside the git working tree and point the app at them:

```env
DATABASE_URL=sqlite:////srv/lecture-bot/data/lecture_bot.db
LECTURES_DIR=/srv/lecture-bot/lectures
LECTURE_BOT_STUDENT_ROOT_PATH=/stats
LECTURE_BOT_ADMIN_ROOT_PATH=/stats-admin
```

Create the parent directories first and make them writable by the service user.

## Initialize Database

From the repo root:

```bash
pixi run init-db
```

This creates SQLAlchemy tables for the configured `DATABASE_URL`. The script also creates repo-local `data/`, but if `DATABASE_URL` points elsewhere, create that external parent directory yourself before running the command.

## Canonical Production Launch

Student app:

```bash
pixi run serve
```

Admin app, only when needed:

```bash
pixi run admin-serve
```

Use `127.0.0.1` behind Nginx so the apps are not directly exposed on the public interface. The scripts default to `127.0.0.1`, ports `8000` and `8001`, and repo prefixes `/bot` and `/bot-admin`.

For the intended production prefixes:

```bash
LECTURE_BOT_STUDENT_ROOT_PATH=/stats pixi run serve
LECTURE_BOT_ADMIN_ROOT_PATH=/stats-admin pixi run admin-serve
```

Optional startup-script environment variables:

- `LECTURE_BOT_STUDENT_HOST`, default `127.0.0.1`
- `LECTURE_BOT_STUDENT_PORT`, default `8000`
- `LECTURE_BOT_ADMIN_HOST`, default `127.0.0.1`
- `LECTURE_BOT_ADMIN_PORT`, default `8001`

## Example systemd Units

Example templates are committed at:

- [deploy/systemd/lecture-bot.service.example](../deploy/systemd/lecture-bot.service.example)
- [deploy/systemd/lecture-bot-admin.service.example](../deploy/systemd/lecture-bot-admin.service.example)

They use `/srv/lecture-bot` as the working directory, `/etc/lecture-bot/stats.env` as the environment file, and the canonical Pixi tasks as `ExecStart`.

Example `/etc/lecture-bot/stats.env`:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
DATABASE_URL=sqlite:////srv/lecture-bot/data/lecture_bot.db
LECTURES_DIR=/srv/lecture-bot/lectures
ADMIN_USERNAME=
ADMIN_PASSWORD=
LECTURE_BOT_STUDENT_ROOT_PATH=/stats
LECTURE_BOT_ADMIN_ROOT_PATH=/stats-admin
```

Copy the example units to `/etc/systemd/system/`, adjust user, paths, and Pixi path for the actual server, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now lecture-bot.service
sudo systemctl status lecture-bot.service
```

Start the admin service only when needed:

```bash
sudo systemctl start lecture-bot-admin.service
```

Logs should go to journald:

```bash
journalctl -u lecture-bot.service -f
journalctl -u lecture-bot-admin.service -f
```

## Nginx Shape

For the intended production prefixes, proxy `/stats/` to the student process and `/stats-admin/` to the admin process. The app processes still listen locally without the public prefix; the startup scripts pass Uvicorn the selected `--root-path`.

Example student location:

```nginx
server {
    listen 80;
    server_name example.edu;

    location = /stats {
        return 308 /stats/;
    }

    location /stats/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## `/stats` Path Prefix Deployment

The app now supports configurable path prefixes while keeping the student and admin FastAPI apps separate.

Committed defaults:

- student app: `/bot`
- admin app: `/bot-admin`

Intended production override:

- student app: `/stats`
- admin app: `/stats-admin`

Set `LECTURE_BOT_STUDENT_ROOT_PATH` and `LECTURE_BOT_ADMIN_ROOT_PATH` before app import, and use the canonical startup tasks so Uvicorn receives matching `--root-path` values:

```bash
LECTURE_BOT_STUDENT_ROOT_PATH=/stats pixi run serve
LECTURE_BOT_ADMIN_ROOT_PATH=/stats-admin pixi run admin-serve
```

The templates generate prefixed static URLs, admin links/forms, and student API URLs. The browser chat frontend reads its API endpoints from the server-rendered `window.APP_ROUTES` object. See [path_prefix_change_note.md](path_prefix_change_note.md) for the focused implementation note.

## Runtime Files And Permissions

Recommended persistent layout:

```text
/srv/lecture-bot/app-repo/      cloned public repo
/srv/lecture-bot/data/          private SQLite database
/srv/lecture-bot/lectures/      private lecture packages and admin uploads
/srv/lecture-bot/exports/       private export packages, if used
```

Configure:

```env
DATABASE_URL=sqlite:////srv/lecture-bot/data/lecture_bot.db
LECTURES_DIR=/srv/lecture-bot/lectures
```

The service user needs write access to the database file and parent directory. If the admin app is used, the service user also needs write access to `LECTURES_DIR`.

## Smoke Checks

After start:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/lectures
```

Then open the browser UI and start a test session with a non-sensitive fixture lecture. Passing local tests does not prove that the production OpenAI credentials, model, DNS, TLS, Nginx path handling, or private lecture files are correct.
