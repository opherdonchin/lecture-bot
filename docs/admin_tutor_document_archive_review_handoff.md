# Admin Tutor Document Archive — Review Handoff

This document describes the work done on branch `admin-tutor-document-archive` for the benefit of an independent reviewer. It covers what was built, why key decisions were made, and where to look for each piece.

---

## Background

The lecture-bot is a FastAPI app with a student-facing chat interface and a separate admin app. The admin app previously had no way to manage or version the tutor prompt. This branch adds a document archive, admin UI for managing and activating tutor prompts, a generation workflow (calling OpenAI), runtime session linkage, and export integration.

Design spec: `docs/admin_tutor_document_archive_spec.md`
Implementation plan: `docs/admin_tutor_document_archive_implementation_plan.md`

---

## Files changed or created

### New app modules
- `app/archive_helpers.py` — pure helpers: `make_document_id`, `make_version_key`, `sha256_of_text`, `parse_linked_documents`, `get_active_document`, `get_active_document_id`, `compatible_with_active_contracts`, `is_activatable`
- `app/admin_documents.py` — document list/detail/activate logic, `build_assembled_tutor`, `collect_export_documents`
- `app/admin_generation.py` — OpenAI generation workflow: assemble active docs, call model, parse JSON response, store results in DB

### Modified app modules
- `app/models.py` — added `ArchiveDocumentModel`, `TutorGenerationRunModel`, `prompt_document_id` on `SessionModel`, `DOCUMENT_TYPES` and `CONTRACT_TYPES` constants
- `app/admin_main.py` — added routes: `/documents`, `/documents/tutor-prompts`, `/documents/{id}`, `/documents/{id}/activate`, `/generate-tutor-prompt` (GET+POST), `/restart-student-app`
- `app/admin_sessions.py` — export zip now includes `documents/` and `assembled_tutors/` folders; top-level manifest lists `prompt_document_ids`
- `app/session_manager.py` — on session creation, identifies the active prompt by SHA-256 lookup (see decision below)

### New templates
- `app/templates/admin_documents.html` — all archive documents grouped by type
- `app/templates/admin_tutor_prompts.html` — focused tutor prompt list with activate buttons and restart button
- `app/templates/admin_document_detail.html` — full document detail with linked docs, provenance, content
- `app/templates/admin_generate.html` — generation form + result display

### Modified templates
- `app/templates/admin_index.html` — added Document Archive and Student App (restart) sections

### Scripts
- `scripts/bootstrap_archive.py` — one-time idempotent import of current repo files into `archive_documents`; skips by document_id or sha256 match; sets active=True
- `scripts/init_db.py` — added migration guard for `prompt_document_id` column
- `scripts/export_session_package.py` — `get_session` now selects `prompt_document_id`; `build_manifest` includes it

### Prompts
- `prompts/tutor_generator_prompt.md` — output format section replaced: now requires a JSON object with keys `status`, `conformance_failures`, `backend_incompatibilities`, `recommended_omissions`, `tutor_spec`, `tutor_artifact_schema`, `tutor_prompt`

### Tests
- `tests/test_archive.py` — 27 tests covering all helpers in `archive_helpers.py` including every `is_activatable` blocking reason
- `tests/test_bootstrap_archive.py` — 12 tests covering import, idempotence, sha256 dedup, dry-run, provenance, linked documents

---

## Key design decisions and non-obvious choices

### Session prompt identity: SHA-256 + active-flag cross-check
`session_manager.py` identifies which archive document corresponds to the live `prompts/tutor_prompt.md` by hashing its content and querying `archive_documents` for a sha256 match. It also queries for the active-flagged document and logs a warning if they disagree. SHA-256 is the stored value because it reflects what the model actually sees; the active flag is a consistency check only.

An earlier approach used a `prompts/current_tutor_prompt.json` marker file. This was removed because it was a redundant extra file that could get out of sync. The SHA-256 approach degrades gracefully: if the file doesn't match any archived document, `prompt_document_id` is `None`.

### No `current_tutor_prompt.json`
The file was briefly introduced and then deleted. There is no marker file. Identity is entirely content-based.

### `is_activatable` only applies to `tutor_prompt` documents
Contracts (`tutor_spec_contract`, `backend_contract`) are read-only in this branch. No UI allows activating a contract. `is_activatable` returns False immediately for any non-`tutor_prompt` document type.

### Generation always archives the input spec
When generation succeeds, three archive documents are created: `tutor_spec`, `tutor_artifact_schema`, and `tutor_prompt`. The input spec (or repaired spec if `status="repaired"`) is always archived because `is_activatable` requires the `tutor_prompt` to link to a `tutor_spec` that exists in the archive. Without archiving the spec, the generated prompt could never be activated.

### Generator prompt updated to JSON output
The previous generator prompt produced structured markdown. The new output format section requires a single JSON object. The model is called with `response_format={"type": "json_object"}`. The quality standards sections (defect reporting standards, prompt generation standards) were kept but moved before the output format section.

### Export: documents are not duplicated per session
`collect_export_documents` in `admin_documents.py` deduplicates by document_id across all exported sessions. Each document appears once in `documents/` regardless of how many sessions used it. The `assembled_tutors/{prompt_doc_id}.json` file contains metadata and file pointers but not the content itself (content is in `documents/`).

### Bootstrap version key
The bootstrap script was run twice: once with the default date key (`2026-05-04`), and once with `--version-key 2026-05-04_json` after the generator prompt was updated. The second run imported only the updated generator prompt (others were skipped by sha256 match). The new generator prompt is now the active one.

---

## What is explicitly out of scope for this branch

- React or any frontend migration
- `app_settings` table
- `tutor_versions` table
- Per-turn prompt ID tracking
- Contract replacement or activation via admin UI
- Scheduled restart
- Deleting historical archive documents
- Storing failed/invalid documents as archive documents

---

## Running the tests

```
pixi run pytest tests/test_archive.py tests/test_bootstrap_archive.py
```

48 tests pass across archive, bootstrap, admin app, and admin sessions test files. 7 pre-existing failures in `test_send_message.py` are unrelated to this branch.

## Bootstrapping the archive

After `python scripts/init_db.py`:

```
python scripts/bootstrap_archive.py
```

This imports current repo files. Idempotent — safe to run multiple times.
