# Deployment runbook — lecture-bot on Ubuntu LTS

This runbook sets up a server that runs one or more **courses**, each as its own **instance**, from one shared code checkout. It covers:

- one-time server setup (Part 1);
- adding a course (Part 2);
- deploying and rolling back code (Part 3);
- day-to-day operations (Part 4).

Moving the original single-course Statistics installation into this layout was a one-time job, described in [`migration_v0.4.md`](migration_v0.4.md).

Background on the terms used here is in the wiki: [services and systemd](https://github.com/opherdonchin/lecture-bot/wiki/Concept-server-services), [nginx as reverse proxy](https://github.com/opherdonchin/lecture-bot/wiki/Concept-reverse-proxy), [deploying with git](https://github.com/opherdonchin/lecture-bot/wiki/Concept-deploying-with-git) and [course instances](https://github.com/opherdonchin/lecture-bot/wiki/Concept-course-instance).

Steps marked **(sudo)** need an account with sudo rights. The others run as the deployment user.

## Placeholders

Replace every placeholder in angle brackets with the value for your deployment:

- `<SERVER_IP>` and `<SERVER_FQDN>`: the server's fixed IP address and the DNS name used in browsers.
- `<DEPLOY_USER>`: the human account that deploys and operates lecture-bot. It must be in the `appops` group.
- `<COURSE>`: an instance name, in lower case, such as `statistics` or `pml`.
- `<PUBLIC_GITHUB_REPO_URL>`: the clone URL of this repository.

## Layout

```text
/srv/lecture-bot/
├── code/                        # git checkout of this repository; no .env, no course data
└── instances/
    ├── statistics/
    │   ├── instance.env         # every setting for this course, including secrets
    │   ├── lectures/            # config.json and one folder per lecture
    │   ├── data/
    │   │   ├── lecture_bot.db
    │   │   └── submissions/     # Moodle participants, deadlines, ZIPs, imports
    │   ├── exports/
    │   └── documents/           # course documents kept on the server (optional)
    └── pml/
        └── ...

/var/log/lecture-bot/
├── statistics-student.log
├── statistics-admin.log
├── pml-student.log
└── pml-admin.log
```

| Instance | Student path | Admin path | Student port | Admin port | Services |
|---|---|---|---|---|---|
| `statistics` | `/stats` | `/stats-admin` | 8000 | 8001 | `lecture-bot@statistics`, `lecture-bot-admin@statistics` |
| `pml` | `/pml` | `/pml-admin` | 8002 | 8003 | `lecture-bot@pml`, `lecture-bot-admin@pml` |

Accounts:

- `lecturebot`: the service account that runs the apps. It has no login shell.
- `<DEPLOY_USER>`: the human operator, in group `appops`.
- `appops`: the shared group. Members can read logs and the database and write exports without becoming the service account.

The apps listen only on `127.0.0.1`. Nginx is the only public-facing service.

**Why the checkout has no `.env`:** the app reads settings from its service's environment first, then from a `.env` file in the folder it runs from. Keeping the checkout free of `.env` means a setting missing from an instance can never be taken from another course. Each `instance.env` must set every setting; `deploy/instances/*.env.example` shows them all, and a test checks that they do.

## Part 1 — One-time server setup

### 1.1 Host check

```bash
hostnamectl
ip addr
getent hosts <SERVER_FQDN> || true
```

If DNS does not resolve yet, continue: it only blocks the final browser URL (see 4.5).

### 1.2 Base packages (sudo)

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y curl git nginx sqlite3 lsof poppler-utils ca-certificates
```

`poppler-utils` provides `pdftotext`, which the admin app uses for PDF handouts.

### 1.3 Group and accounts (sudo)

```bash
sudo addgroup --system appops || true
sudo usermod -aG appops <DEPLOY_USER>
sudo adduser --system --home /home/lecturebot --group --shell /usr/sbin/nologin lecturebot
sudo usermod -aG appops lecturebot
```

The service account is in `appops` so that it can read the checkout and the Pixi environment, which the deployment user manages.

### 1.4 Folders and checkout (sudo, then deploy user)

```bash
sudo install -d -o root -g appops -m 2775 /srv/lecture-bot /srv/lecture-bot/instances
sudo install -d -o <DEPLOY_USER> -g appops -m 2775 /srv/lecture-bot/code
```

As `<DEPLOY_USER>`:

```bash
git clone <PUBLIC_GITHUB_REPO_URL> /srv/lecture-bot/code
chmod -R g+rX /srv/lecture-bot/code
```

The setgid bit (the `2` in `2775`) makes new files inherit the `appops` group.

**Do not edit or commit in `/srv/lecture-bot/code`.** It only ever moves to merged, tagged versions of `main` (Part 3).

### 1.5 Pixi

Install the Pixi binary for the service account (sudo) and for the deployment user:

```bash
sudo -u lecturebot -H bash -lc 'curl -fsSL https://pixi.sh/install.sh | PIXI_VERSION=v0.82.0 bash'
curl -fsSL https://pixi.sh/install.sh | PIXI_VERSION=v0.82.0 bash
```

Build the project environment as `<DEPLOY_USER>`, and make it readable to the service:

```bash
cd /srv/lecture-bot/code
~/.pixi/bin/pixi install --locked
chgrp -R appops .pixi
chmod -R g+rX .pixi
find .pixi -type d -exec chmod g+rx {} \;
```

Both accounts need at least the Pixi version that `pixi.toml` requires (`requires-pixi`); keep them the same, and update both with `pixi self-update --version <version>` when that requirement changes. An older Pixi cannot read the lock file and re-resolves every dependency. The service units run `pixi run --as-is`, so starting a service never installs anything or touches `pixi.lock`.

Non-interactive SSH sessions may not have `~/.pixi/bin` on `PATH`, so these commands use the full path. Set `LECTURE_BOT_REMOTE_PIXI_BIN` in `deploy/remote.env` the same way.

### 1.6 Service units (sudo)

The two systemd **template units** serve every course. `lecture-bot@<COURSE>` reads `/srv/lecture-bot/instances/<COURSE>/instance.env`:

```bash
sudo cp /srv/lecture-bot/code/deploy/systemd/lecture-bot@.service.example /etc/systemd/system/lecture-bot@.service
sudo cp /srv/lecture-bot/code/deploy/systemd/lecture-bot-admin@.service.example /etc/systemd/system/lecture-bot-admin@.service
sudo install -d -o lecturebot -g appops -m 2775 /var/log/lecture-bot
sudo systemctl daemon-reload
```

### 1.7 Nginx site (sudo)

Create `/etc/nginx/sites-available/lecture-bot` from [`deploy/nginx/lecture-bot.conf.example`](../deploy/nginx/lecture-bot.conf.example), keeping only the location blocks for courses that exist, then:

```bash
sudo ln -sfn /etc/nginx/sites-available/lecture-bot /etc/nginx/sites-enabled/lecture-bot
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

Keep both `<SERVER_FQDN>` and `<SERVER_IP>` in `server_name` while DNS is being fixed.

## Part 2 — Adding a course instance

The commands use `pml` as the example. For another course, use its name, its paths and the next free pair of ports.

### 2.1 Instance folder (sudo)

```bash
sudo install -d -o lecturebot -g appops -m 2770 \
  /srv/lecture-bot/instances/pml \
  /srv/lecture-bot/instances/pml/lectures \
  /srv/lecture-bot/instances/pml/data \
  /srv/lecture-bot/instances/pml/data/submissions \
  /srv/lecture-bot/instances/pml/exports
```

### 2.2 Settings

If the course has no `deploy/instances/<COURSE>.env.example` yet, add one through a pull request. Copy an existing example and change every path, port, URL path and service name. The instance-example tests check that it is complete and does not collide with another course.

Then, as `<DEPLOY_USER>`:

```bash
cp /srv/lecture-bot/code/deploy/instances/pml.env.example /srv/lecture-bot/instances/pml/instance.env
chgrp appops /srv/lecture-bot/instances/pml/instance.env
chmod 640 /srv/lecture-bot/instances/pml/instance.env
nano /srv/lecture-bot/instances/pml/instance.env      # fill in every <...>
```

Check what the instance will actually use:

```bash
cd /srv/lecture-bot/code
( set -a; source /srv/lecture-bot/instances/pml/instance.env; set +a
  ~/.pixi/bin/pixi run python -c "import app.config as c; s = c.get_settings(); print(s.database_url, s.lectures_dir, s.moodle_submissions_dir, s.student_root_path, s.admin_root_path, s.admin_username, s.student_restart_command, sep='\n')" )
```

Every path must be inside `/srv/lecture-bot/instances/pml/`.

After any later edit to `instance.env`, restart the course's services: `sudo systemctl restart lecture-bot@pml lecture-bot-admin@pml`.

### 2.3 Database and lectures

```bash
cd /srv/lecture-bot/code
( umask 007; set -a; source /srv/lecture-bot/instances/pml/instance.env; set +a
  ~/.pixi/bin/pixi run python scripts/init_db.py )
sqlite3 /srv/lecture-bot/instances/pml/data/lecture_bot.db ".tables"
```

Put the course's `lectures/config.json` and lecture folders in `/srv/lecture-bot/instances/pml/lectures/`. `example_content/` in the checkout is a working starting point. Lecture packages are private course material: copy them in directly, never through git. New lectures should start with `"active": false` in their `lecture_config.json` until they have been reviewed and piloted.

### 2.4 Logs, restart permission and Nginx (sudo)

```bash
sudo install -o lecturebot -g appops -m 0660 /dev/null /var/log/lecture-bot/pml-student.log
sudo install -o lecturebot -g appops -m 0660 /dev/null /var/log/lecture-bot/pml-admin.log
```

The admin app's **Restart Student App** button, and `publish-prod`, restart services with `sudo -n`, which works only for commands a sudoers rule allows without a password. Run `sudo visudo -f /etc/sudoers.d/lecture-bot-pml` and enter:

```
lecturebot ALL=(root) NOPASSWD: /usr/bin/systemctl restart lecture-bot@pml.service
<DEPLOY_USER> ALL=(root) NOPASSWD: /usr/bin/systemctl restart lecture-bot@pml.service lecture-bot-admin@pml.service
```

Each line allows exactly one command, with exactly those arguments.

Add the course's two location pairs from [`deploy/nginx/lecture-bot.conf.example`](../deploy/nginx/lecture-bot.conf.example) inside the `server` block of `/etc/nginx/sites-available/lecture-bot`, then:

```bash
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl enable --now lecture-bot@pml.service lecture-bot-admin@pml.service
```

### 2.5 Verify

```bash
systemctl status lecture-bot@pml lecture-bot-admin@pml --no-pager
curl -fsS http://127.0.0.1/pml/health
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1/pml-admin/      # 401 without credentials
curl -s -o /dev/null -w '%{http_code}\n' -u '<ADMIN_USERNAME>:<ADMIN_PASSWORD>' http://127.0.0.1/pml-admin/   # 200
sudo -u lecturebot sudo -n /usr/bin/systemctl restart lecture-bot@pml.service   # the admin button's permission
tail -n 50 /var/log/lecture-bot/pml-student.log
```

Use `GET` (plain `curl`), not `curl -I`: `HEAD` requests can return a misleading `405`.

**Isolation check.** Record every other course's database before and after a test session on the new course; both values must be unchanged:

```bash
sqlite3 /srv/lecture-bot/instances/statistics/data/lecture_bot.db 'select count(*) from sessions;'
sha256sum /srv/lecture-bot/instances/statistics/data/lecture_bot.db
```

**OpenAI check,** with the instance's own key and model:

```bash
cd /srv/lecture-bot/code
( set -a; source /srv/lecture-bot/instances/pml/instance.env; set +a
  ~/.pixi/bin/pixi run python - <<'PY'
import os
import openai
client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=30.0, max_retries=0)
resp = client.chat.completions.create(
    model=os.environ["OPENAI_MODEL"],
    messages=[{"role": "user", "content": "Reply with valid JSON only: {\"ok\": true}"}],
    response_format={"type": "json_object"},
)
print(resp.choices[0].message.content)
PY
)
```

Then do one real session in a browser: start a session, send messages, and check that the current grade and the final report work. A wrong key makes the tutor fall back quietly rather than crash, so watch the student log while you do this.

### 2.6 Include the course in deploys

On each development machine, add the course to `LECTURE_BOT_REMOTE_INSTANCES` in `deploy/remote.env`, for example `LECTURE_BOT_REMOTE_INSTANCES="statistics=/stats pml=/pml"`. `publish-prod` then restarts and checks it.

## Part 3 — Deploying and rolling back

Production runs merged code from `main`, at a release tag (such as `v0.4.0`). Code reaches `main` only through reviewed pull requests; nobody edits files in `/srv/lecture-bot/code`.

From a development machine with `deploy/remote.env` configured (see [`deploy/remote.env.example`](../deploy/remote.env.example)):

```bash
pixi run publish-prod -- --dry-run      # the server's current commit, and what would be deployed
pixi run publish-prod                   # deploy the newest origin/main
pixi run publish-prod -- --revision v0.4.0   # deploy, or roll back to, a specific tag or commit
```

On the server, `publish-prod`:

1. refuses to run if tracked files in the checkout have been changed, or if the checkout is not on `main`;
2. fetches, then fast-forwards to `origin/main`, or resets to `--revision`;
3. runs `pixi install --locked`, which installs exactly what `pixi.lock` lists, and repairs the `.pixi` group permissions;
4. restarts each listed course and checks its `/health` and admin URL.

It never copies files from the development machine. Untracked files on the server, including all instance data, cannot be touched. It prints the previous commit, and if a check fails it prints the command that rolls back.

The deploy user needs a sudoers rule for each course's restart command (2.4).

## Part 4 — Operations

### 4.1 Logs

```bash
tail -n 200 /var/log/lecture-bot/<COURSE>-student.log
tail -n 200 /var/log/lecture-bot/<COURSE>-admin.log
systemctl status lecture-bot@<COURSE> --no-pager       # process state and restarts
```

### 4.2 Session review and exports

The admin Sessions page (`/<path>-admin/sessions`) filters sessions by student, lecture, date, turn count and grade, and downloads the selected sessions as one ZIP.

The command-line scripts still default to folders inside the checkout, so pass the instance's paths explicitly:

```bash
cd /srv/lecture-bot/code
~/.pixi/bin/pixi run python scripts/list_sessions.py --database /srv/lecture-bot/instances/<COURSE>/data/lecture_bot.db --limit 50
```

Exports can contain student content, private lecture material and grades. Keep them in the instance's `exports/`. Moodle grade uploads follow [`moodle_grade_upload_runbook.md`](moodle_grade_upload_runbook.md).

### 4.3 Backups

Before a migration or any risky change, copy the database with SQLite's own backup command, which is safe while the app runs:

```bash
sqlite3 /srv/lecture-bot/instances/<COURSE>/data/lecture_bot.db ".backup '/srv/lecture-bot/instances/<COURSE>/data/lecture_bot.$(date +%Y%m%dT%H%M).bak.db'"
```

A wider backup policy is [issue #5](https://github.com/opherdonchin/lecture-bot/issues/5).

### 4.4 Reboot test

Before announcing a course to students, reboot (`sudo reboot`), then check every course's services, logs and health URLs as in 2.5.

### 4.5 DNS

Final student-facing use should be by hostname. Ask IT to create or verify the DNS record `<SERVER_FQDN> -> <SERVER_IP>`, and to confirm that the IP address is fixed.

### 4.6 What counts as student-ready

A course is student-ready when all of these are true:

- `http://<SERVER_FQDN>/<path>/` and `/<path>-admin/` load through Nginx inside the VPN;
- its lectures are present and the active ones have been reviewed;
- the OpenAI check and one real session (grade and report) work;
- the isolation check passed;
- its services survive a reboot.
