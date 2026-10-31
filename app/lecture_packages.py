"""The lecture package handshake: what an instance expects, and checking and installing a package.

Every route to an instance (the command on the server, the admin page, and later
machine-facing hooks) calls these functions, so that it gives the same result.
docs/lecture_package_handshake.md is the authoritative description.
"""

from __future__ import annotations

import dataclasses as dc
import datetime as dt
import io as io_module
import json as j
import os as os_module
import pathlib as pathlib_
import re as re_module
import shutil as shutil_module
import stat as stat_module
import tempfile as tempfile_module
import zipfile as zipfile_module

import app.bot_engine as bot_engine
import app.lecture_loader as lecture_loader
import app.prompt_loader as prompt_loader


HANDSHAKE_VERSION = 1
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
MAX_ARCHIVE_FILES = 50

REPO_ROOT = pathlib_.Path(__file__).resolve().parent.parent
PACKAGE_CONTRACTS_DIR = REPO_ROOT / "docs" / "lecture_package_contracts"
SHARED_RULES_FILE = REPO_ROOT / "docs" / "lecture_package_contract.md"
INSTRUCTIONS_FILE = REPO_ROOT / ".agents" / "skills" / "prepare-lecture" / "SKILL.md"

_LOAD_BEARING_RE = re_module.compile(r"^\s*-\s*\*\*Load-bearing:\*\*.*$", re_module.MULTILINE)
_LECTURE_ID_RE = re_module.compile(r"\A[A-Za-z0-9_-]+\Z")
_PROMPT_NAME_RE = re_module.compile(r"\A[A-Za-z0-9_][A-Za-z0-9_.-]*\Z")


class ArchiveError(ValueError):
    """A package archive that cannot be accepted."""


@dc.dataclass
class PackageResult:
    """The result of checking or installing a package, the same on every route."""

    lecture_id: str
    package_contract: str | None = None
    files: list[str] = dc.field(default_factory=list)
    topics: list[dict] = dc.field(default_factory=list)
    load_bearing: list[str] = dc.field(default_factory=list)
    errors: list[str] = dc.field(default_factory=list)
    installed: bool = False
    message: str = ""
    sizes: dict[str, int] = dc.field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        """Return the result in the form the handshake documents."""
        return {
            "handshake": HANDSHAKE_VERSION,
            "ok": self.ok,
            "lecture_id": self.lecture_id,
            "package_contract": self.package_contract,
            "files": self.files,
            "topics": [{"topic_id": t["topic_id"], "label": t["label"]} for t in self.topics],
            "load_bearing": self.load_bearing,
            "errors": self.errors,
            "installed": self.installed,
            "message": self.message,
        }


def contract_problem(declared: str | None, template: str | None) -> str | None:
    """Return why a package's declared contract does not match the one its tutor prompt declares."""
    if template is None:
        return "Cannot find the tutor prompt for this lecture."
    if not _PROMPT_NAME_RE.match(template):
        return f"Tutor prompt {template!r} is not a file name in prompts/."
    try:
        expected = prompt_loader.declared_package_contract(prompt_loader.load_prompt_template(template))
    except OSError as error:
        return f"Cannot read tutor prompt {template!r}: {error}"
    if expected is None:
        return f"Tutor prompt {template} declares no lecture package contract."
    contract_file = PACKAGE_CONTRACTS_DIR / f"{expected}.md"
    if not contract_file.exists():
        return f"Tutor prompt {template} declares contract {expected!r}, which has no file at {contract_file.name}."
    if declared != expected:
        return (
            f"lecture_config.json declares package_contract {declared!r}, but tutor prompt {template} "
            f"expects {expected!r}. See docs/lecture_package_contracts/{contract_file.name}."
        )
    return None


def _topic_signature(topics: list[dict]) -> list[tuple[str, str, str]]:
    return [(t["topic_id"], t["label"], t["importance"]) for t in topics]


