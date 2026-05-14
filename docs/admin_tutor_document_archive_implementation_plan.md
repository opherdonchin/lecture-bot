# Admin Tutor Document Archive — Implementation Plan

See `docs/admin_tutor_document_archive_spec.md` for the design specification this plan implements.

---

## Phase 1 — Schema and helpers

**Goal:** Database models and helper functions. No UI, no import.

### Tasks

1. Add `ArchiveDocumentModel` to `app/models.py`.
   - Columns: `document_id` (PK), `document_type`, `version_key`, `title`, `description`, `content_text`, `content_format`, `linked_documents_json`, `content_sha256`, `active`, `provenance_json`, `created_at`, `updated_at`.

2. Add `TutorGenerationRunModel` to `app/models.py`.
   - Columns: `id` (PK), `run_id` (unique), `status`, `input_spec_text`, `input_spec_title`, `generator_document_id`, `spec_contract_document_id`, `backend_contract_document_id`, `output_document_ids_json`, `raw_output_json`, `error_text`, `created_at`.

3. Add `prompt_document_id` (nullable TEXT) to `SessionModel`.

4. Update `scripts/init_db.py` to:
   - Create new tables via `Base.metadata.create_all` (automatic since models are registered).
   - Add `ALTER TABLE sessions ADD COLUMN prompt_document_id TEXT` migration for existing SQLite databases.

5. Create `app/archive_helpers.py` with:
   - `make_document_id(document_type, version_key) -> str`
   - `make_version_key(date, suffix=None) -> str`
   - `sha256_of_text(text) -> str`
   - `parse_linked_documents(linked_documents_json) -> dict[str, str]`
   - `get_active_document(db, document_type) -> ArchiveDocumentModel | None`
   - `get_active_document_id(db, document_type) -> str | None`
   - `compatible_with_active_contracts(doc, db) -> bool`
   - `is_activatable(doc, db) -> tuple[bool, list[str]]`

6. Add `tests/test_archive.py` covering:
   - `make_document_id` and `make_version_key`
   - `sha256_of_text`
   - `parse_linked_documents`
   - `get_active_document` / `get_active_document_id`
   - `compatible_with_active_contracts`
   - `is_activatable` (happy path and each blocking reason)

### Out of scope in Phase 1
- Bootstrap import
- Admin UI
- Runtime changes

---

## Phase 2 — Initial archive import / bootstrap

**Goal:** One-time script to populate archive_documents from current repo files.

### Tasks

1. Create `scripts/bootstrap_archive.py`.
   - Import current repo files into `archive_documents`.
   - Documents to import (skip if file does not exist):
     - `docs/tutor_specification_contract.md` → `tutor_spec_contract`
     - `docs/backend_tutor_contract.md` → `backend_contract`
     - `prompts/tutor_generator_prompt.md` → `tutor_generator_prompt`
     - `docs/tutor_specification.md` → `tutor_spec`
     - `prompts/tutor_prompt_private_artifact_schema.json` → `tutor_artifact_schema`
     - `prompts/tutor_prompt.md` → `tutor_prompt`
     - `prompts/spec_repair_prompt.md` → `spec_repair_prompt` (if present)
   - Set `active = True` on all imported documents.
   - Build `linked_documents_json` for the tutor_prompt linking all other imported documents.
   - Build `linked_documents_json` for tutor_spec linking the active tutor_spec_contract.
   - Build `linked_documents_json` for tutor_generator_prompt linking both contracts.
   - Store import source path in `provenance_json`.
   - **Idempotent**: skip any document whose `document_id` already exists in the table. If a document with matching sha256 exists under a different ID, still skip insertion and ensure the active flag is correct.

2. Add `tests/test_bootstrap_archive.py` (or in existing test file) covering:
   - Script produces the expected set of archive_documents rows.
   - Running the script twice does not create duplicates.
   - Each imported document has correct sha256, content_format, and linked_documents_json.
   - active flags are correct after import.

