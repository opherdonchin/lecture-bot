# Moodle Grade Import Handoff

Date: 2026-05-07

This document captures historical implementation context for the Moodle grade-import work so a future conversation can resume quickly. For the current step-by-step operator process, use [`moodle_grade_upload_runbook.md`](moodle_grade_upload_runbook.md).

## Goal

Prepare one Moodle grade-import CSV from multiple Lecture Bot submission ZIPs, while validating every submitted report against:

- the Moodle participants export;
- the report filename metadata;
- the report header;
- the Lecture Bot SQLite database;
- grade events and report-generation timestamps.

The intended Moodle workflow is **Grade import**, not assignment offline grading worksheet. Grade import is the better fit here because one CSV can update multiple grade items at once.

## Decisions Made

### Submission ZIP Names

Future default naming pattern:

```text
data/submissions/<lecture_id>_submissions.zip
```

Examples:

```text
data/submissions/lecture_01_submissions.zip
data/submissions/lecture_02_submissions.zip
data/submissions/lecture_03_submissions.zip
```

I renamed the three current downloaded Moodle ZIPs into this pattern:

```text
367143610120262-Tutor 1-3323135.zip -> lecture_01_submissions.zip
367143610120262-Tutor 2-3323136.zip -> lecture_02_submissions.zip
367143610120262-Tutor 3-3323137.zip -> lecture_03_submissions.zip
```

### Config Boundary

The validation/import logic should not parse the app config directly. The future admin route should be responsible for:

- reading app/course/lecture config;
- deciding the submissions directory;
- saving uploaded ZIPs to the default or configured names;
- resolving the participants CSV path;
- resolving the database path;
- resolving Moodle grade-item column names;
- then calling the reusable function with explicit paths.

The reusable processing function now accepts those paths and mappings as arguments. This keeps the core logic testable and prevents web/config details from leaking into the parser.

### Participants Source

Use the CSV export as the default participants source:

```text
data/submissions/courseid_64733_participants.csv
```

It is flat, UTF-8 with BOM, and contains 67 participants with no duplicate ID numbers or emails. The JSON export is usable too, but has an extra top-level array wrapper, so the CSV is simpler.

### Moodle Identifier

The generated Moodle upload CSV uses:

```text
ID number
```

This should be mapped in Moodle to:

```text
ID number -> useridnumber
```

Do **not** map this column to `userid`; `userid` means Moodle's internal numeric user id, not the institutional/student ID number.

Moodle grade item columns are currently named by lecture id by default:

```text
lecture_01, lecture_02, lecture_03
```

These are intentionally configurable via the processing function and CLI. In real use, pass exact Moodle grade-item names if they differ from the lecture ids.

## What Was Implemented

### Admin App Integration

Added a simple admin home page:

```text
/
```

with links to:

```text
/lectures   Content
/sessions   Sessions
/grades     Grades
/analysis   Analysis placeholder
```

The old lecture setup screen remains available at:

```text
/lectures
```

Added the Grades workflow at:

```text
/grades
```

The Grades page can:

- show the current participants CSV status;
- upload/replace the participants CSV;
- set deadlines in the browser or upload a bulk deadlines CSV;
- show one expected submission ZIP per lecture folder;
- upload one or more per-lecture Moodle submission ZIPs;
- save those ZIPs using the default `<lecture_id>_submissions.zip` naming pattern;
- regenerate the Moodle import CSV and validation report from the uploaded ZIPs that exist;
- download the generated Moodle import CSV;
- download the validation/report CSV.

New admin routes:

```text
GET  /grades
POST /grades/participants
GET  /grades/deadlines/template
POST /grades/deadlines
POST /grades/deadlines/edit
POST /grades/submissions
POST /grades/prepare
GET  /grades/files/import
GET  /grades/files/report
GET  /analysis
```

Added app settings for the Moodle grade workflow:

```python
moodle_submissions_dir = Path("data/submissions")
moodle_participants_csv = Path("data/submissions/courseid_64733_participants.csv")
moodle_deadlines_csv = Path("data/submissions/moodle_deadlines.csv")
moodle_deadline_timezone_offset = "+03:00"
moodle_grade_import_csv = Path("data/submissions/moodle_grade_import.csv")
moodle_grade_import_report_csv = Path("data/submissions/moodle_grade_import_report.csv")
```

### New Core Module

Added:

```text
app/moodle_grade_import.py
```

Important functions:

```python
default_submission_zip_name(lecture_id)
default_submission_zip_path(submissions_dir, lecture_id)
discover_submission_archives(submissions_dir, lecture_ids=None)
load_participants_csv(path)
read_submission_records(submission_archives)
prepare_moodle_grade_import(...)
write_grade_import_outputs(...)
```

The admin flow calls the reusable preparation logic with resolved paths and deadline mappings. Direct use still looks like:

```python
prepare_moodle_grade_import(
    submission_archives={
        "lecture_01": Path("data/submissions/lecture_01_submissions.zip"),
        "lecture_02": Path("data/submissions/lecture_02_submissions.zip"),
        "lecture_03": Path("data/submissions/lecture_03_submissions.zip"),
    },
    participants_csv_path=Path("data/submissions/courseid_64733_participants.csv"),
    db_path=Path("data/lecture_bot.db"),
    grade_item_names={
        "lecture_01": "EXACT MOODLE GRADE ITEM NAME",
        "lecture_02": "EXACT MOODLE GRADE ITEM NAME",
        "lecture_03": "EXACT MOODLE GRADE ITEM NAME",
    },
)
```

### New CLI Wrapper

Added:

```text
scripts/prepare_moodle_grade_import.py
```

Basic command:

```bash
python3 scripts/prepare_moodle_grade_import.py
```

