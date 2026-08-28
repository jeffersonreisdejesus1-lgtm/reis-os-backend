from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "REIS OS Backend"
    app_env: str = "development"
    debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = Field(
        default="postgresql+psycopg://reis:reis@localhost:5432/reis_os"
    )
    log_level: str = "INFO"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60
    command_github_token: SecretStr | None = None
    command_notion_token: SecretStr | None = None
    command_notion_version: str = "2022-06-28"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
