# Admin Tutor Document Archive — Design Specification

## Purpose

This document describes the target design for the lecture-bot admin document archive. It is the authoritative reference for implementation, review, and future work on this branch.

---

## 1. Overview

The admin system gains a document archive that stores tutor-related documents and typed links between them. The archive makes it possible to track which spec, generator prompt, and contracts produced a given tutor prompt, activate a new tutor prompt from the admin UI, and export the full document graph alongside session exports.

The student-facing runtime is unchanged for now. It continues to load prompts from canonical repo files. Activation writes those files from the archive.

---

## 2. Document types

Exactly eight document types exist. No others are valid in archive_documents.

| Type | Description |
|---|---|
| `tutor_spec` | A tutor specification (pedagogy, identity, evaluation, topics) |
| `tutor_prompt` | The runtime system prompt derived from a spec |
| `tutor_artifact_schema` | The private artifact JSON Schema used by the tutor |
| `tutor_spec_contract` | The structural contract a tutor spec must satisfy |
| `backend_contract` | The runtime contract governing tutor↔backend interface |
| `tutor_generator_prompt` | The prompt used to generate tutor prompts from specs |
| `spec_repair_prompt` | Prompt used to repair a spec that fails contract checks |
| `tutor_analysis_prompt` | Prompt used for tutor analysis workflows |

---

## 3. archive_documents table

Each row represents one structurally valid, usable document. Failed generations, malformed outputs, and contract failures are not stored here — they belong in `tutor_generation_runs`.

### Columns

| Column | Type | Notes |
|---|---|---|
| `document_id` | TEXT PK | Format: `doc_{document_type}_{version_key}` |
| `document_type` | TEXT | One of the eight types above |
| `version_key` | TEXT | Human-readable version identifier, e.g. `2026-05-03` |
| `title` | TEXT | Short display title |
| `description` | TEXT nullable | Optional longer description |
| `content_text` | TEXT | Full document text (Markdown or JSON) |
| `content_format` | TEXT | `"markdown"` or `"json"` |
| `linked_documents_json` | TEXT nullable | JSON object mapping document_type to document_id |
| `content_sha256` | TEXT | SHA-256 hex digest of `content_text` (UTF-8) |
| `active` | BOOLEAN | True for the one active document of this type |
| `provenance_json` | TEXT nullable | Import/generation metadata (source_path, etc.) |
| `created_at` | DATETIME | Row creation timestamp (UTC) |
| `updated_at` | DATETIME | Last update timestamp (UTC) |

**Constraints:**
- At most one active document per `document_type` (enforced in application code).
- Invalid documents must not be inserted. Only insert on confirmed structural validity.

### linked_documents_json format

A JSON object where each key is the linked document's type and the value is that document's document_id. Keys are plain document type names — not verbose edge names.

Example for a `tutor_prompt`:
```json
{
  "tutor_spec": "doc_tutor_spec_2026-05-03",
  "tutor_generator_prompt": "doc_tutor_generator_prompt_2026-05-04",
  "tutor_spec_contract": "doc_tutor_spec_contract_2026-05-04",
  "backend_contract": "doc_backend_contract_2026-05-04",
  "tutor_artifact_schema": "doc_tutor_artifact_schema_2026-05-04"
}
```

### Fields NOT in archive_documents

- `source_path`, `source_git_commit` — put these in `provenance_json` if needed.
- `valid` / `status` fields — invalid documents must not be stored here.

---

## 4. tutor_generation_runs table

Records every generation attempt, successful or not. Failed runs are only here — never in `archive_documents`.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `run_id` | TEXT UNIQUE | Unique run identifier |
| `status` | TEXT | `"success"`, `"failed"`, or `"partial"` |
| `input_spec_text` | TEXT nullable | The raw spec pasted or uploaded |
| `input_spec_title` | TEXT nullable | Title given to the spec |
| `generator_document_id` | TEXT nullable | FK into archive_documents |
| `spec_contract_document_id` | TEXT nullable | FK into archive_documents |
| `backend_contract_document_id` | TEXT nullable | FK into archive_documents |
| `output_document_ids_json` | TEXT nullable | JSON list of created document IDs (success only) |
| `raw_output_json` | TEXT nullable | Raw generator output |
| `error_text` | TEXT nullable | Error detail on failure |
| `created_at` | DATETIME | Run creation timestamp (UTC) |

