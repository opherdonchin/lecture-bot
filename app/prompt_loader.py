import functools as functools_
import pathlib as pathlib_
import re as re_

_REPO_ROOT = pathlib_.Path(__file__).resolve().parent.parent
_PROMPTS_DIR = _REPO_ROOT / "prompts"
_PLACEHOLDER_RE = re_.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")


@functools_.lru_cache
def load_prompt_template(template_name: str) -> str:
    template_path = _PROMPTS_DIR / template_name
    return template_path.read_text(encoding="utf-8")


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
