# Deployment runbook — lecture-bot on Ubuntu LTS

> Replace every placeholder in angle brackets, such as `<SERVER_FQDN>` and `<SERVER_IP>`, with values for your own deployment. The expected deployment SSH user is `lecture-bot`.

This runbook assumes:

- server OS: **Ubuntu LTS** (tested in practice on Ubuntu 22.04 LTS; expected to work similarly on 24.04 LTS)
- SSH currently works by IP (`<SERVER_IP>`)
- browser access should ultimately be by DNS name (`<SERVER_FQDN>`)
- student app path: `/stats`
- admin app path: `/stats-admin`
- repo checkout location: `/srv/lecture-bot`
- simple layout: code, `.env`, database, and lecture packages all live under `/srv/lecture-bot`
- startup uses the committed repo scripts and Pixi tasks:
  - `pixi run serve`
  - `pixi run admin-serve`
- `<SERVER_IP>`: the fixed IP address of the new Ubuntu server
- `<SERVER_FQDN>`: the DNS name students and staff should use in a browser
- `<BOOTSTRAP_USER>`: the existing SSH user that can already log in to the VM before `lecture-bot` is created
- `<TA_UNIX_USER>`: an optional additional Linux account for a teaching assistant or operator
- `<PUBLIC_GITHUB_REPO_URL>`: the clone URL for this public lecture-bot repository
- `<REAL_OPENAI_API_KEY>`: the production OpenAI API key used by the app
- `<REAL_OPENAI_MODEL>`: the OpenAI model name to use in production
- `<REAL_ADMIN_USERNAME>`: the admin username for the deployed admin app
- `<REAL_ADMIN_PASSWORD>`: the admin password for the deployed admin app
- `<OLD_SERVER_USER>`: the SSH user on the old server when copying existing private lecture material
- `<OLD_SERVER_IP>`: the IP address or hostname of the old server when copying existing private lecture material
- `<OLD_PRIVATE_CLONE_PATH>`: the path on the old server whose `lectures/` directory contains the private lecture packages

## 0. One-time choices locked in

Use this layout:

```text
/srv/lecture-bot/
├─ .env
├─ app/
├─ data/
│  └─ lecture_bot.db
├─ lectures/
│  ├─ config.json
│  └─ <lecture folders>
├─ scripts/
│  ├─ serve_student.sh
│  └─ serve_admin.sh
└─ ... repo files ...
```

Service/user model:

- bootstrap SSH user already present on the VM: `<BOOTSTRAP_USER>`
- primary deployment SSH user: `lecture-bot`
- optional other operator users: `<TA_UNIX_USER>`, sysop, etc.
- service user: `lecturebot`
- main group for shared repo operations: `appops`

Network model:

- student app listens locally on `127.0.0.1:8000`
- admin app listens locally on `127.0.0.1:8001`
- Nginx is the only public-facing service

## 1. First login and host sanity check

SSH in by IP using the bootstrap account.

Run:

```bash
hostnamectl
hostname -f || true
ip addr
getent hosts <SERVER_FQDN> || true
```

What you want to know:

- does `<SERVER_FQDN>` resolve on the server?
- if so, does it resolve to the new server?
- what hostname the machine thinks it has

If DNS does not yet resolve correctly, that does **not** block the rest of setup. It only blocks the final browser URL.

