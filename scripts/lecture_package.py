"""Check a lecture folder locally, and send it to a course's instance over SSH.

A lecture package is the folder the student app reads for one lecture. These are
conveniences for someone working in a lecture-bot clone; an agent elsewhere uses
the handshake directly. See docs/lecture_package_handshake.md.

    pixi run check-lecture ~/lecture-bot-instances/pml/lectures/lecture_02
    pixi run push-lecture -- pml lecture_02 --dry-run
"""

from __future__ import annotations

import argparse as ap_module
import json as j
import os as os_module
import pathlib as pathlib_
import re as re_module
import shlex as shlex_module
import subprocess as subprocess_module
import sys as sys_module


SCRIPT_DIR = pathlib_.Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys_module.path:
    sys_module.path.insert(0, str(REPO_ROOT))

import app.lecture_packages as lecture_packages


DEFAULT_INSTANCES_ROOT = pathlib_.Path.home() / "lecture-bot-instances"
DEFAULT_REMOTE_ROOT = "/srv/lecture-bot/code"
REMOTE_ENV_FILE = REPO_ROOT / "deploy" / "remote.env"
INSTANCE_EXAMPLES_DIR = REPO_ROOT / "deploy" / "instances"
PROMPT_TEMPLATE_RE = re_module.compile(r"^TUTOR_PROMPT_TEMPLATE=(\S+)", re_module.MULTILINE)


def instance_prompt(course: str) -> str | None:
    """Return the tutor prompt in a course's example settings, the local stand-in for its real settings."""
    settings = INSTANCE_EXAMPLES_DIR / f"{course}.env.example"
    match = PROMPT_TEMPLATE_RE.search(settings.read_text(encoding="utf-8")) if settings.exists() else None
    return match.group(1) if match else None


def check_lecture(lecture_dir: pathlib_.Path) -> lecture_packages.PackageResult:
    """Check a local lecture folder, <course>/lectures/<lecture_id>."""
    lecture_dir = lecture_dir.resolve()
    return lecture_packages.check_package(lecture_dir, instance_prompt(lecture_dir.parent.parent.name))


def format_check(result: lecture_packages.PackageResult) -> str:
    """Render a check result for the researcher and the agent."""
    lines = [f"Lecture {result.lecture_id}: {'OK' if result.ok else 'FAILED'}"]
    for error in result.errors:
        lines.append(f"  error: {error}")
    if result.package_contract:
        lines.append(f"Package contract: {result.package_contract}")
    if result.files:
        lines.append("Files to install:")
        lines.extend(f"  {name} ({result.sizes[name]:,} bytes)" for name in result.files)
    if result.topics:
        lines.append("Topics:")
        lines.extend(f"  {t['topic_id']}. {t['label']}" for t in result.topics)
        lines.append("Load-bearing (for the researcher to confirm):")
        lines.extend(f"  {line}" for line in result.load_bearing or ["(none marked)"])
    return "\n".join(lines)


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


def push_command(env: dict[str, str]) -> list[str]:
    """The ssh command that reaches the server."""
    host = env.get("LECTURE_BOT_REMOTE_HOST")
    if not host:
        raise SystemExit("LECTURE_BOT_REMOTE_HOST is not set (deploy/remote.env).")
    user = env.get("LECTURE_BOT_REMOTE_USER")
    return ["ssh", *shlex_module.split(env.get("LECTURE_BOT_SSH_OPTS", "")), f"{user}@{host}" if user else host]


def remote_command(env: dict[str, str], course: str, lecture_id: str, *, replace: bool, dry_run: bool) -> str:
    """The handshake command to run on the server."""
    root = env.get("LECTURE_BOT_REMOTE_ROOT", DEFAULT_REMOTE_ROOT)
    words = [f"{root}/scripts/lecture-package", "check" if dry_run else "install", course, lecture_id]
    if replace and not dry_run:
        words.append("--replace")
    return shlex_module.join(words)


def push_lecture(
    course: str,
    lecture_id: str,
    *,
    replace: bool = False,
    dry_run: bool = False,
    instances_root: pathlib_.Path = DEFAULT_INSTANCES_ROOT,
    env: dict[str, str] | None = None,
) -> int:
    """Check a local lecture and send it to the instance's install (or, for dry_run, check) operation."""
    env = load_remote_env() if env is None else env
    lecture_dir = instances_root / course / "lectures" / lecture_id
    result = check_lecture(lecture_dir)
    print(format_check(result))
    if not result.ok:
        print("Not pushed: the check failed.", file=sys_module.stderr)
        return 1
    archive = lecture_packages.build_archive(lecture_dir, result.files)
    command = remote_command(env, course, lecture_id, replace=replace, dry_run=dry_run)
    print(f"==> {command}", flush=True)
    completed = subprocess_module.run([*push_command(env), command], input=archive, stdout=subprocess_module.PIPE)
    output = completed.stdout.decode("utf-8", errors="replace").strip()
    try:
        print(j.dumps(j.loads(output), indent=2, ensure_ascii=False))
    except ValueError:
        print(output)
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point for check-lecture and push-lecture."""
    parser = ap_module.ArgumentParser(description=__doc__, formatter_class=ap_module.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    check_parser = sub.add_parser("check", help="Check a lecture folder.")
    check_parser.add_argument("lecture_dir", type=pathlib_.Path)

    push_parser = sub.add_parser("push", help="Send a lecture to its instance, which installs it switched off.")
    push_parser.add_argument("course")
    push_parser.add_argument("lecture_id")
    push_parser.add_argument("--replace", action="store_true", help="Replace a lecture that is switched off.")
    push_parser.add_argument("--dry-run", "-n", action="store_true", help="Run the instance's check; install nothing.")
    push_parser.add_argument("--instances-root", type=pathlib_.Path, default=DEFAULT_INSTANCES_ROOT)

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
    )


if __name__ == "__main__":
    raise SystemExit(main())
