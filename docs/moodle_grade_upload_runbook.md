# Moodle Grade Upload Runbook

This runbook is the operator-facing process for turning Lecture Bot reports submitted through Moodle into Moodle gradebook entries.

Use Moodle **Grade import** with a CSV. Do not use the assignment offline grading worksheet for this workflow: one generated CSV can update multiple grade items, and the validator cross-checks each report against the Lecture Bot database before anything is uploaded back to Moodle.

## Inputs And Outputs

Required inputs:

- Moodle participants CSV export for the course.
- One Moodle assignment submission ZIP per Lecture Bot lecture.
- The current Lecture Bot SQLite database, normally `data/lecture_bot.db`.

Optional input:

- Per-lecture generated-report deadlines. When present, the generated import CSV includes an additional `<grade item>_on_time` column for each lecture with a deadline.

Default files:

| Path | Purpose |
|---|---|
| `data/submissions/courseid_64733_participants.csv` | Moodle participants CSV used to validate student IDs. |
| `data/submissions/moodle_deadlines.csv` | Optional `lecture_id,deadline` CSV used for on-time columns. |
| `data/submissions/<lecture_id>_submissions.zip` | Moodle submission ZIP saved for one lecture. |
| `data/submissions/moodle_grade_import.csv` | CSV to upload through Moodle Grade import. |
| `data/submissions/moodle_grade_import_report.csv` | Validation/audit report to review before importing grades. |

Keep all of these files private. They can contain student identifiers, grades, and submitted reports.

## Preferred Admin UI Process

Use this path when the admin app is available.

1. Start or open the admin app.

   In production, open:

   ```text
   /stats-admin/grades
   ```

   In local development, run:

   ```bash
   pixi run admin-dev
   ```

   Then open:

   ```text
   http://127.0.0.1:8001/bot-admin/grades
   ```

2. Export the Moodle participants list as CSV from the Moodle course.

   The CSV must include the Moodle profile ID number column. The importer reads the column named:

   ```text
   ID number
   ```

3. Upload the participants CSV in the **Participants CSV** section.

   The admin app saves it to `data/submissions/courseid_64733_participants.csv`, unless the path is overridden by `MOODLE_PARTICIPANTS_CSV`.

4. Set deadlines, if the Moodle gradebook needs on-time indicators.

   Either edit the per-lecture deadline fields in the **Deadlines** section, or download the template, fill `lecture_id,deadline`, and upload it as a bulk CSV.

   Deadline values must be ISO datetimes, for example:

   ```text
   2026-05-10T23:59:00+03:00
   ```

   If a lecture has no deadline, no on-time column is generated for that lecture.

5. Download Moodle submission ZIPs, one per Lecture Bot assignment or lecture.

   Use Moodle's assignment submissions download for each lecture. Do not unzip or rename the files manually when using the admin UI.

6. Upload each ZIP in the matching row under **Submission ZIPs**.

   The admin app saves each ZIP as:

   ```text
   data/submissions/<lecture_id>_submissions.zip
   ```

   Uploading ZIPs automatically regenerates the Moodle import CSV and validation report.

7. Review **Latest Preparation**.

   A normal run should have:

   - `participants` matching the Moodle course participant count.
   - `archives` matching the number of uploaded lecture ZIPs.
   - `rejected` equal to `0`.
   - `difficulties` equal to `0`.

   Any non-zero `rejected` or `difficulties` count means the validation report needs review before Moodle import.

8. Download and inspect `moodle_grade_import_report.csv`.

   For every row that matters, check:

   - `status` is `accepted` or, for older duplicate submissions, `accepted_superseded`.
   - `issue` is blank for accepted rows.
   - `student_id`, `lecture_id`, `session_id`, `submitted_grade`, and `db_grade` look right.
   - `timing_status` is expected: `on_time`, `late`, or `deadline_missing`.

   Do not import grades while unexplained rows are `rejected`.

