# Admin Session Review And Export Plan

## Goal

Extend the existing admin app with a sessions page that lets an authenticated admin review student activity, filter sessions, select one or more sessions, and download a ZIP export for analysis.

This is an extension of the current admin app and current rich session export package. It is not a separate admin subsystem and it does not introduce a reduced export format.

## Routes

The admin FastAPI app continues to rely on its configured `root_path`. Route decorators inside `app.admin_main` use app-local paths only:

```text
GET  /sessions
POST /sessions/export
```

With `LECTURE_BOT_ADMIN_ROOT_PATH=/stats-admin`, these are publicly available as:

```text
/stats-admin/sessions
/stats-admin/sessions/export
```

Templates must use the existing `url_path(...)` helper instead of hard-coded deployment paths.

## Sessions Page

The sessions page is server-rendered and protected by the existing admin Basic Auth dependency.

Default behavior:

- newest sessions first
- page size 100
- simple pagination through `page` and `page_size`

Filters:

- student id, with exact or contains match
- lecture id
- started-at date range
- user turn count range
- current grade range

Table semantics:

- user turns: count of `messages` where `role == "user"`
- assistant turns: count of `messages` where `role == "assistant"`
- notes: count of `session_notes` rows for the session
- grade events: count of `grade_events` rows for the session
- current grade: stored `sessions.current_grade`

The list page is non-mutating. It does not recompute grades or inspect `session_state.turn_count`.

## Export

The export form uses checkboxes and one `Export Selected` button.

The endpoint validates:

- at least one selected session id
- every selected id is a valid UUID-shaped session id
- every selected id exists
- selection count is no greater than the export cap

The export cap is 50 sessions.

The response is a direct ZIP download with:

```text
Content-Type: application/zip
Content-Disposition: attachment; filename="lecture_bot_sessions_<timestamp>.zip"
```

For both single-session and multi-session exports, the ZIP uses one top-level directory per session:

```text
manifest.json
<session_id_1>/
  manifest.json
  conversation/
  prompts/
  contracts/
  schemas/
  lecture/
<session_id_2>/
  manifest.json
  conversation/
  prompts/
  contracts/
  schemas/
  lecture/
```

No nested ZIP files are written.

The top-level `manifest.json` uses:

```json
{
  "format": "lecture_bot_sessions_multi_export",
  "exported_at": "...",
  "session_count": 2,
  "session_ids": ["...", "..."],
  "notes": {
    "prompt_files_source": "current_files_at_export_time",
    "rendered_prompts_source": "dialogue_turn_audits",
    "student_comments_source": "conversation/session_notes.json"
  }
}
```

Each per-session package preserves the existing `scripts/export_session_package.py` shape, including:

- `conversation/session_bundle.json`
- `conversation/chat_transcript.json`
- `conversation/messages.txt`
- `conversation/messages_for_chat_agent.json`
- `conversation/dialogue_turn_audits.json`
- `conversation/private_artifact_logs.json`
- `conversation/session_notes.json`
- `conversation/session_private_artifact_schema.json` when present
- `prompts/`
- `contracts/`
- `schemas/`
- `lecture/`

The prompt bundle includes both the staged tutor-behavior analysis prompt and the separate comment-analysis prompt. The main analysis uses student comments only for late triangulation; the comment-analysis workflow gives those comments their fuller user-facing treatment without folding them into the ordinary chat transcript.

Student comments submitted through `POST /submit_note` are stored in `session_notes` and must appear in each exported session as:

```text
<session_id>/conversation/session_notes.json
```

## Implementation Shape

1. Refactor `scripts/export_session_package.py` so it can write one existing-format session package into an already-open `zipfile.ZipFile` under an archive prefix.
2. Preserve the existing CLI behavior for single-session exports.
3. Add `app/admin_sessions.py` for list/filter/export orchestration.
4. Add `/sessions` and `/sessions/export` to `app.admin_main`.
5. Add `app/templates/admin_sessions.html`.
6. Add a root-path-safe link from the existing admin index.
7. Update README and deployment docs.
8. Add tests for auth, filters, pagination-safe links, validation, ZIP shape, notes export, and no nested ZIP files.