## 2. Base packages

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y curl git nginx sqlite3 lsof poppler-utils ca-certificates rsync
```

`poppler-utils` is included because admin-side PDF text conversion uses `pdftotext`.
`rsync` is included because it is the cleanest first-pass way to copy private lecture material from an older server.

## 3. Create the human deployment user and SSH access

Create the shared group first:

```bash
sudo addgroup --system appops || true
```

Create your primary deployment user:

```bash
sudo adduser lecture-bot
sudo usermod -aG appops lecture-bot
sudo usermod -aG sudo lecture-bot
```

Install an SSH key for `lecture-bot` and verify you can log in directly as that user.

After this point:

- use `<BOOTSTRAP_USER>` only as a fallback/bootstrap account
- do actual deployment work as `lecture-bot`
- use `sudo` from `lecture-bot` when needed

## 4. Create the service user

```bash
sudo adduser --system --home /home/lecturebot --group --shell /usr/sbin/nologin lecturebot
sudo usermod -aG appops lecturebot
```

Why add `lecturebot` to `appops`:

- the repo will be human-managed under the `appops` group
- the service still needs read access to repo files and the built Pixi environment

## 5. Create the main deployment directory

Run as `lecture-bot`:

```bash
sudo mkdir -p /srv/lecture-bot
sudo chown lecture-bot:appops /srv/lecture-bot
sudo chmod 2775 /srv/lecture-bot
```

This simple layout worked better in practice than making `/srv/lecture-bot` root-owned.

## 6. Clone the public repo

Clone as your normal user, not as root and not as the service user.

```bash
git clone <PUBLIC_GITHUB_REPO_URL> /srv/lecture-bot
cd /srv/lecture-bot
sudo chgrp -R appops /srv/lecture-bot
sudo chmod -R g+rX /srv/lecture-bot
sudo find /srv/lecture-bot/.git -type d -exec chmod g+rx {} \;
sudo find /srv/lecture-bot/.git -type f -exec chmod g+r {} \;
```

## 7. Create runtime directories inside the repo

```bash
cd /srv/lecture-bot
sudo mkdir -p data lectures exports
sudo chown -R lecturebot:lecturebot data exports
sudo chown -R lecturebot:appops lectures
sudo chmod -R u=rwX,g=rX,o= data exports
sudo chmod -R u=rwX,g=rwX,o= lectures
```

Why these permissions:

- `data/` and `exports/` are private runtime state for the service
- `lectures/` is writable by the service and also accessible to course operators when they need to copy or inspect lecture packages manually

## 8. Install Pixi

Install the **Pixi binary** for the service user:

```bash
sudo -u lecturebot -H bash -lc 'curl -fsSL https://pixi.sh/install.sh | bash'
```

Then build the **project environment** as `lecture-bot`:

```bash
cd /srv/lecture-bot
pixi install
```

Then make the built project environment readable to the service through `appops`:

```bash
chgrp -R appops /srv/lecture-bot/.pixi
chmod -R g+rX /srv/lecture-bot/.pixi
find /srv/lecture-bot/.pixi -type d -exec chmod g+rx {} \;
```

This worked better in practice than trying to run `pixi install` as the `lecturebot` service account inside an `appops`-managed repo.

## 9. Create the production `.env`

Start from the committed example **as `lecture-bot`**:

```bash
cd /srv/lecture-bot
cp .env.example .env
chgrp appops .env
chmod 640 .env
```

Edit it:

```bash
nano /srv/lecture-bot/.env
```

Use this production-oriented content as the initial template:

```env
APP_NAME=lecture-bot
APP_ENV=prod

OPENAI_API_KEY=<REAL_OPENAI_API_KEY>
OPENAI_MODEL=<REAL_OPENAI_MODEL>

DATABASE_URL=sqlite:///data/lecture_bot.db
LECTURES_DIR=lectures

ADMIN_USERNAME=<REAL_ADMIN_USERNAME>
ADMIN_PASSWORD=<REAL_ADMIN_PASSWORD>

LECTURE_BOT_STUDENT_ROOT_PATH=/stats
LECTURE_BOT_ADMIN_ROOT_PATH=/stats-admin

SESSION_TIMEOUT_MINUTES=20
SESSION_WARNING_MINUTES=5
RECENT_MESSAGE_LIMIT=10
MAX_DIALOGUE_CONTEXT_CHARS=45000
MAX_GRADING_CONTEXT_CHARS=70000
SAMPLED_TOPIC_COUNT=5
OPENING_TOPIC_CHOICE_COUNT=3
```

Important consequence of this simple layout:

- the `.env` lives in the repo root for simplicity
- it must never be committed
- operators who need to change it will do so via the normal deployment user
- **after any edit to `.env`, restart the affected services**

```bash
sudo systemctl restart lecture-bot
sudo systemctl restart lecture-bot-admin
```

## 10. Copy in private lecture material

The public repo only contains the lecture scaffold. Copy the actual private lecture folders into `/srv/lecture-bot/lectures/`.

For first deployment, `rsync` is the cleanest method.

Example pull from the old server:

```bash
rsync -av --no-owner --no-group --progress <OLD_SERVER_USER>@<OLD_SERVER_IP>:<OLD_PRIVATE_CLONE_PATH>/lectures/ /srv/lecture-bot/lectures/
```

Then fix ownership:

```bash
sudo chown -R lecturebot:appops /srv/lecture-bot/lectures
sudo chmod -R u=rwX,g=rwX,o= /srv/lecture-bot/lectures
```

The `--no-owner --no-group` flags avoid noisy attribute-preservation warnings during a non-root copy.

## 11. Initialize the database

Run **as the service user**, with `.env` exported into the shell:

```bash
sudo -u lecturebot -H bash -lc '
  cd /srv/lecture-bot
  set -a
  source .env
  set +a
  /home/lecturebot/.pixi/bin/pixi run init-db
