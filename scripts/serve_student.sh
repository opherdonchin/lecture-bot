#!/usr/bin/env bash
set -euo pipefail

dotenv_value() {
  local key="$1"
  local env_file="${2:-.env}"
  if [[ ! -f "$env_file" ]]; then
    return 1
  fi
  local line
  line="$(grep -E "^${key}=" "$env_file" | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    return 1
  fi
  printf '%s' "${line#*=}"
}

host="${LECTURE_BOT_STUDENT_HOST:-127.0.0.1}"
port="${LECTURE_BOT_STUDENT_PORT:-8000}"
reload="${LECTURE_BOT_STUDENT_RELOAD:-0}"
root_path="${LECTURE_BOT_STUDENT_ROOT_PATH:-$(dotenv_value LECTURE_BOT_STUDENT_ROOT_PATH || printf '/bot')}"

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

uvicorn_args=(
  app.main:app
  --host "$host"
  --port "$port"
  --root-path "$root_path"
)

if [[ "$reload" == "1" ]]; then
  uvicorn_args+=(--reload)
fi

exec uvicorn "${uvicorn_args[@]}"
