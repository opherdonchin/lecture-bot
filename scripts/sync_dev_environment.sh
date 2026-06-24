#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE_ENV_FILE="${LECTURE_BOT_REMOTE_ENV_FILE:-$ROOT_DIR/deploy/remote.env}"

if [[ -f "$REMOTE_ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$REMOTE_ENV_FILE"
  set +a
fi

usage() {
  cat <<'EOF'
Usage: scripts/sync_dev_environment.sh [--dry-run]

Pull production runtime state into a local development snapshot.

Required environment:
  LECTURE_BOT_REMOTE_HOST         SSH host for the production server

Optional environment:
  LECTURE_BOT_REMOTE_USER         SSH user (default: lecture-bot)
  LECTURE_BOT_REMOTE_ROOT         Remote repo root (default: /srv/lecture-bot)
  LECTURE_BOT_REMOTE_REPO_PATH    Backward-compatible alias for the remote repo root
  LECTURE_BOT_REMOTE_LOG_DIR      Remote log dir (default: /var/log/lecture-bot)
  LECTURE_BOT_LOCAL_SYNC_DIR      Local snapshot dir (default: .local/dev-sync)
  LECTURE_BOT_LOCAL_ENV_FILE      Generated local env file (default: .env.dev-sync)
  LECTURE_BOT_SSH_OPTS            Extra ssh options, appended as words

Examples:
  LECTURE_BOT_REMOTE_HOST=prod.example.edu pixi run sync-dev
  LECTURE_BOT_REMOTE_HOST=prod.example.edu pixi run sync-dev -- --dry-run
EOF
}

dry_run=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run|-n)
      dry_run=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_command rsync
require_command ssh

remote_host="${LECTURE_BOT_REMOTE_HOST:-}"
remote_user="${LECTURE_BOT_REMOTE_USER:-lecture-bot}"
remote_root="${LECTURE_BOT_REMOTE_ROOT:-${LECTURE_BOT_REMOTE_REPO_PATH:-/srv/lecture-bot}}"
remote_log_dir="${LECTURE_BOT_REMOTE_LOG_DIR:-/var/log/lecture-bot}"
local_sync_dir="${LECTURE_BOT_LOCAL_SYNC_DIR:-$ROOT_DIR/.local/dev-sync}"
local_env_file="${LECTURE_BOT_LOCAL_ENV_FILE:-$ROOT_DIR/.env.dev-sync}"

if [[ -z "$remote_host" ]]; then
  echo "LECTURE_BOT_REMOTE_HOST is required." >&2
  exit 1
fi

mkdir -p "$local_sync_dir/data/submissions" "$local_sync_dir/lectures" "$local_sync_dir/logs"
mkdir -p "$ROOT_DIR/docs" "$ROOT_DIR/prompts"

ssh_target="${remote_user}@${remote_host}"
ssh_opts=()
if [[ -n "${LECTURE_BOT_SSH_OPTS:-}" ]]; then
  # shellcheck disable=SC2206
  ssh_opts=(${LECTURE_BOT_SSH_OPTS})
fi
rsync_ssh=(ssh)
if [[ ${#ssh_opts[@]} -gt 0 ]]; then
  rsync_ssh+=("${ssh_opts[@]}")
fi

run_rsync() {
  local source_path="$1"
  local dest_path="$2"
  local -a cmd=(rsync -az --delete -e "${rsync_ssh[*]}")
  if [[ $dry_run -eq 1 ]]; then
    cmd+=(--dry-run --itemize-changes)
  fi
  cmd+=("$source_path" "$dest_path")
  printf '==> %s\n' "${cmd[*]}"
  "${cmd[@]}"
}

fetch_remote_file() {
  local remote_path="$1"
  local local_path="$2"
  local -a cmd=(scp)
  if [[ ${#ssh_opts[@]} -gt 0 ]]; then
    cmd+=("${ssh_opts[@]}")
  fi
  if [[ $dry_run -eq 1 ]]; then
    printf '==> %s %s:%s %s\n' "${cmd[*]}" "$ssh_target" "$remote_path" "$local_path"
    return 0
  fi
  printf '==> %s %s:%s %s\n' "${cmd[*]}" "$ssh_target" "$remote_path" "$local_path"
  "${cmd[@]}" "${ssh_target}:${remote_path}" "$local_path"
}

render_local_env() {
  local remote_env_copy="$local_sync_dir/remote.env"
  if [[ $dry_run -eq 1 ]]; then
    cat <<EOF
==> would write $local_env_file from $remote_env_copy with local overrides:
    DATABASE_URL=sqlite:///$local_sync_dir/data/lecture_bot.db
    LECTURES_DIR=$local_sync_dir/lectures
    APP_ENV=dev-sync
    LECTURE_BOT_STUDENT_ROOT_PATH=/bot
    LECTURE_BOT_ADMIN_ROOT_PATH=/bot-admin
EOF
    return 0
  fi

  python - "$remote_env_copy" "$local_env_file" "$local_sync_dir" <<'PY'
from pathlib import Path
import sys

remote_env = Path(sys.argv[1])
local_env = Path(sys.argv[2])
local_sync_dir = Path(sys.argv[3])

values: dict[str, str] = {}
for raw_line in remote_env.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    values[key] = value

values["APP_ENV"] = "dev-sync"
values["DATABASE_URL"] = f"sqlite:///{(local_sync_dir / 'data' / 'lecture_bot.db').as_posix()}"
values["LECTURES_DIR"] = (local_sync_dir / "lectures").as_posix()
values["LECTURE_BOT_STUDENT_ROOT_PATH"] = "/bot"
values["LECTURE_BOT_ADMIN_ROOT_PATH"] = "/bot-admin"

ordered_keys = [
    "APP_NAME",
    "APP_ENV",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "DATABASE_URL",
    "LECTURES_DIR",
    "ADMIN_USERNAME",
    "ADMIN_PASSWORD",
    "LECTURE_BOT_STUDENT_ROOT_PATH",
    "LECTURE_BOT_ADMIN_ROOT_PATH",
    "SESSION_TIMEOUT_MINUTES",
    "SESSION_WARNING_MINUTES",
    "RECENT_MESSAGE_LIMIT",
    "MAX_DIALOGUE_CONTEXT_CHARS",
    "MAX_GRADING_CONTEXT_CHARS",
    "SAMPLED_TOPIC_COUNT",
    "OPENING_TOPIC_CHOICE_COUNT",
]

seen = set()
lines: list[str] = []
for key in ordered_keys:
    if key in values:
        lines.append(f"{key}={values[key]}")
        seen.add(key)
for key in sorted(values):
    if key not in seen:
        lines.append(f"{key}={values[key]}")

local_env.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
  printf 'Wrote %s\n' "$local_env_file"
}

remote_env_path="$remote_root/.env"
fetch_remote_file "$remote_env_path" "$local_sync_dir/remote.env"
run_rsync "$ssh_target:$remote_root/docs/" "$ROOT_DIR/docs/"
run_rsync "$ssh_target:$remote_root/prompts/" "$ROOT_DIR/prompts/"
run_rsync "$ssh_target:$remote_root/data/lecture_bot.db" "$local_sync_dir/data/lecture_bot.db"
run_rsync "$ssh_target:$remote_root/lectures/" "$local_sync_dir/lectures/"
run_rsync "$ssh_target:$remote_root/data/submissions/" "$local_sync_dir/data/submissions/"
run_rsync "$ssh_target:$remote_log_dir/" "$local_sync_dir/logs/"
render_local_env

cat <<EOF

Local development snapshot ready.
  Snapshot dir: $local_sync_dir
  Local env:    $local_env_file

Next steps:
  pixi run dev-synced
  pixi run admin-dev-synced
EOF