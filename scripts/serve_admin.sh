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

host="${LECTURE_BOT_ADMIN_HOST:-127.0.0.1}"
port="${LECTURE_BOT_ADMIN_PORT:-8001}"
reload="${LECTURE_BOT_ADMIN_RELOAD:-0}"
root_path="${LECTURE_BOT_ADMIN_ROOT_PATH:-$(dotenv_value LECTURE_BOT_ADMIN_ROOT_PATH || printf '/bot-admin')}"

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
  app.admin_main:app
  --host "$host"
  --port "$port"
  --root-path "$root_path"
)

if [[ "$reload" == "1" ]]; then
  uvicorn_args+=(--reload)
fi

exec uvicorn "${uvicorn_args[@]}"
