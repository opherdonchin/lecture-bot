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
Usage: scripts/publish_production.sh [--dry-run] [--revision <commit>]

Deploy merged code to the production server through git. On the server this
fast-forwards the checkout to origin/main (or resets it to --revision, a tag or
commit, for a specific release or a rollback), refreshes the Pixi environment,
restarts every course instance and checks its health. Nothing is copied from this machine, so local files,
lectures and other untracked server files are never touched.

The deploy refuses to run when the server checkout has local changes or is
not on main.

Required environment:
  LECTURE_BOT_REMOTE_HOST         SSH host for the production server
  LECTURE_BOT_REMOTE_INSTANCES    Space-separated <instance>=<path> pairs, e.g.
                                  "statistics=/stats pml=/pml". Each restarts
                                  lecture-bot@<instance> and
                                  lecture-bot-admin@<instance> and checks
                                  <path>/health and <path>-admin/.

Optional environment:
  LECTURE_BOT_REMOTE_USER         SSH user (default: current SSH config)
  LECTURE_BOT_REMOTE_ROOT         Remote code checkout (default: /srv/lecture-bot/code)
  LECTURE_BOT_REMOTE_APP_GROUP    Shared runtime group (default: appops)
  LECTURE_BOT_REMOTE_PIXI_BIN     Remote Pixi binary (default: pixi)
  LECTURE_BOT_SSH_OPTS            Extra ssh options, appended as words

Examples:
  pixi run publish-prod -- --dry-run
  pixi run publish-prod
  pixi run publish-prod -- --revision v0.4.0     # a specific release, or a rollback
EOF
}

dry_run=0
revision=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run|-n)
      dry_run=1
      shift
      ;;
    --revision)
      revision="${2:-}"
      if [[ -z "$revision" ]]; then
        echo "--revision needs a commit." >&2
        exit 1
      fi
      shift 2
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

if ! command -v ssh >/dev/null 2>&1; then
  echo "Missing required command: ssh" >&2
  exit 1
fi

remote_host="${LECTURE_BOT_REMOTE_HOST:-}"
remote_user="${LECTURE_BOT_REMOTE_USER:-}"
remote_root="${LECTURE_BOT_REMOTE_ROOT:-/srv/lecture-bot/code}"
remote_app_group="${LECTURE_BOT_REMOTE_APP_GROUP:-appops}"
remote_pixi_bin="${LECTURE_BOT_REMOTE_PIXI_BIN:-pixi}"
instances="${LECTURE_BOT_REMOTE_INSTANCES:-}"

if [[ -z "$remote_host" ]]; then
  echo "LECTURE_BOT_REMOTE_HOST is required." >&2
  exit 1
fi
if [[ -z "$instances" ]]; then
  echo "LECTURE_BOT_REMOTE_INSTANCES is required." >&2
  exit 1
fi

ssh_target="$remote_host"
if [[ -n "$remote_user" ]]; then
  ssh_target="${remote_user}@${remote_host}"
fi
ssh_cmd=(ssh)
if [[ -n "${LECTURE_BOT_SSH_OPTS:-}" ]]; then
  # shellcheck disable=SC2206
  ssh_cmd+=(${LECTURE_BOT_SSH_OPTS})
fi
ssh_cmd+=("$ssh_target")

# Each check is "<service>|<health url>|<admin url>".
checks=()
for pair in $instances; do
  name="${pair%%=*}"
  path="${pair#*=}"
  if [[ -z "$name" || "$path" != /* || "$pair" != *=* ]]; then
    echo "Bad LECTURE_BOT_REMOTE_INSTANCES entry: $pair (expected <instance>=/<path>)" >&2
    exit 1
  fi
  checks+=("lecture-bot@${name}.service lecture-bot-admin@${name}.service|http://127.0.0.1${path}/health|http://127.0.0.1${path}-admin/")
done

read -r -d '' remote_script <<EOF || true
set -euo pipefail
cd "$remote_root"
dry_run=$dry_run
revision="$revision"

branch=\$(git rev-parse --abbrev-ref HEAD)
if [[ -n "\$(git status --porcelain --untracked-files=no)" ]]; then
  echo "Refusing to deploy: the server checkout has local changes." >&2
  git status --short --untracked-files=no >&2
  exit 1
fi
if [[ "\$branch" != "main" ]]; then
  echo "Refusing to deploy: the server checkout is on '\$branch', not main." >&2
  exit 1
fi

git fetch --quiet --tags origin
previous=\$(git rev-parse --short HEAD)
if [[ -n "\$revision" ]]; then
  target=\$(git rev-parse --short "\$revision^{commit}")
else
  target=\$(git rev-parse --short origin/main)
  if ! git merge-base --is-ancestor HEAD origin/main; then
    echo "Refusing to deploy: server main (\$previous) is not an ancestor of origin/main." >&2
    exit 1
  fi
fi
echo "Server is at \$previous; deploying \$target."
echo "To roll back afterwards: pixi run publish-prod -- --revision \$previous"
if [[ \$dry_run -eq 1 ]]; then
  git log --oneline "\$previous..\$target"
  exit 0
fi

if [[ -n "\$revision" ]]; then
  git reset --hard --quiet "\$target"
else
  git merge --ff-only --quiet origin/main
fi
"$remote_pixi_bin" install --locked
# Repair only what this account owns; anything else is not ours to change.
find .pixi -user "\$(id -un)" -exec chgrp "$remote_app_group" {} +
find .pixi -user "\$(id -un)" -exec chmod g+rX {} +

check_failed=0
while IFS='|' read -r services health_url admin_url; do
  # shellcheck disable=SC2086
  sudo -n systemctl restart \$services
  sleep 2
  if ! curl --fail --silent --show-error --retry 5 --retry-delay 2 --retry-connrefused "\$health_url" >/dev/null; then
    echo "Health check failed: \$health_url" >&2
    check_failed=1
  fi
  admin_status=\$(curl --silent --output /dev/null --write-out '%{http_code}' "\$admin_url")
  if [[ "\$admin_status" != "401" && "\$admin_status" != "200" ]]; then
    echo "Admin check failed with HTTP \$admin_status: \$admin_url" >&2
    check_failed=1
  fi
done <<'CHECKS'
$(printf '%s\n' "${checks[@]}")
CHECKS
if [[ \$check_failed -ne 0 ]]; then
  echo "Deployed \$target but a check failed. Roll back with: pixi run publish-prod -- --revision \$previous" >&2
  exit 1
fi
echo "Deployed \$target; all instances healthy."
EOF

printf '==> %s <<REMOTE\n' "${ssh_cmd[*]}"
"${ssh_cmd[@]}" "$remote_script"
