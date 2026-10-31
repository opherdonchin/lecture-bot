import functools as functools_
import json as json_
import pathlib as pathlib_
import re as re_

_REPO_ROOT = pathlib_.Path(__file__).resolve().parent.parent
_PROMPTS_DIR = _REPO_ROOT / "prompts"
_PLACEHOLDER_RE = re_.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")

# The backend-tutor contract this code implements, named by the development
# version in which the contract last changed (docs/backend_tutor_contract.md).
# A tutor prompt declares the contract it was written for on its first line;
# a prompt declaring another version, or none, is not loaded.
BACKEND_CONTRACT_VERSION = "0.7.0"
_CONTRACT_DECLARATION_RE = re_.compile(r"\ABackend contract: *(\S+)[ \t]*\r?\n(?:[ \t]*\r?\n)?")
# A prompt may also declare the lecture package it expects, next after that line
# (docs/lecture_package_contracts/). The package check compares it with the
# package when a lecture is prepared; nothing checks it while the app runs.
_PACKAGE_DECLARATION_RE = re_.compile(r"\ALecture package contract: *(\S+)[ \t]*\r?\n(?:[ \t]*\r?\n)?")
# A prompt may end with this section, which the backend repeats after the
# student's latest message on every turn (docs/backend_tutor_contract.md).
TURN_REMINDER_HEADING = "## Turn reminder"


@functools_.lru_cache
def load_prompt_template(template_name: str) -> str:
    template_path = _PROMPTS_DIR / template_name
    return template_path.read_text(encoding="utf-8")


def private_artifact_schema_path(template_name: str) -> pathlib_.Path:
    template_path = _PROMPTS_DIR / template_name
    return template_path.with_name(f"{template_path.stem}_private_artifact_schema.json")


def tutor_document_paths(template_name: str, repo_root: pathlib_.Path) -> dict[str, pathlib_.Path]:
    """Return where a tutor's prompt, schema and specification live, named after its prompt file."""
    prompts_dir = repo_root / "prompts"
    stem = pathlib_.Path(template_name).stem
    return {
        "tutor_prompt": prompts_dir / template_name,
        "tutor_artifact_schema": prompts_dir / f"{stem}_private_artifact_schema.json",
        "tutor_spec": repo_root / "docs" / f"{stem.replace('tutor_prompt', 'tutor_specification')}.md",
    }


def load_private_artifact_schema_json(template_name: str) -> str | None:
    schema_path = private_artifact_schema_path(template_name)
    if not schema_path.exists():
        return None
    schema_text = schema_path.read_text(encoding="utf-8")
    schema = json_.loads(schema_text)
    return json_.dumps(schema, indent=2, ensure_ascii=False)


def render_prompt_template(template_name: str, values: dict) -> str:
    missing: list[str] = []
    template = load_prompt_template(template_name)

    def replace(match):
        key = match.group(1)
        if key not in values:
            missing.append(key)
            return match.group(0)
        return str(values[key])

    rendered = _PLACEHOLDER_RE.sub(replace, template)
    if missing:
        missing_text = ", ".join(sorted(set(missing)))
        raise KeyError(f"Missing prompt template values for: {missing_text}")
    return rendered


def declared_backend_contract(prompt_text: str) -> str | None:
    """Return the backend contract version a prompt declares on its first line, if any."""
    match = _CONTRACT_DECLARATION_RE.match(prompt_text)
    return match.group(1) if match else None


def declared_package_contract(prompt_text: str) -> str | None:
    """Return the lecture package contract a prompt declares after its backend contract, if any."""
    match = _PACKAGE_DECLARATION_RE.match(_CONTRACT_DECLARATION_RE.sub("", prompt_text, count=1))
    return match.group(1) if match else None


def turn_reminder(prompt_text: str) -> str | None:
    """Return the text of the prompt's final Turn reminder section, if it has one."""
    _, heading, reminder = prompt_text.rpartition(TURN_REMINDER_HEADING)
    return reminder.strip() or None if heading else None


def strip_contract_declaration(prompt_text: str) -> str:
    """Return the prompt without its contract declaration lines, as the model should see it."""
    without_backend = _CONTRACT_DECLARATION_RE.sub("", prompt_text, count=1)
    return _PACKAGE_DECLARATION_RE.sub("", without_backend, count=1)


def prompt_contract_problem(template_name: str) -> str | None:
    """Return why a tutor prompt cannot run under this backend, or None if it can."""
    try:
        declared = declared_backend_contract(load_prompt_template(template_name))
    except OSError as error:
        return f"tutor prompt {template_name!r} cannot be read: {error}"
    if declared is None:
        return (
            f"tutor prompt {template_name!r} declares no backend contract; "
            f"this backend implements contract {BACKEND_CONTRACT_VERSION}"
        )
    if declared != BACKEND_CONTRACT_VERSION:
        return (
            f"tutor prompt {template_name!r} was written for backend contract {declared}; "
            f"this backend implements contract {BACKEND_CONTRACT_VERSION}"
        )
    return None
