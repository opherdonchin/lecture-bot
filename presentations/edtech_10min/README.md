# Ed-Tech 10-Minute Presentation

This folder contains a Quarto Reveal.js deck for a 10-minute talk about `lecture-bot` as a reusable educational-technology pattern.

## Render

From the repository root:

```bash
cd presentations/edtech_10min
pixi run python generated/make_repo_tree.py
pixi run quarto render presentation.qmd
```

The canonical source is `presentation.qmd`. The rendered HTML will be created by Quarto in this folder.

Use Pixi for Quarto in this repository. If your shell also exposes Python as `python` or `python3`, that is fine for the repo-map helper, but the commands above keep the environment consistent.

## Regenerate the Repo Map

```bash
cd presentations/edtech_10min
pixi run python generated/make_repo_tree.py
```

The script writes `generated/repo_tree.txt`. It intentionally keeps the output to a first-level orientation map, shows lecture package directory names only, and excludes `.env`, databases, exports, logs, Quarto render output, caches, and private lecture-package contents.

## Export PDF

```bash
cd presentations/edtech_10min
pixi run quarto render presentation.qmd --to revealjs
pixi run quarto render presentation.qmd --to pdf
```

PDF export may require Quarto's PDF dependencies on the local machine. If PDF export is not available, use the rendered Reveal.js HTML and the browser print/export workflow.

## Screenshots

Place manual screenshots under:

```text
presentations/edtech_10min/assets/screenshots/
```

Do not fabricate screenshots. Use synthetic or scrubbed data only. Follow the exact checklist in `TO_DO.md`.

## Manual Work Remaining

- Capture the requested screenshots in `TO_DO.md`.
- Review the inserted screenshots for privacy and legibility.
- Re-render the deck after screenshots are added.
- Do one final privacy pass before sharing outside the project.

## Safe To Commit

- `presentation.qmd`
- `_quarto.yml`
- `README.md`
- `TO_DO.md`
- `assets/css/custom.scss`
- `assets/diagrams/*.mmd`
- `assets/screenshots/.gitkeep`
- `generated/make_repo_tree.py`
- `generated/repo_tree.txt`
- Scrubbed/synthetic screenshots that contain no student data, secrets, logs, database rows, private course material, or private exports

## Do Not Commit

- `.env` or API keys
- SQLite databases under `data/` or elsewhere
- `exports/` packages unless explicitly scrubbed and approved
- `app.log`, `admin.log`, or production logs
- student IDs, rosters, Moodle exports, or identifiable student data
- private lecture source files or processed lecture packages
- screenshots showing API keys, admin credentials, database contents, raw logs, or identifiable students
