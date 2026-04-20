# Path Prefix Support Change Note

## What changed

The student and admin FastAPI apps now generate browser-facing URLs from FastAPI route names instead of hard-coded root-relative paths.

- `app/templates/chat.html` uses generated static asset URLs.
- `app/templates/chat.html` renders `window.APP_ROUTES` with generated student API URLs.
- `app/static/chat.js` reads all API endpoints from `window.APP_ROUTES`.
- Admin templates use generated URLs for static assets, page links, file downloads, prompt downloads, bundle downloads, and form actions.
- The apps remain separate: student runs as `app.main:app`, admin runs as `app.admin_main:app`.

## Committed default prefixes

The committed defaults live in `app/config.py`:

- student app: `/bot`
- admin app: `/bot-admin`

They are exposed as pydantic settings:

- `LECTURE_BOT_STUDENT_ROOT_PATH`
- `LECTURE_BOT_ADMIN_ROOT_PATH`

Empty values or `/` normalize to root deployment. Values without a leading slash are normalized by adding one.

## Production override

For the intended production deployment, set:

```bash
LECTURE_BOT_STUDENT_ROOT_PATH=/stats
LECTURE_BOT_ADMIN_ROOT_PATH=/stats-admin
```

Launch Uvicorn with matching root paths:

```bash
LECTURE_BOT_STUDENT_ROOT_PATH=/stats pixi run uvicorn app.main:app \
  --host 127.0.0.1 --port 8000 --root-path /stats

LECTURE_BOT_ADMIN_ROOT_PATH=/stats-admin pixi run uvicorn app.admin_main:app \
  --host 127.0.0.1 --port 8001 --root-path /stats-admin
```

The matching setting and Uvicorn `--root-path` are both intentional: the app setting controls generated URLs, and the ASGI root path tells the server/proxy context what public prefix is in use.

## Running repo defaults

Pixi tasks use the committed prefixes:

```bash
pixi run dev
pixi run admin-dev
```

Equivalent explicit commands:

```bash
pixi run uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 --root-path /bot

pixi run uvicorn app.admin_main:app \
  --host 0.0.0.0 --port 8001 --root-path /bot-admin
```

Nginx can proxy:

- `/bot/` to the student process on port `8000`
- `/bot-admin/` to the admin process on port `8001`

## Running the production-style prefixes

Convenience tasks are available for the intended `/stats` deployment shape:

```bash
pixi run stats-dev
pixi run stats-admin-dev
```

Equivalent explicit commands:

```bash
LECTURE_BOT_STUDENT_ROOT_PATH=/stats pixi run uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 --root-path /stats

LECTURE_BOT_ADMIN_ROOT_PATH=/stats-admin pixi run uvicorn app.admin_main:app \
  --host 0.0.0.0 --port 8001 --root-path /stats-admin
```

Nginx can proxy:

- `/stats/` to the student process on port `8000`
- `/stats-admin/` to the admin process on port `8001`

## Caveats

- The student and admin apps are still separate processes/apps.
- The selected `LECTURE_BOT_STUDENT_ROOT_PATH` or `LECTURE_BOT_ADMIN_ROOT_PATH` must be present in the environment before the corresponding app module is imported.
- Keep Uvicorn `--root-path` aligned with the selected setting to avoid mismatched generated URLs and request scope.
- This change does not add deployment automation or Nginx config; it only removes the application-level root-path blocker.
