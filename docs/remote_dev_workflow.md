# Remote Development Workflow

This workflow treats the repository on your Linux workstation as the development environment and the server as a source of current operational state plus a deployment target.

## Goal

The intended cycle is:

1. Clone or update the repo on a local Linux machine.
2. Run one Pixi command to pull the current server state needed for development.
3. Work locally.
4. Deploy merged code to the server with one Pixi command.

This avoids day-to-day development inside the deployed server checkout.

## Local Setup

Copy [deploy/remote.env.example](../deploy/remote.env.example) to `deploy/remote.env` on your local machine and fill in the SSH and remote-path values.

Required variables:

- `LECTURE_BOT_REMOTE_HOST`
- `LECTURE_BOT_REMOTE_USER`

For deploying (`publish-prod`), set also:

- `LECTURE_BOT_REMOTE_ROOT=/srv/lecture-bot/code` (the default)
- `LECTURE_BOT_REMOTE_PIXI_BIN=/home/<DEPLOY_USER>/.pixi/bin/pixi`
- `LECTURE_BOT_REMOTE_INSTANCES="statistics=/stats pml=/pml"`

**`sync-dev` still expects the single-course layout**, where data and lectures sit inside the checkout. It does not work against the instance layout until [scope issue #16, PR 2c](https://github.com/opherdonchin/lecture-bot/issues/16#user-content-pr-2c) makes it instance-aware. Until then, copy an instance's data with `rsync` from `/srv/lecture-bot/instances/<course>/` into `~/lecture-bot-instances/<course>/`.

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

## Deploy To The Server

Code reaches the server only through merged `main`; this machine's working tree is never copied. After a pull request is merged, run:

```bash
pixi run publish-prod-dry-run
pixi run publish-prod
```

On the server, this refuses to run if the checkout has local changes or is not on `main`, fast-forwards to `origin/main`, runs `pixi install`, restarts each course instance's services and checks their health. It prints the previous commit; `pixi run publish-prod -- --revision <commit>` rolls back to it. The steps, and the sudoers rules the restart needs, are in [deployment_ubuntu.md](deployment_ubuntu.md#part-3--deploying-and-rolling-back).

Lecture packages, databases, Moodle files and exports are instance data and are never deployed through git.
