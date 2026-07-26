# Making a full local copy on WSL (with secrets)

Production host: `bmed-edu`  →  Local: `opher@DESKTOP-P681IHN:~/Repositories/lecture-bot`

## Status
- Production `/srv/lecture-bot` is committed and pushed to GitHub `origin/main` (clean).
- The sync mechanism is already in git: `scripts/sync_dev_environment.sh` (pixi task `sync-dev`).
- Only `deploy/remote.env` (per-machine, git-ignored) needs to be created on WSL.

## Steps (run on WSL)
```bash
cd ~/Repositories/lecture-bot
git pull origin main                            # 1. GitHub sync down

cp deploy/remote.env.example deploy/remote.env  # 2. create local-only host config
# edit deploy/remote.env:
#   LECTURE_BOT_REMOTE_HOST=<address WSL uses to reach bmed-edu>
#   LECTURE_BOT_REMOTE_USER=opher                # your SSH login; must be in group appops

pixi run sync-dev-dry-run                        # 3. preview transfer (safe)
pixi run sync-dev                                # 4. pull secrets + runtime data
```

## What sync-dev pulls from production
`.env` (-> rewritten as `.env.dev-sync` with dev overrides), `docs/`, `prompts/`,
`data/lecture_bot.db`, `lectures/`, `data/submissions/`, logs — into `.local/dev-sync/`.

Run the local copy with: `pixi run dev-synced` / `pixi run admin-dev-synced`.

## Caveat
This is a runnable dev snapshot, not a byte-identical mirror: DB/lectures/etc. land
under `.local/dev-sync/`, and `.env` becomes `.env.dev-sync`. Ask if you want a true
in-place mirror instead.