def check_package(lecture_dir: pathlib_.Path, instance_prompt: str | None) -> PackageResult:
    """Check a lecture folder the way the student app will load it.

    The folder's parent supplies the course's config.json, as the lectures folder
    does in the app. The prompt is the lecture's own tutor_prompt_template if it
    sets one, as in the app, and otherwise instance_prompt.
    """
    lecture_dir = lecture_dir.resolve()
    lecture_id = lecture_dir.name
    result = PackageResult(lecture_id)
    try:
        package = lecture_loader.load_lecture_package(lecture_dir.parent, lecture_id)
    except (FileNotFoundError, ValueError, AttributeError) as exc:
        result.errors.append(f"The package cannot be loaded: {exc}")
        return result

    config = package["config"]
    if config.get("lecture_id", lecture_id) != lecture_id:
        result.errors.append(
            f"lecture_config.json has lecture_id {config.get('lecture_id')!r}, but the folder is {lecture_id!r}."
        )

    result.package_contract = config.get("package_contract")
    problem = contract_problem(result.package_contract, config.get("tutor_prompt_template", instance_prompt))
    if problem:
        result.errors.append(problem)

    rubric_topics = bot_engine.parse_rubric_topics(package["rubric"])
    if not rubric_topics:
        result.errors.append("rubric.md has no '### T<n>. <name>' topic headings.")

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
    result.load_bearing = [line.strip() for line in _LOAD_BEARING_RE.findall(package["rubric"])]
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


def describe_expectations(instance_prompt: str | None) -> dict:
    """Return what an instance expects of a package: its contract, the shared rules and the instructions."""
    response = {"handshake": HANDSHAKE_VERSION, "ok": False, "errors": []}
    try:
        name = prompt_loader.declared_package_contract(prompt_loader.load_prompt_template(instance_prompt or ""))
    except OSError as error:
        response["errors"].append(f"Cannot read tutor prompt {instance_prompt!r}: {error}")
        return response
    if name is None:
        response["errors"].append(f"Tutor prompt {instance_prompt} declares no lecture package contract.")
        return response
    contract_file = PACKAGE_CONTRACTS_DIR / f"{name}.md"
    if not contract_file.exists():
        response["errors"].append(f"Contract {name!r} has no file at {contract_file.name}.")
        return response
    response.update(
        ok=True,
        package_contract=name,
        contract=contract_file.read_text(encoding="utf-8"),
        shared_rules=SHARED_RULES_FILE.read_text(encoding="utf-8"),
        instructions=INSTRUCTIONS_FILE.read_text(encoding="utf-8"),
    )
    return response


def read_archive(data: bytes) -> dict[str, bytes]:
    """Return a package archive's files, refusing anything but a small, flat .zip of regular files."""
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ArchiveError(f"The archive is larger than {MAX_ARCHIVE_BYTES} bytes.")
    try:
        archive = zipfile_module.ZipFile(io_module.BytesIO(data))
    except zipfile_module.BadZipFile as error:
        raise ArchiveError("The archive is not a valid .zip file.") from error
    with archive:
        entries = archive.infolist()
        if len(entries) > MAX_ARCHIVE_FILES:
            raise ArchiveError(f"The archive has more than {MAX_ARCHIVE_FILES} files.")
        if sum(entry.file_size for entry in entries) > MAX_ARCHIVE_BYTES:
            raise ArchiveError(f"The archive unpacks to more than {MAX_ARCHIVE_BYTES} bytes.")
        files: dict[str, bytes] = {}
        for entry in entries:
            name = entry.filename
            is_symlink = stat_module.S_ISLNK(entry.external_attr >> 16)
            if entry.is_dir() or is_symlink or "/" in name or "\\" in name or name in {"", ".", ".."}:
                raise ArchiveError(f"Archive entry {name!r} is not a file at the top level of the archive.")
            if name in files:
                raise ArchiveError(f"Archive entry {name!r} appears twice.")
            try:
                files[name] = archive.read(entry)
            except (zipfile_module.BadZipFile, RuntimeError, EOFError) as error:
                raise ArchiveError(f"Archive entry {name!r} cannot be read: {error}") from error
    return files


