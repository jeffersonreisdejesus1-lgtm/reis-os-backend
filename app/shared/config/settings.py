from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
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

    # COMMAND v0.1 private-mode contract. These defaults fail closed.
    public_signup_enabled: bool = False
    organization_self_service_enabled: bool = False
    canonical_institution_name: str = "REIS OS"
    canonical_institution_slug: str = "reis-os"
    session_cookie_name: str = "reis_os_command_session"
    session_cookie_secure: bool = True
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # Refresh is backend-owned. Policies remain persistent per source/fact class.
    command_refresh_enabled: bool = True
    command_refresh_poll_seconds: int = Field(default=60, ge=10, le=3600)

    command_github_token: SecretStr | None = None
    command_notion_token: SecretStr | None = None
    command_notion_version: str = "2022-06-28"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_private_production_boundary(self) -> Self:
        if self.app_env.lower() != "production":
            return self
        if self.secret_key == "change-me" or len(self.secret_key) < 32:
            raise ValueError("Production requires a non-default strong SECRET_KEY")
        if self.debug:
            raise ValueError("Production debug must be disabled")
        if not self.session_cookie_secure:
            raise ValueError("Production sessions require secure cookies")
        if self.public_signup_enabled:
            raise ValueError("Public signup is prohibited in COMMAND v0.1")
        if self.organization_self_service_enabled:
            raise ValueError("Organization self-service is prohibited in COMMAND v0.1")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