'
```

Then verify with `sudo`, since `data/` is intentionally private to the service:

```bash
sudo ls -l /srv/lecture-bot/data
sudo sqlite3 /srv/lecture-bot/data/lecture_bot.db ".tables"
```

## 12. Run both apps manually before creating services

This is the most important early gate.

### Important rule before systemd

Before enabling the systemd units later, make sure any manually started student/admin server processes have been stopped and ports 8000/8001 are free.

Useful checks:

```bash
sudo lsof -iTCP:8000 -sTCP:LISTEN -n -P
sudo lsof -iTCP:8001 -sTCP:LISTEN -n -P
```

### Student app

In one terminal:

```bash
sudo -u lecturebot -H bash -lc '
  cd /srv/lecture-bot
  set -a
  source .env
  set +a
  /home/lecturebot/.pixi/bin/pixi run serve
'
```

In another terminal:

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/
```

### Admin app

In one terminal:

```bash
sudo -u lecturebot -H bash -lc '
  cd /srv/lecture-bot
  set -a
  source .env
  set +a
  /home/lecturebot/.pixi/bin/pixi run admin-serve
'
```

In another terminal:

```bash
curl -i -u '<REAL_ADMIN_USERNAME>:<REAL_ADMIN_PASSWORD>' http://127.0.0.1:8001/
```

If either of these manual starts fails, stop and fix that before touching systemd or Nginx.

## 13. Run the test suite

As `lecture-bot`:

```bash
cd /srv/lecture-bot
set -a
source .env
set +a
pixi run test
```

Passing tests are necessary, but not sufficient. They do **not** prove that:

- the real OpenAI key works
- DNS is correct
- Nginx is correct
- the private lecture files are correct

## 14. Create systemd services

You may use the committed examples as a base:

```bash
sudo cp /srv/lecture-bot/deploy/systemd/lecture-bot.service.example /etc/systemd/system/lecture-bot.service
sudo cp /srv/lecture-bot/deploy/systemd/lecture-bot-admin.service.example /etc/systemd/system/lecture-bot-admin.service
```

But verify that the final files match the real server exactly.

A clean final version for the student app is:

```ini
[Unit]
Description=Lecture Bot student app
After=network.target

[Service]
User=lecturebot
Group=lecturebot
WorkingDirectory=/srv/lecture-bot
EnvironmentFile=/srv/lecture-bot/.env
ExecStart=/home/lecturebot/.pixi/bin/pixi run serve
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

A clean final version for the admin app is:

```ini
[Unit]
Description=Lecture Bot admin app
After=network.target

