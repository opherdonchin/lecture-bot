"""Check a lecture package and push it, inactive, to a course instance.

A lecture package is the folder the student app reads for one lecture:
``lecture_config.json``, ``rubric.md`` (a rubric or a lecture brief) and the
context files the course lists. A local agent prepares packages by following
the course's recipe; this script checks them with the student app's own loader
and installs them on the server. See the README's "Agent-prepared lectures".

    pixi run check-lecture ~/lecture-bot-instances/pml/lectures/lecture_02
    pixi run push-lecture -- pml lecture_02 --dry-run
"""

from __future__ import annotations

import argparse as ap_module
import dataclasses as dc
import io as io_module
import json as j
import os as os_module
import pathlib as pathlib_
import re as re_module
import shlex as shlex_module
import subprocess as subprocess_module
import sys as sys_module
import tarfile as tarfile_module


SCRIPT_DIR = pathlib_.Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys_module.path:
    sys_module.path.insert(0, str(REPO_ROOT))

import app.bot_engine as bot_engine
import app.lecture_loader as lecture_loader


DEFAULT_INSTANCES_ROOT = pathlib_.Path.home() / "lecture-bot-instances"
DEFAULT_REMOTE_INSTANCES_ROOT = "/srv/lecture-bot/instances"
REMOTE_ENV_FILE = REPO_ROOT / "deploy" / "remote.env"
LOAD_BEARING_RE = re_module.compile(r"^\s*-\s*\*\*Load-bearing:\*\*.*$", re_module.MULTILINE)


@dc.dataclass
class CheckResult:
    """What check_lecture found: the files to install, topics and problems."""

    lecture_id: str
    files: list[str]
    topics: list[dict]
    load_bearing: list[str]
    errors: list[str]
    sizes: dict[str, int]

    @property
    def ok(self) -> bool:
        return not self.errors


def check_lecture(lecture_dir: pathlib_.Path) -> CheckResult:
    """Check a lecture folder the way the student app will load it.

    The folder's parent is the course's lectures folder, whose config.json
    supplies the default context files.
    """
    lecture_dir = lecture_dir.resolve()
    lecture_id = lecture_dir.name
    result = CheckResult(lecture_id, [], [], [], [], {})
    try:
        package = lecture_loader.load_lecture_package(lecture_dir.parent, lecture_id)
    except (FileNotFoundError, ValueError, j.JSONDecodeError) as exc:
        result.errors.append(str(exc))
        return result

    config = package["config"]
    if config.get("lecture_id", lecture_id) != lecture_id:
        result.errors.append(
            f"lecture_config.json has lecture_id {config.get('lecture_id')!r}, but the folder is {lecture_id!r}."
        )

    rubric_topics = bot_engine.parse_rubric_topics(package["rubric"])
    if not rubric_topics:
        result.errors.append("rubric.md has no '### T<n>. <name>' topic headings.")
    missing_importance = [t["topic_id"] for t in rubric_topics if t["importance"] == "unknown"]
    if missing_importance:
        result.errors.append(f"Topics without an '- **Importance:**' line: {', '.join(missing_importance)}.")

    # The app uses the config's topic list in preference to rubric.md's
    # headings, so a stale list would silently override the brief.
    config_topics = package["topics"]
    if config_topics:
        normalized = bot_engine.normalize_topic_defs(config_topics)
        if _topic_signature(normalized) != _topic_signature(rubric_topics):
            result.errors.append(
                "lecture_config.json's 'topics' differ from rubric.md's headings; the app would use the config's. "
                "Remove 'topics' from the config or make them match."
            )

    result.topics = rubric_topics
    result.load_bearing = [line.strip() for line in LOAD_BEARING_RE.findall(package["rubric"])]
    context_paths = [
        item["path"]
        for item in lecture_loader.resolve_context_files(
            lecture_loader.load_lectures_defaults(lecture_dir.parent), config
        )
        if (lecture_dir / item["path"]).exists()
    ]
    result.files = ["lecture_config.json", "rubric.md", *context_paths]
    result.sizes = {name: (lecture_dir / name).stat().st_size for name in result.files}
    return result