### Not a permanent admin button
The bootstrap script is a one-time CLI operation. It must not be exposed as an admin UI action.

---

## Phase 3 — Admin document pages

**Goal:** Admin UI for viewing and activating tutor prompts.

### Tasks

1. Add `/admin/documents` page listing all archive documents, grouped by type.
   - Show: document_id, version_key, title, active, compatible_with_active_contracts.

2. Add `/admin/documents/tutor-prompts` page focused on `tutor_prompt` documents.
   - For each prompt: show active, compatible_with_active_contracts, activatable, linked document IDs, and all blocking reasons if not activatable.

3. Add `/admin/documents/<document_id>` detail page.
   - Show all fields. Render content_text (with syntax highlight for JSON).

4. Add `POST /admin/documents/<document_id>/activate` endpoint.
   - Reject if not activatable.
   - Write canonical files (spec §7).
   - Write `prompts/current_tutor_prompt.json`.
   - Update active flags in DB.
   - Flash message: "Tutor prompt activated. Restart the student app to apply."

5. Optionally add "restart student app" button if service management is available.

---

## Phase 4 — Generation workflow

**Goal:** Admin can upload a tutor spec and generate a new tutor prompt.

### Tasks

1. Update or replace `prompts/tutor_generator_prompt.md` so generator output is JSON with:
   ```json
   {
     "status": "ok" | "failed" | "repaired",
     "conformance_failures": [...],
     "backend_incompatibilities": [...],
     "recommended_omissions": [...],
     "tutor_spec": null | "<repaired spec text>",
     "tutor_artifact_schema": "<json string>",
     "tutor_prompt": "<prompt text>"
   }
   ```

2. Add repair prompt if needed (`prompts/spec_repair_prompt.md`).

3. Add `POST /admin/generate-tutor-prompt` admin endpoint:
   - Accept uploaded/pasted tutor_spec text and title.
   - Uses active tutor_spec_contract, backend_contract, tutor_generator_prompt, spec_repair_prompt.
   - Calls OpenAI to generate.
   - On success: insert archive_documents rows for tutor_prompt, tutor_artifact_schema, and repaired tutor_spec if applicable.
   - On failure: insert only a tutor_generation_runs row.
   - Never insert invalid documents into archive_documents.

4. Show generation result and link to created documents (if success).

---

## Phase 5 — Runtime session linkage

**Goal:** Sessions record which prompt document they used.

### Tasks

1. On session creation in `app/session_manager.py`:
   - Read `prompts/current_tutor_prompt.json` if it exists.
   - Extract `tutor_prompt_document_id`.
   - Store on `session.prompt_document_id`.

2. Do not change prompt loading logic.

3. Do not switch prompts mid-session.

4. Do not add document IDs to turn-level audit rows.

---

## Phase 6 — Export integration

**Goal:** Exports include the document graph.

### Tasks

1. Update `scripts/export_session_package.py` and admin export in `app/admin_sessions.py`:
   - Add `documents/` folder with one file per relevant archive document.
   - Add `assembled_tutors/<prompt_document_id>.json` containing the full document graph for each prompt used in the export.
   - Include `prompt_document_id` in session manifests.
   - Do not duplicate the same document inside every session folder.
   - Preserve existing export behavior for sessions without `prompt_document_id`.

---

## Phase 7 — Optional restart support

**Goal:** Admin can restart the student app from the UI.

### Tasks

1. Check if the current deployment uses systemd (see `deploy/systemd/`).
2. If restart is safe and straightforward (e.g. `systemctl restart lecture-bot`), add a `POST /admin/restart-student-app` endpoint.
3. If not, show only the restart warning and the command to run.
4. Do not implement scheduled restart.

---

## Out of scope for this branch

- React or any frontend migration
- `app_settings` table
- `tutor_versions` table
- Per-turn tutor version or prompt ID tracking
- Ordinary admin contract replacement or activation
- Scheduled restart
- Deleting historical archive documents
- Storing failed/invalid documents as archive documents
