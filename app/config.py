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
    openai_api_key: str | None = None

    model_config = ps.SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@functools_.lru_cache
def get_settings() -> Settings:
    return Settings()