def _topic_signature(topics: list[dict]) -> list[tuple[str, str, str]]:
    return [(t["topic_id"], t["label"], t["importance"]) for t in topics]


def format_check(result: CheckResult) -> str:
    """Render a check result for the researcher and the agent."""
    lines = [f"Lecture {result.lecture_id}: {'OK' if result.ok else 'FAILED'}"]
    for error in result.errors:
        lines.append(f"  error: {error}")
    if result.files:
        lines.append("Files to install:")
        lines.extend(f"  {name} ({result.sizes[name]:,} bytes)" for name in result.files)
    if result.topics:
        lines.append("Topics:")
        lines.extend(f"  {t['topic_id']}. {t['label']} [{t['importance']}]" for t in result.topics)
        lines.append("Load-bearing (for the researcher to confirm):")
        lines.extend(f"  {line}" for line in result.load_bearing or ["(none marked)"])
    return "\n".join(lines)


def build_archive(lecture_dir: pathlib_.Path, files: list[str]) -> bytes:
    """Tar the package's files, with the lecture always marked inactive."""
    buffer = io_module.BytesIO()
    with tarfile_module.open(fileobj=buffer, mode="w:gz") as tar:
        for name in files:
            data = (lecture_dir / name).read_bytes()
            if name == "lecture_config.json":
                config = j.loads(data)
                config["active"] = False
                data = (j.dumps(config, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
            info = tarfile_module.TarInfo(name)
            info.size = len(data)
            info.mode = 0o660
            tar.addfile(info, io_module.BytesIO(data))
    return buffer.getvalue()


def remote_install_script(lectures_dir: str, lecture_id: str, *, replace: bool, group: str, dry_run: bool) -> str:
    """Shell script that installs the tar on stdin as <lectures_dir>/<lecture_id>.

    It refuses to overwrite an existing lecture without replace, and never
    replaces an active one. A replaced lecture is moved to
    <instance>/lecture_backups/, outside the folder the app lists.
    """
    q = shlex_module.quote
    return f"""set -euo pipefail
lectures={q(lectures_dir)}
lecture_id={q(lecture_id)}
replace={1 if replace else 0}
dry_run={1 if dry_run else 0}
group={q(group)}
target="$lectures/$lecture_id"
if [[ ! -d "$lectures" ]]; then
  echo "No lectures folder at $lectures." >&2; exit 1
fi
if [[ -e "$target" ]]; then
  if [[ $replace -ne 1 ]]; then
    echo "Refusing: $target already exists. Use --replace to replace it." >&2; exit 1
  fi
  if grep -Eq '"active"[[:space:]]*:[[:space:]]*true' "$target/lecture_config.json" 2>/dev/null; then
    echo "Refusing: $target is active. Switch it off in the admin page first." >&2; exit 1
  fi
fi
staging=$(mktemp -d "$lectures/.push-$lecture_id.XXXXXX")
trap 'rm -rf "$staging"' EXIT
tar -xzf - -C "$staging"
if [[ $dry_run -eq 1 ]]; then
  echo "Dry run: would install into $target:"; ls -l "$staging"; exit 0
fi
if [[ -n "$group" ]] && getent group "$group" >/dev/null; then
  chgrp -R "$group" "$staging"
fi
chmod 2770 "$staging"
chmod 660 "$staging"/*
if [[ -e "$target" ]]; then
  backups="$(dirname "$lectures")/lecture_backups"
  mkdir -p "$backups"
  mv "$target" "$backups/$lecture_id-$(date -u +%Y%m%dT%H%M%SZ)"
  echo "Moved the previous $lecture_id to $backups."
fi
mv "$staging" "$target"
trap - EXIT
echo "Installed $target (inactive)."
"""


def load_remote_env(path: pathlib_.Path = REMOTE_ENV_FILE) -> dict[str, str]:
    """Read deploy/remote.env (KEY=value lines), with the process environment taking precedence."""
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    values.update({k: v for k, v in os_module.environ.items() if k.startswith("LECTURE_BOT_")})
    return values


def push_command(env: dict[str, str], target_dir: pathlib_.Path | None) -> list[str]:
    """The command that runs the install script: local bash for --target-dir, else ssh."""
    if target_dir is not None:
        return ["bash", "-c"]
    host = env.get("LECTURE_BOT_REMOTE_HOST")
    if not host:
        raise SystemExit("LECTURE_BOT_REMOTE_HOST is not set (deploy/remote.env).")
    user = env.get("LECTURE_BOT_REMOTE_USER")
    return ["ssh", *shlex_module.split(env.get("LECTURE_BOT_SSH_OPTS", "")), f"{user}@{host}" if user else host]


def push_lecture(
    course: str,
    lecture_id: str,
    *,
    replace: bool = False,
    dry_run: bool = False,
    instances_root: pathlib_.Path = DEFAULT_INSTANCES_ROOT,
    target_dir: pathlib_.Path | None = None,
    env: dict[str, str] | None = None,
) -> int:
    """Check a local lecture and install it, inactive, in the course's lectures folder.

    target_dir installs into a local lectures folder instead of the server.
    """
    env = load_remote_env() if env is None else env
    lecture_dir = instances_root / course / "lectures" / lecture_id
    result = check_lecture(lecture_dir)
    print(format_check(result))
    if not result.ok:
        print("Not pushed: the check failed.", file=sys_module.stderr)
        return 1

    if target_dir is not None:
        lectures_dir = str(target_dir)
    else:
        root = env.get("LECTURE_BOT_REMOTE_INSTANCES_ROOT", DEFAULT_REMOTE_INSTANCES_ROOT)
        lectures_dir = f"{root}/{course}/lectures"
    script = remote_install_script(
        lectures_dir,
        lecture_id,
        replace=replace,
        group=env.get("LECTURE_BOT_REMOTE_APP_GROUP", "appops"),
        dry_run=dry_run,
    )
    # The script runs as the command and reads the package archive on stdin.
    runner = push_command(env, target_dir)
    print(f"==> {' '.join(runner)}: {lectures_dir}/{lecture_id}")
    completed = subprocess_module.run([*runner, script], input=build_archive(lecture_dir, result.files))
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point for check-lecture and push-lecture."""
    parser = ap_module.ArgumentParser(description=__doc__, formatter_class=ap_module.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    check_parser = sub.add_parser("check", help="Check a lecture folder.")
    check_parser.add_argument("lecture_dir", type=pathlib_.Path)

    push_parser = sub.add_parser("push", help="Check and install a lecture, inactive, on the server.")
    push_parser.add_argument("course")
    push_parser.add_argument("lecture_id")
    push_parser.add_argument("--replace", action="store_true", help="Replace an existing, inactive lecture.")
    push_parser.add_argument("--dry-run", "-n", action="store_true", help="Show what would be installed.")
    push_parser.add_argument("--instances-root", type=pathlib_.Path, default=DEFAULT_INSTANCES_ROOT)
    push_parser.add_argument("--target-dir", type=pathlib_.Path, help="Install into this local lectures folder instead.")

    args = parser.parse_args(argv)
    if args.command == "check":
        result = check_lecture(args.lecture_dir.expanduser())
        print(format_check(result))
        return 0 if result.ok else 1
    return push_lecture(
        args.course,
        args.lecture_id,
        replace=args.replace,
        dry_run=args.dry_run,
        instances_root=args.instances_root.expanduser(),
        target_dir=args.target_dir.expanduser() if args.target_dir else None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
