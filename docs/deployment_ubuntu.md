# Ubuntu 24.04 Deployment Notes

This document describes the current repository state for a clean Ubuntu 24.04 LTS server. It is operational for root-mounted deployment today, and it calls out the code changes still needed for the intended `/stats` and `/stats/stats-admin` public paths.

## Current Verdict

- Student app entrypoint: `app.main:app`.
- Admin app entrypoint: `app.admin_main:app`.
- Current production launch is direct Uvicorn through Pixi.
- No production Pixi task or service file is committed.
- The code currently assumes root-relative public URLs and does not cleanly support `/stats`.

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

Copy private runtime material after cloning:

- `.env`
- lecture packages under `lectures/<lecture_id>/`
- any existing production SQLite database, if migrating one
- Moodle roster/export files, if using grading scripts

The public repo only tracks `lectures/config.json` and `lectures/.gitkeep`; actual lecture folders are private course material.

## Environment

Create `.env` in the repository root, or set equivalent environment variables in systemd.

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
DATABASE_URL=sqlite:///data/lecture_bot.db
LECTURES_DIR=lectures
ADMIN_USERNAME=
ADMIN_PASSWORD=
SESSION_TIMEOUT_MINUTES=20
SESSION_WARNING_MINUTES=5
```

`pydantic-settings` loads `.env` relative to the current working directory, so set `WorkingDirectory` to the repository root in systemd.

For production, prefer persistent paths outside the git working tree and point the app at them:

```env
DATABASE_URL=sqlite:////srv/lecture-bot/data/lecture_bot.db
LECTURES_DIR=/srv/lecture-bot/lectures
```

Create the parent directories first and make them writable by the service user.

## Initialize Database

From the repo root:

```bash
pixi run init-db
```

This creates SQLAlchemy tables for the configured `DATABASE_URL`. The script also creates repo-local `data/`, but if `DATABASE_URL` points elsewhere, create that external parent directory yourself before running the command.

## Manual Production Launch

Student app:

```bash
pixi run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Admin app, only when needed:

```bash
pixi run uvicorn app.admin_main:app --host 127.0.0.1 --port 8001
```

Use `127.0.0.1` behind Nginx so the apps are not directly exposed on the public interface.

## Example systemd Units

Create `/etc/systemd/system/lecture-bot.service`:

```ini
[Unit]
Description=Lecture Bot student app
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=lecturebot
Group=lecturebot
WorkingDirectory=/srv/lecture-bot/app-repo
Environment=PATH=/home/lecturebot/.pixi/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/lecturebot/.pixi/bin/pixi run uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/lecture-bot-admin.service` if the admin app should be available:

```ini
[Unit]
Description=Lecture Bot admin app
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=lecturebot
Group=lecturebot
WorkingDirectory=/srv/lecture-bot/app-repo
Environment=PATH=/home/lecturebot/.pixi/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/lecturebot/.pixi/bin/pixi run uvicorn app.admin_main:app --host 127.0.0.1 --port 8001
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Adjust user, paths, and Pixi path for the actual server. Then:

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

For the current code, the simplest working Nginx shape is to serve the student app at the origin root and put the admin app on a separate host or route that does not require rewriting generated links.

Example root-mounted student app:

```nginx
server {
    listen 80;
    server_name example.edu;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## `/stats` Status And Blocker

The intended public paths are:

- student app: `/stats`
- admin app: `/stats/stats-admin`

The current code does not support that cleanly:

- `app/templates/chat.html` uses `/static/...`.
- `app/static/chat.js` fetches `/lectures`, `/start_session`, `/send_message`, `/get_grade`, `/generate_report`, and `/restart_session`.
- admin templates use root-relative links and forms such as `/lectures` and `/lectures/{lecture_id}/upload`.
- admin is a separate FastAPI app, not mounted below the student app.

An Nginx `location /stats/ { proxy_pass ... }` that strips the prefix will still serve HTML containing root-relative URLs. The browser will then request root-level `/static`, `/lectures`, and API paths. That is not a clean `/stats` deployment.

Before deploying at `/stats`, the app should be changed to generate prefix-aware URLs. Likely work includes:

- make static asset URLs and frontend API URLs respect a configured base path or `root_path`
- use `request.url_for(...)` or a shared injected base path in templates
- avoid root-relative admin form actions and links
- decide whether admin is mounted under one combined FastAPI app or proxied as a separate app with a prefix-aware admin base path
- add tests for the `/stats` and `/stats/stats-admin` URL behavior

Until then, either deploy at root or accept an explicit Nginx workaround that exposes root-level aliases for every static/API/admin path. The workaround is operationally fragile and is not recommended as the long-term production shape.

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
