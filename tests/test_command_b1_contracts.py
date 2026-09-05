from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.command import application as command_application
from app.memberships.domain.enums import MembershipRole
from app.memberships.infrastructure.models import MembershipModel
from tests.conftest import TestSessionLocal

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


async def command_context(
    client: AsyncClient,
) -> tuple[dict[str, str], dict[str, Any]]:
    user = await register(client)
    response = await client.post(
        "/organizations",
        headers={"Authorization": f"Bearer {user['access_token']}"},
        json={"name": "REIS OS Command", "slug": "reis-os-command"},
    )
    assert response.status_code == 201, response.text
    organization = response.json()
    headers = {
        "Authorization": f"Bearer {user['access_token']}",
        "X-Organization-ID": organization["id"],
    }
    return headers, user


async def command_headers(client: AsyncClient) -> dict[str, str]:
    headers, _ = await command_context(client)
    return headers


@pytest.mark.asyncio
async def test_command_lists_ten_declared_ocs_profiles(
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
    assert body["source"]["snapshot_class"] == "static_profile_declaration"
    assert body["source"]["evidence_state"] == "declared"
    assert body["source"]["content_source_ref"].endswith(
        "/app/profile_bindings/profiles.py"
    )
    assert body["source"]["kernel_interface_ref"].startswith(
        "R1-UNIVERSAL-KERNEL@"
    )
    assert (
        body["source"]["content_source_ref"]
        != body["source"]["kernel_interface_ref"]
    )

    assert all(
        item["namespaces"]["semantics"] == "distinct_declarations"
        for item in body["items"]
    )
    assert len({item["namespaces"]["state"] for item in body["items"]}) == 10
    assert len({item["namespaces"]["memory"] for item in body["items"]}) == 10


@pytest.mark.asyncio
async def test_command_uses_ascii_slugs_and_preserves_canonical_ids(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/v1/command/ocs",
        headers=await command_headers(client),
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]

    slugs = {item["slug"] for item in items}
    canonical_ids = {item["ocs_id"] for item in items}
    assert slugs == {
        "noesis",
        "dedala",
        "synesis",
        "iris",
        "lyra",
        "sofia",
        "metis",
        "agora",
        "auri",
        "synergeia",
    }
    assert all(slug.isascii() and slug.isalpha() for slug in slugs)
    assert {"NÓESIS", "DÉDALA", "SÝNESIS", "ÍRIS", "MÊTIS", "ÁGORA"} <= (
        canonical_ids
    )


@pytest.mark.asyncio
async def test_command_profile_resolves_slug_and_separates_authority(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/v1/command/ocs/sofia",
        headers=await command_headers(client),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["slug"] == "sofia"
    assert body["ocs_id"] == "SOFIA"
    assert body["support_capabilities"]
    assert body["authority_envelope_ref"].startswith("authority://")
    assert body["allowed_action_classes"] != body["support_capabilities"]


@pytest.mark.asyncio
async def test_command_profile_unknown_is_not_silently_empty(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/v1/command/ocs/unknown",
        headers=await command_headers(client),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ocs_profile_not_found"


@pytest.mark.asyncio
async def test_command_routes_require_authentication(
    client: AsyncClient,
) -> None:
    response = await client.get("/v1/command/ocs")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_command_routes_require_organization_context(
    client: AsyncClient,
) -> None:
    user = await register(client)
    response = await client.get(
        "/v1/command/ocs",
        headers={"Authorization": f"Bearer {user['access_token']}"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "organization_context_required"


@pytest.mark.asyncio
async def test_command_read_boundary_denies_viewer_membership(
    client: AsyncClient,
) -> None:
    headers, _ = await command_context(client)
    async with TestSessionLocal() as session:
        membership = await session.scalar(select(MembershipModel))
        assert membership is not None
        membership.role = MembershipRole.VIEWER
        await session.commit()

    response = await client.get("/v1/command/ocs", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "command_read_forbidden"


@pytest.mark.asyncio
async def test_command_profile_validation_fails_closed_before_serving(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profiles = dict(command_application.PROFILES)
    profiles.pop("AURI")
    monkeypatch.setattr(command_application, "PROFILES", profiles)

    with pytest.raises(ValueError, match="ten_distinct_ocs_profiles_required"):
        command_application.list_ocs_profiles()
