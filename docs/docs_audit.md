# Documentation Audit

Date: 2026-04-20

Update: the path-prefix blocker identified in this audit has since been addressed. See `docs/path_prefix_change_note.md` for the current `/bot`, `/bot-admin`, `/stats`, and `/stats-admin` behavior.

## Scope

This audit checked the current repository against the operational claims in the docs, focusing on:

- README status claims
- OpenAI-backed behavior
- admin UI behavior
- production launch commands
- Ubuntu deployment assumptions
- intended `/stats` and `/stats-admin` paths
- runtime files and private material
- tests and lecture-package flow

## Stale Or Misleading Prior Claims

### README claimed OpenAI was pending

Prior README text said:

- `OpenAI for bot responses and grading (integration pending)`
- `Bot stub (echo responses)`
- `OpenAI integration` unchecked
- `Grading logic` unchecked

Current code does not match that. `app/bot_engine.py` calls OpenAI for tutoring replies and report text, with fallback behavior on API/auth/parse failures. `app/main.py` computes authoritative current grades from backend session state and records grade/report events.

### README listed a non-existent `pixi run build-lecture` task

`pixi.toml` does not define a `build-lecture` task. The actual current command is:

```bash
pixi run python scripts/build_lecture_package.py <lecture_id> --force
```

The README now documents the command that exists today.

### Admin UI was treated as future or under-described

`docs/implementation_spec.md` listed Admin UI as a future extension, but the repo has a working separate admin app:

- `app/admin_main.py`
- `app/admin_workflow.py`
- templates in `app/templates/admin_*.html`
- tests in `tests/test_admin_app.py`

The README now documents admin routes, Basic Auth configuration, upload behavior, source selection, local build, prompt/bundle download, generated artifact upload, and topic refresh behavior.

### Deployment docs implied Fedora-only assumptions

Older docs mentioned Fedora as the deployment server. The target is now clean Ubuntu 24.04 LTS. The README points to the new Ubuntu deployment doc, and `docs/deployment_ubuntu.md` gives Ubuntu package, Pixi, systemd, Nginx, filesystem, and smoke-check guidance.

### `/stats` support was unclear

At the time of this audit, the code assumed root-relative URLs:

- `app/templates/chat.html` links `/static/style.css` and `/static/chat.js`
- `app/static/chat.js` fetches root paths such as `/lectures` and `/send_message`
- admin templates use root-relative links/forms such as `/lectures`
- the admin app is not mounted under the student app

That blocker has since been fixed with prefix-aware URL generation and configurable root-path settings.

### Tests were not described precisely

The README now states that tests mock OpenAI calls, use temporary SQLite databases and fixture lecture packages, and do not prove real API credentials, Nginx/systemd deployment, `/stats` routing, or Moodle end-to-end behavior.

## Documentation Changed

- `README.md`
  - Rewritten as the current operational overview.
  - Updated status from pending/stub to current OpenAI-backed and backend-graded behavior.
  - Added current commands, routes, environment variables, admin behavior, lecture-package flow, runtime filesystem notes, public/private split, path-prefix status, and test coverage.

- `docs/deployment_ubuntu.md`
  - Added dedicated Ubuntu 24.04 deployment guidance.
  - Updated production launch guidance to use committed Pixi startup tasks and example systemd unit templates.
  - Documented Nginx shape and `/stats` prefix deployment.
  - Documented persistent filesystem layout and smoke checks.

- `docs/docs_audit.md`
  - Added this audit note.

- `docs/project_plan.md`
  - Updated infrastructure assumptions from Fedora-only to current Ubuntu target.

- `docs/implementation_spec.md`
  - Updated deployment wording and Admin UI status so the spec no longer calls admin purely future work.

- `docs/implementation_plan.md`
  - Marked the OpenAI integration plan as historical/completed instead of current pending work.

- `docs/grading_policy.md`
  - Aligned the cross-topic weighting table with the code's current five-topic weights: 55, 25, 13, 4, 3.

## Remaining Uncertainties

- Production Pixi tasks and systemd unit templates are now committed; the docs no longer rely on direct production Uvicorn commands.
- I did not inspect private `.env` values. The docs list variable names and purposes only.
- Moodle grading behavior was not audited end to end; only the presence of `scripts/grade_moodle.py` and the configured Pixi task were noted.
- Root-level `app.log` and `admin.log` are tracked legacy/dev log files. Production should prefer journald or private log paths and should not write sensitive runtime logs into tracked files.

## Validation

- `git diff --check`
- `pixi run test` -> `114 passed`

## `/stats` Deployment Blockers

The intended public paths are not currently supported cleanly by the app. Code changes are still needed before the deployment can be truthfully documented as `/stats`-ready:

- Replace root-relative student template asset URLs with prefix-aware URLs.
- Replace root-relative frontend `fetch(...)` endpoints with prefix-aware API URLs.
- Replace root-relative admin links and form actions with prefix-aware URLs.
- Decide whether to mount admin under the student FastAPI app or keep it separate with an explicit admin base path.
- Add regression tests that request the app with a `/stats` root path or configured base path and verify rendered links, static assets, API fetch URLs, and admin forms.

Until those changes exist, `/stats` requires an Nginx workaround that exposes root-level aliases for the app's generated URLs. That workaround is not a clean implementation of the intended public path.
