import functools as functools_
import pathlib as pathlib_

import pydantic as pd
import pydantic_settings as ps


class Settings(ps.BaseSettings):
    app_name: str = "lecture-bot"
    app_env: str = "dev"
    database_url: str = pd.Field(default="sqlite:///data/lecture_bot.db")
    lectures_dir: pathlib_.Path = pd.Field(default=pathlib_.Path("lectures"))
    session_timeout_minutes: int = 20
    session_warning_minutes: int = 5
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    recent_message_limit: int = 10
    max_dialogue_context_chars: int = 120000
    max_grading_context_chars: int = 180000
    sampled_topic_count: int = 5
    opening_topic_choice_count: int = 3
    classifier_model: str = "gpt-4.1-mini"
    classifier_recent_message_window: int = 6
    policy_top1_min: float = 0.50
    policy_top2_trigger: float = 0.30
    policy_ambiguity_gap_max: float = 0.20
    clarification_redirect_threshold: int = 3
    prompt_dir: pathlib_.Path = pd.Field(default=pathlib_.Path("prompts/generated"))

    model_config = ps.SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@functools_.lru_cache
def get_settings() -> Settings:
    return Settings()
