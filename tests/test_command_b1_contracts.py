from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def register(client: AsyncClient) -> dict[str, Any]:
    response = await client.post(
        "/auth/register",
        json={
            "email": "command-founder@example.com",
            "password": "strong-password",
            "display_name": "Command Founder",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def command_headers(client: AsyncClient) -> dict[str, str]:
    user = await register(client)
    response = await client.post(
        "/organizations",
        headers={"Authorization": f"Bearer {user['access_token']}"},
        json={"name": "REIS OS Command", "slug": "reis-os-command"},
    )
    assert response.status_code == 201, response.text
    organization = response.json()
    return {
        "Authorization": f"Bearer {user['access_token']}",
        "X-Organization-ID": organization["id"],
    }


@pytest.mark.asyncio
async def test_command_lists_ten_source_bound_ocs_profiles(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/v1/command/ocs",
        headers=await command_headers(client),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["count"] == 10
    assert len(body["items"]) == 10
    assert body["source"]["freshness"] == "static_versioned"
    assert body["source"]["evidence_state"] == "observed"
    assert all(item["source"]["source_ref"] for item in body["items"])
    assert len({item["state_namespace"] for item in body["items"]}) == 10
    assert len({item["memory_namespace"] for item in body["items"]}) == 10


@pytest.mark.asyncio
async def test_command_profile_separates_capability_and_authority(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/v1/command/ocs/SOFIA",
        headers=await command_headers(client),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ocs_id"] == "SOFIA"
    assert body["support_capabilities"]
    assert body["authority_envelope_ref"].startswith("authority://")
    assert body["allowed_action_classes"] != body["support_capabilities"]


@pytest.mark.asyncio
async def test_command_profile_unknown_is_not_silently_empty(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/v1/command/ocs/UNKNOWN",
        headers=await command_headers(client),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ocs_profile_not_found"


@pytest.mark.asyncio
async def test_command_routes_require_authenticated_organization_context(
    client: AsyncClient,
) -> None:
    response = await client.get("/v1/command/ocs")
    assert response.status_code == 401
