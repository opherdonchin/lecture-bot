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
Usage: scripts/publish_production.sh [--dry-run]

Push the current repo checkout to the production server, refresh the remote
Pixi environment, repair shared permissions, restart services, and verify
health checks.

Required environment:
  LECTURE_BOT_REMOTE_HOST         SSH host for the production server

Optional environment:
  LECTURE_BOT_REMOTE_USER         SSH user (default: lecture-bot)
  LECTURE_BOT_REMOTE_ROOT         Remote repo root (default: /srv/lecture-bot)
  LECTURE_BOT_REMOTE_REPO_PATH    Backward-compatible alias for the remote repo root
  LECTURE_BOT_REMOTE_APP_GROUP    Shared runtime group (default: appops)
  LECTURE_BOT_REMOTE_PIXI_BIN     Remote Pixi binary (default: pixi)
  LECTURE_BOT_REMOTE_STUDENT_SERVICE Remote student service name (default: lecture-bot)
  LECTURE_BOT_REMOTE_ADMIN_SERVICE   Remote admin service name (default: lecture-bot-admin)
  LECTURE_BOT_REMOTE_STUDENT_HEALTH_URL  Local student health URL (default: http://127.0.0.1/stats/health)
  LECTURE_BOT_REMOTE_ADMIN_URL    Local admin URL (default: http://127.0.0.1/stats-admin/)
  LECTURE_BOT_SSH_OPTS            Extra ssh options, appended as words

Examples:
  LECTURE_BOT_REMOTE_HOST=prod.example.edu pixi run publish-prod
  LECTURE_BOT_REMOTE_HOST=prod.example.edu pixi run publish-prod -- --dry-run
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
remote_app_group="${LECTURE_BOT_REMOTE_APP_GROUP:-appops}"
remote_pixi_bin="${LECTURE_BOT_REMOTE_PIXI_BIN:-pixi}"
student_service="${LECTURE_BOT_REMOTE_STUDENT_SERVICE:-lecture-bot}"
admin_service="${LECTURE_BOT_REMOTE_ADMIN_SERVICE:-lecture-bot-admin}"
student_health_url="${LECTURE_BOT_REMOTE_STUDENT_HEALTH_URL:-http://127.0.0.1/stats/health}"
admin_url="${LECTURE_BOT_REMOTE_ADMIN_URL:-http://127.0.0.1/stats-admin/}"

if [[ -z "$remote_host" ]]; then
  echo "LECTURE_BOT_REMOTE_HOST is required." >&2
  exit 1
fi

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

rsync_cmd=(
  rsync -az --delete
  --exclude=.git/
  --exclude=.pixi/
  --exclude=__pycache__/
  --exclude=.pytest_cache/
  --exclude=.local/
  --exclude=.env
  --exclude=.env.*
  --exclude=data/
  --exclude=exports/
  --exclude=app.log
  --exclude=admin.log
  -e "${rsync_ssh[*]}"
)
if [[ $dry_run -eq 1 ]]; then
  rsync_cmd+=(--dry-run --itemize-changes)
fi
rsync_cmd+=("$ROOT_DIR/" "$ssh_target:$remote_root/")

printf '==> %s\n' "${rsync_cmd[*]}"
"${rsync_cmd[@]}"

read -r -d '' remote_script <<EOF || true
set -euo pipefail
cd "$remote_root"
"$remote_pixi_bin" install
chgrp -R "$remote_app_group" .pixi
chmod -R g+rX .pixi
find .pixi -type d -exec chmod g+rx {} \;
sudo -n systemctl restart "$student_service" "$admin_service"
curl --fail --silent --show-error "$student_health_url" >/dev/null
admin_status=\$(curl --silent --output /dev/null --write-out '%{http_code}' "$admin_url")
if [[ "\$admin_status" != "401" && "\$admin_status" != "200" ]]; then
  echo "Admin health check failed with HTTP \$admin_status" >&2
  exit 1
fi
sudo -n systemctl status "$student_service" "$admin_service" --no-pager -l
EOF

ssh_cmd=(ssh)
if [[ ${#ssh_opts[@]} -gt 0 ]]; then
  ssh_cmd+=("${ssh_opts[@]}")
fi
ssh_cmd+=("$ssh_target")

if [[ $dry_run -eq 1 ]]; then
  printf '==> %s <<REMOTE\n%s\nREMOTE\n' "${ssh_cmd[*]}" "$remote_script"
  exit 0
fi

printf '==> %s <<REMOTE\n' "${ssh_cmd[*]}"
"${ssh_cmd[@]}" "$remote_script"