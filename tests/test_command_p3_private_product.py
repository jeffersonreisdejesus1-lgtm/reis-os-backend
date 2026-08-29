from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.shared.config.settings import get_settings
from app.shared.security.tokens import create_access_token, decode_session_identity


@pytest.mark.asyncio
async def test_public_registration_is_fail_closed(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/register",
        json={
            "email": "outsider@example.com",
            "password": "not-a-public-password",
            "display_name": "Outsider",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "public_registration_disabled"


@pytest.mark.asyncio
async def test_institutional_command_requires_authentication(
    client: AsyncClient,
) -> None:
    response = await client.get("/command/situation")
    assert response.status_code == 401


def test_session_token_is_limited_and_revocation_bound() -> None:
    user_id = uuid4()
    token = create_access_token(user_id, session_version=7)
    identity = decode_session_identity(token)
    assert identity.user_id == user_id
    assert identity.session_version == 7


def test_private_product_defaults_are_fail_closed() -> None:
    settings = get_settings()
    assert settings.public_signup_enabled is False
    assert settings.organization_self_service_enabled is False
    assert settings.canonical_institution_slug == "reis-os"
    assert settings.session_cookie_secure is True
    assert settings.command_refresh_enabled is True


def test_frontend_has_no_direct_provider_or_persistent_token_storage() -> None:
    frontend = (
        Path(__file__).parents[1] / "app" / "command" / "frontend" / "index.html"
    ).read_text(encoding="utf-8")
    assert "api.github.com" not in frontend
    assert "api.notion.com" not in frontend
    assert "localStorage" not in frontend
    assert "sessionStorage" not in frontend
    assert "/auth/register" not in frontend
    assert "/command/conversation/query" in frontend
