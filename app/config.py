from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "lecture-bot"
    app_env: str = "dev"
    database_url: str = Field(default="sqlite:///data/lecture_bot.db")
    lectures_dir: Path = Field(default=Path("lectures"))
    session_timeout_minutes: int = 20
    openai_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()