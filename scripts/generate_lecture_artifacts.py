from __future__ import annotations

import json as j_
import pathlib as pathlib_

import openai as openai_

import app.config as config_module
import app.prompt_loader as prompt_loader


def _require_api_key() -> str:
    settings = config_module.get_settings()
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required to generate lecture artifacts such as minutes.json and rubric.md."
        )
    return settings.openai_api_key


def _build_user_message(prompt_name: str, source_paths: dict[str, pathlib_.Path]) -> str:
    prompt_text = prompt_loader.load_prompt_template(prompt_name).strip()
    parts = [prompt_text, "", "Source file contents", ""]

    for label, path in source_paths.items():
        parts.append(f"## {label} ({path.name})")
        parts.append(path.read_text(encoding="utf-8").strip())
        parts.append("")

    return "\n".join(parts).strip()


def _call_chat_completion(
    *,
    prompt_name: str,
    source_paths: dict[str, pathlib_.Path],
    expect_json: bool,
) -> str:
    settings = config_module.get_settings()
    client = openai_.OpenAI(api_key=_require_api_key(), timeout=120.0, max_retries=0)
    create_kwargs = {
        "model": settings.openai_model,
        "messages": [
            {
                "role": "system",
                "content": "Follow the user's artifact-generation instructions exactly.",
            },
            {
                "role": "user",
                "content": _build_user_message(prompt_name, source_paths),
            },
        ],
        "temperature": 0.2,
    }
    if expect_json:
        create_kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**create_kwargs)
    content = response.choices[0].message.content
    if not content:
        raise ValueError(f"Model returned empty content while generating {prompt_name}")
    return content


def generate_instructional_minutes(
    source_paths: dict[str, str | pathlib_.Path],
    target: str | pathlib_.Path,
) -> pathlib_.Path:
    ordered_sources = {
        "Slides": pathlib_.Path(source_paths["slides"]),
        "Handout": pathlib_.Path(source_paths["handout"]),
        "Notebook": pathlib_.Path(source_paths["notebook"]),
        "Transcript": pathlib_.Path(source_paths["transcript"]),
    }
    raw = _call_chat_completion(
        prompt_name="minutes_generation_prompt.md",
        source_paths=ordered_sources,
        expect_json=True,
    )
    parsed = j_.loads(raw)

    target_path = pathlib_.Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(j_.dumps(parsed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target_path


def generate_master_rubric(
    source_paths: dict[str, str | pathlib_.Path],
    target: str | pathlib_.Path,
) -> pathlib_.Path:
    ordered_sources = {
        "Slides": pathlib_.Path(source_paths["slides"]),
        "Handout": pathlib_.Path(source_paths["handout"]),
        "Notebook": pathlib_.Path(source_paths["notebook"]),
        "Instructional Minutes": pathlib_.Path(source_paths["minutes"]),
    }
    rubric_text = _call_chat_completion(
        prompt_name="master_rubric_generation_prompt.md",
        source_paths=ordered_sources,
        expect_json=False,
    ).strip()

    target_path = pathlib_.Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(rubric_text + "\n", encoding="utf-8")
    return target_path