def _write_staged(staging: pathlib_.Path, lectures_dir: pathlib_.Path, lecture_id: str, files: dict[str, bytes]) -> pathlib_.Path:
    """Write a package under staging as <lecture_id>/, beside a copy of the course's config.json."""
    package_dir = staging / lecture_id
    package_dir.mkdir()
    for name, content in files.items():
        (package_dir / name).write_bytes(content)
    course_config = lectures_dir / "config.json"
    if course_config.exists():
        shutil_module.copyfile(course_config, staging / "config.json")
    return package_dir


def _check_staged(package_dir: pathlib_.Path, files: dict[str, bytes], instance_prompt: str | None) -> PackageResult:
    result = check_package(package_dir, instance_prompt)
    if result.files:
        extra = sorted(set(files) - set(result.files))
        if extra:
            result.errors.append(f"The archive has files the app does not read: {', '.join(extra)}.")
    return result


def check_archive(
    lectures_dir: pathlib_.Path, lecture_id: str, data: bytes, instance_prompt: str | None
) -> PackageResult:
    """Check a package archive against an instance, installing nothing."""
    result = PackageResult(lecture_id)
    if not _LECTURE_ID_RE.match(lecture_id):
        result.errors.append(f"{lecture_id!r} is not a valid lecture id.")
        return result
    try:
        files = read_archive(data)
    except ArchiveError as error:
        result.errors.append(str(error))
        return result
    with tempfile_module.TemporaryDirectory() as staging:
        package_dir = _write_staged(pathlib_.Path(staging), lectures_dir, lecture_id, files)
        return _check_staged(package_dir, files, instance_prompt)


def _refusal_to_replace(target: pathlib_.Path, replace: bool) -> str | None:
    """Return why an existing lecture must not be replaced. The app treats a missing active setting as on."""
    if not target.exists():
        return None
    if not replace:
        return f"{target.name} is already installed. Ask to replace it."
    try:
        config = j.loads((target / "lecture_config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        config = {}
    if config.get("active", True) is not False:
        return f"{target.name} is not marked as off. Switch it off in the admin page first."
    return None


def install_archive(
    lectures_dir: pathlib_.Path, lecture_id: str, data: bytes, instance_prompt: str | None, *, replace: bool = False
) -> PackageResult:
    """Check a package archive and install it, always switched off.

    It is unpacked beside the lectures and moved into place last. A replaced
    lecture moves to the instance's lecture_backups folder.
    """
    result = check_archive(lectures_dir, lecture_id, data, instance_prompt)
    if not result.ok:
        return result
    target = lectures_dir / lecture_id
    refusal = _refusal_to_replace(target, replace)
    if refusal:
        result.errors.append(refusal)
        return result

    files = read_archive(data)
    config = j.loads(files["lecture_config.json"])
    config["active"] = False
    files["lecture_config.json"] = (j.dumps(config, indent=2, ensure_ascii=False) + "\n").encode("utf-8")

    staging = None
    try:
        staging = pathlib_.Path(tempfile_module.mkdtemp(prefix=f".push-{lecture_id}.", dir=lectures_dir))
        package_dir = staging / lecture_id
        package_dir.mkdir()
        for name, content in files.items():
            (package_dir / name).write_bytes(content)
            os_module.chmod(package_dir / name, 0o660)
        os_module.chmod(package_dir, 0o2770)
        messages = []
        if target.exists():
            backups = lectures_dir.parent / "lecture_backups"
            backups.mkdir(exist_ok=True)
            stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            target.rename(backups / f"{lecture_id}-{stamp}")
            messages.append(f"Moved the previous {lecture_id} to lecture_backups.")
        package_dir.rename(target)
    except OSError as error:
        result.errors.append(f"Could not install {lecture_id}: {error}")
        return result
    finally:
        if staging is not None:
            shutil_module.rmtree(staging, ignore_errors=True)
    result.installed = True
    result.message = " ".join([*messages, f"Installed {lecture_id}, switched off."])
    return result


def build_archive(lecture_dir: pathlib_.Path, files: list[str]) -> bytes:
    """Build a package archive from a lecture folder's files."""
    buffer = io_module.BytesIO()
    with zipfile_module.ZipFile(buffer, "w", zipfile_module.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(lecture_dir / name, arcname=name)
    return buffer.getvalue()
