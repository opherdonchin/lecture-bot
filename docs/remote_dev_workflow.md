# Remote Development Workflow

This workflow treats the repository on your Linux workstation as the development environment and the server as a source of current operational state plus a deployment target.

## Goal

The intended cycle is:

1. Clone or update the repo on a local Linux machine.
2. Run one Pixi command to pull the current server state needed for development.
3. Work locally.
4. Run one Pixi command to publish code and content changes back to the server safely.

This avoids day-to-day development inside the deployed server checkout.

## Local Setup

Copy [deploy/remote.env.example](../deploy/remote.env.example) to `deploy/remote.env` on your local machine and fill in the SSH and remote-path values.

Required variables:

- `LECTURE_BOT_REMOTE_HOST`
- `LECTURE_BOT_REMOTE_USER`

Useful defaults already match the current production layout:

- `LECTURE_BOT_REMOTE_ROOT=/srv/lecture-bot`
- `LECTURE_BOT_REMOTE_PIXI_BIN=/home/lecturebot/.pixi/bin/pixi`
- `LECTURE_BOT_REMOTE_LOG_DIR=/var/log/lecture-bot`
- `LECTURE_BOT_REMOTE_STUDENT_SERVICE=lecture-bot`
- `LECTURE_BOT_REMOTE_ADMIN_SERVICE=lecture-bot-admin`

`LECTURE_BOT_REMOTE_REPO_PATH` is also accepted as a backward-compatible alias for `LECTURE_BOT_REMOTE_ROOT`.

Optional:

- `LECTURE_BOT_REMOTE_SSH_OPTS` for extra ssh flags such as `-i ~/.ssh/lecture-bot_ed25519`

## Pull Current Server State

Run:

```bash
pixi run sync-dev
```

This pulls current canonical prompt/spec files into the repo plus runtime state into a local snapshot under `.local/dev-sync/` by default:

- remote `.env` into `.local/dev-sync/remote.env`
- remote `docs/` into repo-root `docs/`
- remote `prompts/` into repo-root `prompts/`
- remote `lectures/` into `.local/dev-sync/lectures/`
- remote `data/submissions/` into `.local/dev-sync/data/submissions/`
- remote `data/lecture_bot.db` into `.local/dev-sync/data/lecture_bot.db`
- remote service logs into `.local/dev-sync/logs/`

It also writes a repo-root `.env.dev-sync` that points the app at that local snapshot.

Because the runtime snapshot lives under `.local/`, database, lecture-content, submission, and log syncs stay out of the tracked repo. The prompt/spec sync does update the tracked canonical files in `docs/` and `prompts/`, because that is what the current app runtime reads.

To preview without changing anything:

```bash
pixi run sync-dev-dry-run
```

## Work Locally

After sync, install dependencies if needed and run the local app against the synced environment:

```bash
pixi install
pixi run dev-synced
pixi run admin-dev-synced
```

Because `.env.dev-sync` points at the synced prompts, docs, lectures, submissions, and database, the app can mimic current production behavior without editing the server checkout.

## Publish Back To The Server

Run:

```bash
pixi run publish-prod
```

This command:

1. Rsyncs the local repo to the remote repo path.
2. Excludes mutable production state such as `.env`, `.pixi`, `data/*.db`, and `exports/`.
3. Runs remote `pixi install`.
4. Repairs shared `.pixi` permissions for the `appops` group.
5. Restarts the student and admin systemd services.
6. Verifies both services are active and that the backend ports are listening.
7. Verifies the student health endpoint locally on the server.

To preview without changing anything:

```bash
pixi run publish-prod-dry-run
```

## Remote sudo requirement

The publish command uses `sudo -n` on the remote machine for the service restart and status checks. The remote deployment user therefore needs passwordless sudo for the exact `systemctl` commands involved.

If that is not configured, the rsync phase can still succeed, but the publish command will stop before restart with a clear error.

## What This Does Not Publish

The publish command is intentionally conservative. It does not push:

- `.env`
- `.pixi/`
- SQLite database files
- exported session bundles
- locally synced server logs
- local snapshot directories under `.local/`

That preserves production session history, dialogue logs, notes, grades, and other archival runtime state on the server.