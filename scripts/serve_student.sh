#!/usr/bin/env bash
set -euo pipefail

host="${LECTURE_BOT_STUDENT_HOST:-127.0.0.1}"
port="${LECTURE_BOT_STUDENT_PORT:-8000}"
root_path="${LECTURE_BOT_STUDENT_ROOT_PATH:-/bot}"

normalize_root_path() {
  local value="$1"
  if [[ -z "$value" || "$value" == "/" ]]; then
    printf ''
    return
  fi
  if [[ "$value" != /* ]]; then
    value="/$value"
  fi
  printf '%s' "${value%/}"
}

root_path="$(normalize_root_path "$root_path")"

exec uvicorn app.main:app \
  --host "$host" \
  --port "$port" \
  --root-path "$root_path"
