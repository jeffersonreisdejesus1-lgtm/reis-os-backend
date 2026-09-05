from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient

from app.command.api.dependencies import get_command_institution_organization_id
from app.main import app
from app.shared.config.settings import Settings, get_settings

pytestmark = pytest.mark.integration


async def owner_headers(client: AsyncClient) -> tuple[dict[str, str], UUID]:
    register = await client.post(
        "/auth/register",
        json={
            "email": "command-ib6-founder@example.com",
            "password": "strong-password",
            "display_name": "Command IB6 Founder",
        },
    )
    assert register.status_code == 201, register.text
    user: dict[str, Any] = register.json()
    organization = await client.post(
        "/organizations",
        headers={"Authorization": f"Bearer {user['access_token']}"},
        json={"name": "REIS OS Command IB6", "slug": "reis-os-command-ib6"},
    )
    assert organization.status_code == 201, organization.text
    organization_id = UUID(organization.json()["id"])
    return (
        {
            "Authorization": f"Bearer {user['access_token']}",
            "X-Organization-ID": str(organization_id),
        },
        organization_id,
    )


@pytest.mark.asyncio
async def test_ib6_instance_api_requires_authentication(
    client: AsyncClient,
) -> None:
    response = await client.get("/v1/command/instances")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ib6_instance_api_enforces_institution_organization(
    client: AsyncClient, tmp_path: Path
) -> None:
    headers, organization_id = await owner_headers(client)
    app.dependency_overrides[get_command_institution_organization_id] = lambda: (
        organization_id
    )
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        command_institution_organization_id=organization_id,
        ocs_instance_store_path=str(tmp_path / "missing.sqlite3"),
    )
    own = await client.get("/v1/command/instances", headers=headers)
    assert own.status_code == 200, own.text
    assert own.json()["source"]["health"] == "unavailable"
    assert own.json()["snapshot"]["freshness"] == "unknown"

    foreign = await client.post(
        "/organizations",
        headers={"Authorization": headers["Authorization"]},
        json={"name": "Foreign IB6", "slug": "foreign-command-ib6"},
    )
    assert foreign.status_code == 201, foreign.text
    headers["X-Organization-ID"] = foreign.json()["id"]
    denied = await client.get("/v1/command/instances", headers=headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "command_organization_forbidden"