Command with explicit Moodle grade-item column names:

```bash
python3 scripts/prepare_moodle_grade_import.py \
  --grade-item lecture_01="Lecture 1 grade item name" \
  --grade-item lecture_02="Lecture 2 grade item name" \
  --grade-item lecture_03="Lecture 3 grade item name"
```

Command with specific lectures only:

```bash
python3 scripts/prepare_moodle_grade_import.py \
  --lecture lecture_01 \
  --lecture lecture_02
```

Command with per-lecture deadlines:

```bash
python3 scripts/prepare_moodle_grade_import.py \
  --deadline lecture_01=2026-05-10T23:59:00+03:00
```

Default outputs:

```text
data/submissions/moodle_grade_import.csv
data/submissions/moodle_grade_import_report.csv
```

## Current Validation Result

I ran:

```bash
python3 scripts/prepare_moodle_grade_import.py
```

Result:

```text
participants: 67
archives: 3
records: 38
accepted: 38
accepted_superseded: 0
rejected: 0
difficulties: 0
upload_rows: 16
```

The generated upload CSV currently starts like:

```csv
ID number,lecture_01,lecture_02,lecture_03
206391179,85,89,89
206571093,64,,
207178229,89,89,90
```

The validation report contains one row per submitted report, including participant name, email, session id, source ZIP, source file, submitted grade, database grade, and status.

## What The Validator Checks

For each report file:

- ZIP exists and is readable.
- ZIP entry looks like a Moodle file-submission entry.
- Report starts with:

```text
=== Lecture Bot Session Report ===
```

- Report contains parseable header fields.
- Student ID exists in the participants CSV.
- Student ID in the uploaded report filename matches the Student ID inside the report body, when the filename exposes it.
- Report lecture matches the archive lecture.
- Session ID exists in the SQLite database.
- Database student ID matches report student ID.
- Database lecture matches report lecture.
- Report grade matches database `sessions.current_grade` within the configured tolerance.
- `Session started` matches database `sessions.started_at`.
- `Report generated` is close to a database `grade_events` row with `event_type = 'report'`.
- Optional per-lecture deadline is enforced when provided.

If multiple accepted reports exist for the same student and lecture, the newest `Report generated` timestamp wins. Older accepted duplicates are marked `accepted_superseded` in the validation report and are not uploaded.

## Clarifications From The Earlier Plan

Point 3 in the earlier plan meant:

> Do not trust only one place for identity. The filename, report body, participant CSV, and database each contain overlapping information. The script should extract all of them and compare them.

For example, a Moodle ZIP entry currently looks like:

```text
מאיה אדמוני_13132310_assignsubmission_file_322818386_lecture_01_report.txt
```

The parser extracts:

- display name: `מאיה אדמוני`
- Moodle submission/internal id: `13132310`
- report filename student id: `322818386`
- report body student id: from `Student ID: ...`
- report body lecture id: from `Lecture: ...`

Point 4 meant:

> Moodle/browser downloads sometimes alter filenames, for example by adding `(1)`, `(3)`, or `-2`. The parser should not fail just because of those harmless suffixes.

The current data already includes examples like:

```text
lecture_01_report (1).txt
lecture_02_report (3).txt
lecture_01_report-2.txt
```

The validator now relies on the report header for the authoritative lecture/session/grade data and treats the filename mostly as an additional consistency check.

## Remaining Work

### Config Shape

The active app settings cover paths and admin-entered deadline timezone offset:

```python
moodle_submissions_dir
moodle_participants_csv
moodle_deadlines_csv
moodle_deadline_timezone_offset
moodle_grade_import_csv
moodle_grade_import_report_csv
```

Deadlines are surfaced in the admin UI and stored as `lecture_id,deadline` rows. Grade-item display names are still not configured in the admin UI; generated grade columns default to lecture ids unless the CLI `--grade-item` option or a direct function call supplies names. This could become course-level config rather than global app settings. The important point is that the core function should continue receiving resolved paths/mappings rather than reading config itself.

### Tests

Add focused tests for:

- valid multi-lecture import;
- malformed ZIP;
- unrecognized filename;
- invalid report header;
- missing participant;
- filename/report student mismatch;
- report/database student mismatch;
- report/database lecture mismatch;
- grade mismatch;
- missing report grade event;
- report-generated timestamp mismatch;
- duplicate accepted submissions where newest wins;
- deadline rejection.

### Moodle Dry Run

The current dry-run and upload process is documented in [`moodle_grade_upload_runbook.md`](moodle_grade_upload_runbook.md). The critical Moodle mapping remains: map `ID number` to `useridnumber`, not to `userid`.

## Files Changed Or Created

Created:

```text
app/moodle_grade_import.py
scripts/prepare_moodle_grade_import.py
docs/moodle_grade_import_handoff.md
app/templates/admin_home.html
app/templates/admin_grades.html
app/templates/admin_analysis.html
```

Updated:

```text
app/admin_main.py
app/config.py
app/static/admin.css
app/templates/admin_index.html
app/templates/admin_lecture.html
app/templates/admin_sessions.html
tests/test_admin_app.py
tests/test_path_prefixes.py
```

Renamed:

```text
data/submissions/367143610120262-Tutor 1-3323135.zip
data/submissions/367143610120262-Tutor 2-3323136.zip
data/submissions/367143610120262-Tutor 3-3323137.zip
```

to:

```text
data/submissions/lecture_01_submissions.zip
data/submissions/lecture_02_submissions.zip
data/submissions/lecture_03_submissions.zip
```

Generated:

```text
data/submissions/moodle_grade_import.csv
data/submissions/moodle_grade_import_report.csv
```

Existing unrelated modified files were present before this work and were not touched:

```text
.gitignore
app/bot_engine.py
```