[Service]
User=lecturebot
Group=lecturebot
WorkingDirectory=/srv/lecture-bot
EnvironmentFile=/srv/lecture-bot/.env
ExecStart=/home/lecturebot/.pixi/bin/pixi run admin-serve
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then enable them:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now lecture-bot.service
sudo systemctl enable --now lecture-bot-admin.service
```

Check them:

```bash
sudo systemctl status lecture-bot.service --no-pager -l
sudo systemctl status lecture-bot-admin.service --no-pager -l
journalctl -u lecture-bot.service -n 100 --no-pager
journalctl -u lecture-bot-admin.service -n 100 --no-pager
```

## 15. Configure Nginx

Create `/etc/nginx/sites-available/lecture-bot`:

```nginx
server {
    listen 80;
    server_name <SERVER_FQDN> <SERVER_IP>;

    client_max_body_size 100M;

    location = /stats {
        return 301 /stats/;
    }

    location /stats/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    location = /stats-admin {
        return 301 /stats-admin/;
    }

    location /stats-admin/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

Enable it:

```bash
sudo ln -sfn /etc/nginx/sites-available/lecture-bot /etc/nginx/sites-enabled/lecture-bot
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

Including both `<SERVER_FQDN>` and `<SERVER_IP>` in `server_name` is helpful while DNS is still being fixed.

## 16. Check local reverse-proxy behavior before using the browser

From the server itself:

```bash
curl -i -H 'Host: <SERVER_FQDN>' http://127.0.0.1/stats/health
curl -i -H 'Host: <SERVER_FQDN>' http://127.0.0.1/stats/
curl -i -u '<REAL_ADMIN_USERNAME>:<REAL_ADMIN_PASSWORD>' -H 'Host: <SERVER_FQDN>' http://127.0.0.1/stats-admin/
```

Use `GET`, not `HEAD`, for these checks. `curl -I` can give misleading `405 Method Not Allowed` results on endpoints that only implement `GET`.

If these fail while the services themselves are healthy, the problem is in Nginx, not the Python app.

## 17. Browser smoke test inside the VPN

Now open these in a browser inside the VPN:

- `http://<SERVER_IP>/stats/`
- `http://<SERVER_IP>/stats-admin/`

Once DNS is working, also test:

- `http://<SERVER_FQDN>/stats/`
- `http://<SERVER_FQDN>/stats-admin/`

Student checks:

1. page loads correctly
2. CSS/JS load
3. lecture list appears
4. session starts
5. a real message can be sent
6. current grade works
7. final report works

Admin checks:

1. login prompt/page works
2. admin login succeeds
3. lecture list is visible
4. upload/build actions render properly

## 18. Direct OpenAI smoke test

Before declaring the system ready, verify that the server can make a real structured OpenAI call using the deployed `.env`.

```bash
sudo -u lecturebot -H bash -lc '
  cd /srv/lecture-bot
  set -a
  source .env
  set +a
  /home/lecturebot/.pixi/bin/pixi run python - <<'"'"'PY'"'"'
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=30.0, max_retries=0)
resp = client.chat.completions.create(
    model=os.environ["OPENAI_MODEL"],
    messages=[{"role": "user", "content": "Reply with valid JSON only: {\"ok\": true}"}],
    response_format={"type": "json_object"},
    temperature=0,
)
print(resp.choices[0].message.content)
PY
'
```

If this fails, fix `.env` and **restart the student service** before testing the app again.

## 19. Real OpenAI-backed smoke test

Do one genuine end-to-end session using one of the real lectures.

Confirm all of these:

- the model replies sensibly
- no API/auth errors appear in journald logs
- grade endpoint works
- report endpoint works

Watch logs while doing it:

```bash
journalctl -u lecture-bot.service -f
```

This is important because a wrong key can cause the tutor to fall back gracefully without crashing the whole service.

## 20. DNS / IT follow-up

Deployment can proceed by IP, but final student-facing use should be by hostname.

Ask the responsible IT/DNS team to:

- create or verify the DNS A record  
  `<SERVER_FQDN> -> <SERVER_IP>`
- confirm that `<SERVER_IP>` is reserved/fixed for the VM rather than a temporary lease

Useful checks:

```bash
getent hosts <SERVER_FQDN>
```

and from your own machine:

```bash
nslookup <SERVER_FQDN>
```

## 21. Reboot test

Before announcing the system to students:

```bash
sudo reboot
```

After reboot, verify:

```bash
sudo systemctl status lecture-bot.service --no-pager
sudo systemctl status lecture-bot-admin.service --no-pager
curl -i -H 'Host: <SERVER_FQDN>' http://127.0.0.1/stats/health
curl -i -u '<REAL_ADMIN_USERNAME>:<REAL_ADMIN_PASSWORD>' -H 'Host: <SERVER_FQDN>' http://127.0.0.1/stats-admin/
```

## 22. What counts as student-ready

The deployment is student-ready only if all of these are true:

- `<SERVER_FQDN>` resolves correctly inside the VPN
- `http://<SERVER_FQDN>/stats/` loads through Nginx
- `http://<SERVER_FQDN>/stats-admin/` loads through Nginx
- the real lecture packages are present
- `pixi run test` passes
- the direct OpenAI smoke test succeeds
- one real OpenAI-backed session works
- current grade works
- final report works
- both services survive reboot

## 23. First-update procedure

When you want to update the code later:

```bash
cd /srv/lecture-bot
sudo systemctl stop lecture-bot.service lecture-bot-admin.service
git pull origin main
pixi install
sudo systemctl start lecture-bot.service lecture-bot-admin.service
set -a
source .env
set +a
pixi run test
```

If the code update includes changes to the private lecture packages, sync those too before restarting.

