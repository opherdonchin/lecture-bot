# TO DO

## Render And Validation

- [x] Run `python3 generated/make_repo_tree.py` from `presentations/edtech_10min/`.
- [x] Run `pixi run quarto render presentation.qmd` from `presentations/edtech_10min/`.
- [x] Bare `quarto` was not on this shell path earlier; use Pixi for Quarto in this repository.
- [x] Removed stale rendered `presentation.html` / `presentation_files/`; regenerate before viewing.
- [x] After adding screenshots, re-render the deck with Pixi.
- [ ] Check that slide text and diagrams do not overlap on laptop and projector-sized windows.
- [ ] Optional: run a browser-based visual check of the rendered deck. Playwright is not installed in the current Pixi environment.
- [ ] Do a final privacy pass before sharing the deck.

## Screenshot Checklist

Use only synthetic or scrubbed data. Avoid showing real student IDs, real logs, API keys, `.env`, admin credentials, private database contents, raw exports, or identifiable student data.

### 1. Student chat opening screen

- [x] Screenshot added to `presentation.qmd`.

- Filename: `assets/screenshots/student_chat_opening.png`
- Capture: the student app at `/bot/` or the deployed student root, before starting a session.
- Suggested crop: the full browser viewport showing **Lecture Bot**, **Session**, **Student ID**, **Lecture**, **Start Session**, **Chat**, and **Controls**.
- Used on: Slide 1.
- Avoid showing: real student IDs, real course-only/private lecture labels if the deck will be shared outside the course team.

### 2. Short tutor exchange

- [x] Screenshot added to `presentation.qmd`.

- Filename: `assets/screenshots/student_short_exchange.png`
- Capture: a synthetic session after one or two short student/tutor messages.
- Suggested crop: the chat transcript area plus the message input.
- Used on: Slide 2.
- Avoid showing: real student answers, real session IDs, private lecture content that should not be public.

### 3. Current grade or final report

- [x] Screenshot added to `presentation.qmd`.

- Filename: `assets/screenshots/current_grade_or_final_report.png`
- Capture: preferably the **Final Report** card after clicking **Generate final report** in a synthetic/scrubbed session, including the **Download report** button and Moodle upload notice. A **Current grade** card is acceptable if the final report screenshot is not ready.
- Suggested crop: just the grade/report card and enough surrounding UI to show that it is inside the student chat.
- Used on: Slide 5.
- Avoid showing: real grades for real students, real student IDs, raw report downloads containing identifiable data.
- Note: the downloaded report is what students upload to Moodle. `scripts/grade_moodle.py` validates Moodle submissions against backend session records before producing a grade CSV.

### 4. Lecturer/admin content setup or lecture-package directory

- [x] Screenshot added to `presentation.qmd`.

- Filename: `assets/screenshots/admin_lecture_setup_or_package.png`
- Capture option A: the admin lecture setup page at `/bot-admin/lectures/<lecture_id>` or `/stats-admin/lectures/<lecture_id>`, preferably showing **Select Source Files** and **Build Workflow**.
- Capture option B: a file-browser view of a synthetic lecture-package directory showing public-safe filenames such as `lecture_config.json`, `slides.md`, `handout.md`, `minutes.json`, and `rubric.md`.
- Suggested crop: admin workflow area or file list only.
- Used on: Slide 3.
- Avoid showing: private lecture source contents, uploaded real course materials, full local paths that reveal sensitive deployment/user information, admin credentials.

### 5. Export package, admin export screen, or structured analysis output

- [x] Screenshot added to `presentation.qmd`.

- Filename: `assets/screenshots/export_or_analysis_output.png`
- Capture: a scrubbed export package directory, a terminal/file-browser view of package structure, or a staged analysis output created from synthetic/scrubbed conversations using `prompts/log_analysis_prompt.md`.
- Suggested crop: show filenames or stage outputs, not raw private content.
- Used on: Slide 7.
- Avoid showing: real transcripts, real student IDs, private artifact internals tied to real students, database rows, raw logs, private course material, export zip contents that have not been scrubbed.
- Note: the current repo exposes session filtering/export through the admin app (`/sessions`, `/sessions/export`) and still has script exports (`scripts/export_session_package.py`, `scripts/export_investigation_package.py`).

### 6. Optional repo/file tree view

- [x] Screenshot added to `presentation.qmd`.

- Filename: `assets/screenshots/public_safe_repo_tree.png`
- Capture: the generated `generated/repo_tree.txt` or a public-safe IDE tree.
- Suggested crop: top-level folders plus the `presentations/edtech_10min/` folder.
- Used on: backup slide only if visually useful.
- Avoid showing: `.env`, `data/`, `exports/`, lecture-package contents, `app.log`, `admin.log`, or private runtime files. It is fine to show package directory names such as `lecture_01/`.

## Screenshot Replacement

The previous screenshot slots have been replaced with screenshot images.

Before public sharing, review the screenshots one more time for student IDs, session IDs, dates, grades, or other operational details that should be scrubbed.

## Notes On Analysis Prompt

The repository already contains `prompts/log_analysis_prompt.md`, which serves the structured conversation-analysis role for Slide 7. No new analysis prompt file is needed.
