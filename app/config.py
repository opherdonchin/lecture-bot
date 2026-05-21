import functools as functools_
import pathlib as pathlib_

import pydantic as pd
import pydantic_settings as ps


class Settings(ps.BaseSettings):
    app_name: str = "lecture-bot"
    app_env: str = "dev"
    student_root_path: str = pd.Field(default="/bot", validation_alias="LECTURE_BOT_STUDENT_ROOT_PATH")
    admin_root_path: str = pd.Field(default="/bot-admin", validation_alias="LECTURE_BOT_ADMIN_ROOT_PATH")
    database_url: str = pd.Field(default="sqlite:///data/lecture_bot.db")
    lectures_dir: pathlib_.Path = pd.Field(default=pathlib_.Path("lectures"))
    moodle_submissions_dir: pathlib_.Path = pd.Field(default=pathlib_.Path("data/submissions"))
    moodle_participants_csv: pathlib_.Path = pd.Field(default=pathlib_.Path("data/submissions/courseid_64733_participants.csv"))
    moodle_grade_import_csv: pathlib_.Path = pd.Field(default=pathlib_.Path("data/submissions/moodle_grade_import.csv"))
    moodle_grade_import_report_csv: pathlib_.Path = pd.Field(default=pathlib_.Path("data/submissions/moodle_grade_import_report.csv"))
    session_timeout_minutes: int = 30
    session_warning_minutes: int = 5
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4-mini"
    admin_username: str | None = None
    admin_password: str | None = None
    recent_message_limit: int = 10
    max_dialogue_context_chars: int = 45000
    max_grading_context_chars: int = 70000
    sampled_topic_count: int = 5
    opening_topic_choice_count: int = 3
    tutor_prompt_template: str = "tutor_prompt.md"  # Default prompt template name
    student_restart_command: str = "sudo -n systemctl restart lecture-bot.service"

    @pd.field_validator("student_root_path", "admin_root_path")
    @classmethod
    def normalize_root_path(cls, value: str) -> str:
        root_path = value.strip()
        if root_path in ("", "/"):
            return ""
        if not root_path.startswith("/"):
            root_path = f"/{root_path}"
        return root_path.rstrip("/")

    model_config = ps.SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@functools_.lru_cache
def get_settings() -> Settings:
    return Settings()