---

## 5. Sessions

Add one column to the `sessions` table:

| Column | Type | Notes |
|---|---|---|
| `prompt_document_id` | TEXT nullable | The archive_documents document_id for the prompt used |

This is set at session creation by reading `prompts/current_tutor_prompt.json` if present.

**Do not add:**
- `tutor_version_id`
- prompt hash fields
- document IDs per turn

---

## 6. Active and activatable

### active (stored)
- Boolean column on archive_documents.
- At most one document per type may be active.
- Contracts are read-only in this branch. Their active flag is set during bootstrap. Ordinary admin workflows must not allow replacing or activating contracts.

### compatible_with_active_contracts (computed)
A document is compatible with active contracts if, for every contract type (`tutor_spec_contract`, `backend_contract`) that appears in its `linked_documents_json`, the linked document_id matches the currently active document of that type.

Documents with no contract links (including contracts themselves) are always compatible.

### activatable (computed, tutor_prompt only)
A `tutor_prompt` document is activatable if and only if all of the following hold:

1. Its `document_type` is `tutor_prompt`.
2. `linked_documents_json` contains all required keys: `tutor_spec`, `tutor_artifact_schema`, `tutor_generator_prompt`, `tutor_spec_contract`, `backend_contract`.
3. The `tutor_spec_contract` link matches the currently active tutor_spec_contract.
4. The `backend_contract` link matches the currently active backend_contract.
5. The linked `tutor_spec` exists in archive_documents and is compatible with active contracts.
6. The linked `tutor_generator_prompt` exists in archive_documents and is compatible with active contracts.
7. The linked `tutor_artifact_schema` exists in archive_documents and its `content_text` parses as valid JSON.

---

## 7. Activation

Activating a tutor_prompt:

1. Check it is activatable (fail fast if not).
2. Write `prompts/tutor_prompt.md` from the document's `content_text`.
3. Write `docs/tutor_specification.md` from the linked tutor_spec's `content_text`.
4. Write `prompts/tutor_prompt_private_artifact_schema.json` from the linked tutor_artifact_schema's `content_text`.
5. Write `prompts/current_tutor_prompt.json`:
   ```json
   {
     "tutor_prompt_document_id": "...",
     "activated_at": "2026-..."
   }
   ```
6. Set `active = True` on the tutor_prompt; set `active = False` on any other tutor_prompt.
7. Warn the admin that the student app must be restarted for changes to take effect.

---

## 8. Runtime prompt loading

The student app continues to load prompts from canonical repo files:
- `prompts/tutor_prompt.md`
- `prompts/tutor_prompt_private_artifact_schema.json`
- `docs/tutor_specification.md`

At session creation, the app reads `prompts/current_tutor_prompt.json` if present and stores `prompt_document_id` on the session row.

Prompt loading is cached via `lru_cache`. Changes only take effect on restart.

---

## 9. Export structure

```
export.zip
  manifest.json
  sessions/
    <session_id>/
      manifest.json
      conversation/
      private_artifacts/
      grade_events/
  documents/
    <document_id>.md   (or .json)
  assembled_tutors/
    <prompt_document_id>.json
```

Each session manifest includes `prompt_document_id`. Prompt/spec/contract files appear once in `documents/`, not duplicated per session. Each assembled tutor manifest lists the complete document graph.

---

## 10. Out of scope for this branch

- React or any frontend migration
- `app_settings` table
- `tutor_versions` table
- Per-turn tutor version or prompt tracking
- Ordinary admin contract replacement or activation
- Scheduled restart
- Deleting historical archive documents
- Storing failed or invalid documents in `archive_documents`
- Generation workflow (Phase 4)
- Admin document pages (Phase 3)
- Export integration (Phase 6)
- Restart support (Phase 7)
