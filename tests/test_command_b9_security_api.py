from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.command.api.dependencies import get_command_institution_organization_id
from app.main import app

pytestmark = pytest.mark.integration


async def _owner_headers(client: AsyncClient) -> dict[str, str]:
    register = await client.post(
        "/auth/register",
        json={
            "email": "command-b9-founder@example.com",
            "password": "strong-password",
            "display_name": "Command B9 Founder",
        },
    )
    assert register.status_code == 201, register.text
    user: dict[str, Any] = register.json()
    organization = await client.post(
        "/organizations",
        headers={"Authorization": f"Bearer {user['access_token']}"},
        json={"name": "REIS OS Command B9", "slug": "reis-os-command-b9"},
    )
    assert organization.status_code == 201, organization.text
    organization_id = UUID(organization.json()["id"])
    app.dependency_overrides[get_command_institution_organization_id] = (
        lambda: organization_id
    )
    return {
        "Authorization": f"Bearer {user['access_token']}",
        "X-Organization-ID": str(organization_id),
    }


@pytest.mark.asyncio
async def test_b9_security_posture_requires_authentication(
    client: AsyncClient,
) -> None:
    response = await client.get("/v1/command/security/posture")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_b9_security_posture_requires_institution_binding(
    client: AsyncClient,
) -> None:
    headers = await _owner_headers(client)
    headers["X-Organization-ID"] = str(uuid4())

    response = await client.get("/v1/command/security/posture", headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "command_organization_forbidden"


@pytest.mark.asyncio
async def test_b9_owner_can_read_security_posture(client: AsyncClient) -> None:
    headers = await _owner_headers(client)

    response = await client.get("/v1/command/security/posture", headers=headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["founder_sensitive_role"] == "owner_only"
    assert payload["device_session_binding"] == "not_materialized"
    assert payload["authority_bypass"] == "forbidden"