9. Download `moodle_grade_import.csv`.

   This is the only generated file that should be uploaded into Moodle Grade import.

10. In Moodle, open the course gradebook import page and choose CSV grade import.

11. Upload `moodle_grade_import.csv` and continue to the mapping preview.

12. Map the user identifier exactly:

   ```text
   ID number -> useridnumber
   ```

   Do not map `ID number` to `userid`. In Moodle, `userid` is Moodle's internal numeric user id, not the institutional/student ID number used by this project.

13. Map each grade column to the intended Moodle grade item.

   By default the generated grade columns are lecture IDs such as:

   ```text
   lecture_01
   lecture_02
   lecture_03
   ```

   If deadlines were set, additional columns appear:

   ```text
   lecture_01_on_time
   ```

   Map these only if matching grade items exist in Moodle.

14. Preview the Moodle import carefully before confirming.

   Confirm only after Moodle shows the expected users, grade items, and values.

## CLI Fallback

Use the CLI when the admin app is unavailable or when a scripted run is easier.

1. Put files in the expected locations:

   ```text
   data/submissions/courseid_64733_participants.csv
   data/submissions/lecture_01_submissions.zip
   data/submissions/lecture_02_submissions.zip
   data/submissions/lecture_03_submissions.zip
   ```

2. Run the multi-lecture import preparer:

   ```bash
   pixi run python scripts/prepare_moodle_grade_import.py
   ```

3. To include only specific lectures, repeat `--lecture`:

   ```bash
   pixi run python scripts/prepare_moodle_grade_import.py \
     --lecture lecture_01 \
     --lecture lecture_02
   ```

4. To set grade item column names explicitly, repeat `--grade-item`:

   ```bash
   pixi run python scripts/prepare_moodle_grade_import.py \
     --grade-item lecture_01="Lecture 1" \
     --grade-item lecture_02="Lecture 2"
   ```

5. To add on-time columns from deadlines, repeat `--deadline`:

   ```bash
   pixi run python scripts/prepare_moodle_grade_import.py \
     --deadline lecture_01=2026-05-10T23:59:00+03:00
   ```

6. Review the command summary and `data/submissions/moodle_grade_import_report.csv`.

7. Upload `data/submissions/moodle_grade_import.csv` through Moodle Grade import using the mapping instructions above.

The older `scripts/grade_moodle.py` handles a single Moodle submission ZIP and produces an assignment-style CSV. Prefer `scripts/prepare_moodle_grade_import.py` or the admin **Grades** page for the current multi-lecture workflow.

## What The Validator Checks

The generated validation report is not just a parse log. Each submission is checked against overlapping identity and timing data:

- ZIP exists and is readable.
- ZIP entries look like Moodle file-submission entries.
- Report starts with `=== Lecture Bot Session Report ===`.
- Report contains parseable session, student, lecture, grade, session-start, and report-generated fields.
- Student ID exists in the participants CSV.
- Student ID in the submitted report filename matches the report body when the filename exposes it.
- Report lecture matches the ZIP's expected lecture.
- Session ID exists in the Lecture Bot database.
- Database student ID and lecture match the report.
- Report grade matches `sessions.current_grade` within the configured tolerance.
- `Session started` matches the database session start timestamp.
- `Report generated` is close to a database `grade_events` row with `event_type = 'report'`.
- If a deadline exists for the lecture, `on_time` is `1` or `0`; late reports are still accepted unless another validation check fails.

If multiple accepted reports exist for the same student and lecture, the newest `Report generated` timestamp is uploaded. Older accepted duplicates are marked `accepted_superseded` in the validation report.

## Moodle Notes

Moodle's CSV grade import preview lets you map user fields and grade item columns. Moodle's own guidance is to map an ID number column to `useridnumber`, not to `userid`, when the CSV contains institutional/user ID numbers. Moodle also warns that importing grades into activity grade items is equivalent to manual grading in the grader report, so confirm the target grade items before uploading.

Reference: <https://docs.moodle.org/502/en/Grade_import>
