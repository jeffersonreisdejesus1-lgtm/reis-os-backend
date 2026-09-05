from functools import lru_cache
from uuid import UUID

from pydantic import Field
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
    command_institution_organization_id: UUID | None = None
    command_event_store_path: str = "command_events.sqlite3"
    ocs_instance_store_path: str = "ocs_instances.sqlite3"
    governance_candidate_store_path: str = "governance_candidates.sqlite3"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
