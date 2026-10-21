# Migrating Statistics into the v0.4 instance layout

A one-time procedure. Until v0.4, the server ran a single course, Statistics, from `/srv/lecture-bot`. That one folder held the code checkout, `.env`, `data/`, `lectures/` and `exports/`, and the services were `lecture-bot` and `lecture-bot-admin`.

This procedure moves Statistics into the layout described in [`deployment_ubuntu.md`](deployment_ubuntu.md#layout):

- the code moves to `/srv/lecture-bot/code/`;
- Statistics' data moves to `/srv/lecture-bot/instances/statistics/`;
- Statistics runs under `lecture-bot@statistics` and `lecture-bot-admin@statistics`.

Its URLs (`/stats`, `/stats-admin`) and ports (8000, 8001) stay the same, so nginx does not change. Nothing is deleted except the old unit files, at the very end. Scope: [#16](https://github.com/opherdonchin/lecture-bot/issues/16).

Statistics is down from step 2 to step 9. Expect about half an hour.

Steps marked **(sudo)** are run by the researcher. The others are run by the deployment user (`<DEPLOY_USER>`, in `appops`).

## 0. Before the window

- v0.4 is merged into `main` and tagged `v0.4.0`.
- The researcher has given the go-ahead for the window.
- On a development machine, `deploy/remote.env` has `LECTURE_BOT_REMOTE_ROOT=/srv/lecture-bot/code` and `LECTURE_BOT_REMOTE_INSTANCES="statistics=/stats"`.
- Confirm that the old checkout is clean and on `main`:

  ```bash
  git -C /srv/lecture-bot status --short --untracked-files=no     # must print nothing
  git -C /srv/lecture-bot rev-parse --abbrev-ref HEAD             # main
  ```

## 1. Back up

```bash
cd /srv/lecture-bot
stamp=$(date +%Y%m%dT%H%M)
mkdir -p ~/lecture-bot-backups
sqlite3 data/lecture_bot.db ".backup '$HOME/lecture-bot-backups/statistics-$stamp.db'"
tar -czf ~/lecture-bot-backups/statistics-$stamp.tar.gz .env data lectures exports "Full grading policy.pdf" statistics_2026_2_grade_calculator.xlsx
chmod 600 ~/lecture-bot-backups/statistics-$stamp.*
```

The backup is private: it contains student data and secrets.

## 2. Stop Statistics and record its state (sudo for the first line)

```bash
sudo systemctl stop lecture-bot.service lecture-bot-admin.service
sqlite3 /srv/lecture-bot/data/lecture_bot.db 'select count(*) from sessions; select session_id, started_at from sessions order by started_at desc limit 1;' | tee ~/lecture-bot-backups/statistics-before.txt
sha256sum /srv/lecture-bot/data/lecture_bot.db | tee -a ~/lecture-bot-backups/statistics-before.txt
```

## 3. Move the checkout (sudo)

```bash
sudo mv /srv/lecture-bot /srv/lecture-bot-v03
sudo install -d -o root -g appops -m 2775 /srv/lecture-bot /srv/lecture-bot/instances
sudo mv /srv/lecture-bot-v03 /srv/lecture-bot/code
sudo install -d -o lecturebot -g appops -m 2770 /srv/lecture-bot/instances/statistics /srv/lecture-bot/instances/statistics/documents
```

## 4. Move Statistics' data out of the checkout (sudo)

```bash
cd /srv/lecture-bot/code
sudo mv data lectures exports /srv/lecture-bot/instances/statistics/
sudo cp -a "Full grading policy.pdf" statistics_2026_2_grade_calculator.xlsx /srv/lecture-bot/instances/statistics/documents/
sudo mv .env /srv/lecture-bot/instances/statistics/legacy.env
git status --short --ignored
```

The two course documents are copied, not moved: they are still tracked at v0.3.0, and step 5's update removes them from the checkout. The last command should list only ignored tool folders such as `.pixi/` and `__pycache__/`. If anything else appears, decide where it belongs before continuing.

## 5. Update the code and rebuild the environment

```bash
cd /srv/lecture-bot/code
git fetch --tags origin
git merge --ff-only v0.4.0
rm -rf .pixi
~/.pixi/bin/pixi install
chgrp -R appops .pixi && chmod -R g+rX .pixi && find .pixi -type d -exec chmod g+rx {} \;
```

The Pixi environment is rebuilt because it records the folder it was installed in.

## 6. Write the instance settings

```bash
cp deploy/instances/statistics.env.example /srv/lecture-bot/instances/statistics/instance.env
chgrp appops /srv/lecture-bot/instances/statistics/instance.env
chmod 640 /srv/lecture-bot/instances/statistics/instance.env
```

Fill in the `<...>` values from `legacy.env` (API key, admin password). Compare every other value with `legacy.env`, and keep the old value wherever the two differ. Then run the settings check from [deployment_ubuntu.md, 2.2](deployment_ubuntu.md#22-settings). Every path must be inside `/srv/lecture-bot/instances/statistics/`.

## 7. Check the data arrived intact

```bash
sha256sum /srv/lecture-bot/instances/statistics/data/lecture_bot.db
sqlite3 /srv/lecture-bot/instances/statistics/data/lecture_bot.db 'select count(*) from sessions; select session_id, started_at from sessions order by started_at desc limit 1;'
```

All three values must match `~/lecture-bot-backups/statistics-before.txt`. Then run `init_db.py` for this instance, as in [deployment_ubuntu.md, 2.3](deployment_ubuntu.md#23-database-and-lectures). It only adds missing columns.

## 8. Logs, units and permission (sudo)

```bash
sudo mv /var/log/lecture-bot/student.log /var/log/lecture-bot/statistics-student.log
sudo mv /var/log/lecture-bot/admin.log /var/log/lecture-bot/statistics-admin.log
sudo cp /srv/lecture-bot/code/deploy/systemd/lecture-bot@.service.example /etc/systemd/system/lecture-bot@.service
sudo cp /srv/lecture-bot/code/deploy/systemd/lecture-bot-admin@.service.example /etc/systemd/system/lecture-bot-admin@.service
sudo systemctl disable lecture-bot.service lecture-bot-admin.service
sudo systemctl daemon-reload
sudo visudo -f /etc/sudoers.d/lecture-bot-statistics
```

In the sudoers file:

```
lecturebot ALL=(root) NOPASSWD: /usr/bin/systemctl restart lecture-bot@statistics.service
<DEPLOY_USER> ALL=(root) NOPASSWD: /usr/bin/systemctl restart lecture-bot@statistics.service lecture-bot-admin@statistics.service
```

## 9. Start and verify (sudo for the first line)

```bash
sudo systemctl enable --now lecture-bot@statistics.service lecture-bot-admin@statistics.service
curl -fsS http://127.0.0.1/stats/health
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1/stats-admin/       # 401
tail -n 50 /var/log/lecture-bot/statistics-student.log
```

Then check in a browser that `/stats-admin/sessions` shows the latest session recorded in step 2. Check that the admin page's restart note names `lecture-bot@statistics.service`, and that its button works.

## 10. Confirm the deploy route

From a development machine:

```bash
pixi run publish-prod -- --dry-run      # should report v0.4.0 and nothing to deploy
pixi run publish-prod -- --revision v0.4.0
```

This exercises the restart permissions and health checks end to end.

## 11. Clean up, after a day without problems (sudo)

```bash
sudo rm /etc/systemd/system/lecture-bot.service /etc/systemd/system/lecture-bot-admin.service
sudo systemctl daemon-reload
```

Remove `legacy.env` once nothing more is needed from it. Keep the backups from step 1 until the next semester starts.

## Rolling back

If Statistics does not come up at step 9 and the problem isn't quickly fixable:

```bash
sudo systemctl disable --now lecture-bot@statistics.service lecture-bot-admin@statistics.service
sudo mv /srv/lecture-bot/instances/statistics/{data,lectures,exports} /srv/lecture-bot/code/
sudo mv /srv/lecture-bot/instances/statistics/legacy.env /srv/lecture-bot/code/.env
sudo mv /var/log/lecture-bot/statistics-student.log /var/log/lecture-bot/student.log
sudo mv /var/log/lecture-bot/statistics-admin.log /var/log/lecture-bot/admin.log
sudo mv /srv/lecture-bot /srv/lecture-bot-v04
sudo mv /srv/lecture-bot-v04/code /srv/lecture-bot
cd /srv/lecture-bot && git reset --hard v0.3.0 && rm -rf .pixi && ~/.pixi/bin/pixi install
sudo systemctl enable --now lecture-bot.service lecture-bot-admin.service
```

The data never leaves the server and is never modified by the migration itself, so a rollback only moves it back.
