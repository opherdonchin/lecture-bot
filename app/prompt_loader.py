import functools as functools_
import json as json_
import pathlib as pathlib_
import re as re_

_REPO_ROOT = pathlib_.Path(__file__).resolve().parent.parent
_PROMPTS_DIR = _REPO_ROOT / "prompts"
_PLACEHOLDER_RE = re_.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")


@functools_.lru_cache
def load_prompt_template(template_name: str) -> str:
    template_path = _PROMPTS_DIR / template_name
    return template_path.read_text(encoding="utf-8")


def private_artifact_schema_path(template_name: str) -> pathlib_.Path:
    template_path = _PROMPTS_DIR / template_name
    return template_path.with_name(f"{template_path.stem}_private_artifact_schema.json")


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
