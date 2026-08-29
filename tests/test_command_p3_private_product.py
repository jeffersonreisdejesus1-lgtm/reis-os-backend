from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.shared.config.settings import Settings, get_settings
from app.shared.security.passwords import hash_password
from app.shared.security.tokens import create_access_token, decode_session_identity
from app.users.infrastructure.models import UserModel
from tests.conftest import TestSessionLocal


async def create_private_user(email: str) -> None:
    async with TestSessionLocal() as session:
        session.add(
            UserModel(
                email=email,
                password_hash=hash_password("private-test-password"),
                display_name="Private Founder",
                is_active=True,
            )
        )
        await session.commit()


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


@pytest.mark.asyncio
async def test_cookie_product_login_does_not_return_session_secret(
    client: AsyncClient,
) -> None:
    await create_private_user("founder-session@example.com")
    response = await client.post(
        "/auth/session/login",
        json={
            "email": "founder-session@example.com",
            "password": "private-test-password",
        },
    )
    assert response.status_code == 200
    assert "access_token" not in response.json()
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "secure" in cookie


@pytest.mark.asyncio
async def test_logout_revokes_existing_session_token(client: AsyncClient) -> None:
    await create_private_user("founder-revoke@example.com")
    login = await client.post(
        "/auth/login",
        json={
            "email": "founder-revoke@example.com",
            "password": "private-test-password",
        },
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert (await client.get("/auth/me", headers=headers)).status_code == 200
    assert (await client.post("/auth/logout", headers=headers)).status_code == 204
    assert (await client.get("/auth/me", headers=headers)).status_code == 401


@pytest.mark.asyncio
async def test_organization_self_service_is_fail_closed(client: AsyncClient) -> None:
    await create_private_user("founder-org@example.com")
    login = await client.post(
        "/auth/login",
        json={
            "email": "founder-org@example.com",
            "password": "private-test-password",
        },
    )
    token = login.json()["access_token"]
    response = await client.post(
        "/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Unauthorized Org", "slug": "unauthorized-org"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "organization_self_service_disabled"


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


def test_unsafe_production_configuration_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", secret_key="change-me")


def test_frontend_has_no_direct_provider_or_persistent_token_storage() -> None:
    frontend = (
        Path(__file__).parents[1] / "app" / "command" / "frontend" / "index.html"
    ).read_text(encoding="utf-8")
    assert "api.github.com" not in frontend
    assert "api.notion.com" not in frontend
    assert "localStorage" not in frontend
    assert "sessionStorage" not in frontend
    assert "/auth/register" not in frontend
    assert "/auth/session/login" in frontend
    assert "/command/objects/" in frontend
    assert "/command/conversation/query" in frontend
