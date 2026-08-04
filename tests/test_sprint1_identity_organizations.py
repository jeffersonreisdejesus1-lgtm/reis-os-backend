from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.audit.infrastructure.models import AuditEventModel
from app.memberships.domain.enums import MembershipRole, MembershipStatus
from app.memberships.infrastructure.models import MembershipModel
from tests.conftest import TestSessionLocal

pytestmark = pytest.mark.integration


async def register(
    client: AsyncClient, *, email: str, display_name: str
) -> dict[str, Any]:
    response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "strong-password",
            "display_name": display_name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def authorization(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_register_login_and_me(client: AsyncClient) -> None:
    registered = await register(client, email="owner@example.com", display_name="Owner")
    token = registered["access_token"]

    me_response = await client.get("/auth/me", headers=authorization(token))
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "owner@example.com"

    login_response = await client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": "strong-password"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_create_organization_is_atomic_and_audited(client: AsyncClient) -> None:
    registered = await register(client, email="owner@example.com", display_name="Owner")
    response = await client.post(
        "/organizations",
        headers=authorization(registered["access_token"]),
        json={"name": "REIS OS", "slug": "reis-os"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["membership"]["role"] == MembershipRole.OWNER
    assert body["membership"]["status"] == MembershipStatus.ACTIVE

    async with TestSessionLocal() as session:
        membership_count = await session.scalar(
            select(func.count()).select_from(MembershipModel)
        )
        audit_count = await session.scalar(
            select(func.count()).select_from(AuditEventModel)
        )
        assert membership_count == 1
        assert audit_count == 1


@pytest.mark.asyncio
async def test_user_cannot_access_another_users_organization(
    client: AsyncClient,
) -> None:
    user_a = await register(client, email="a@example.com", display_name="User A")
    organization_a = await client.post(
        "/organizations",
        headers=authorization(user_a["access_token"]),
        json={"name": "Organization A", "slug": "organization-a"},
    )
    assert organization_a.status_code == 201
    organization_a_id = organization_a.json()["id"]

    user_b = await register(client, email="b@example.com", display_name="User B")
    organization_b = await client.post(
        "/organizations",
        headers=authorization(user_b["access_token"]),
        json={"name": "Organization B", "slug": "organization-b"},
    )
    assert organization_b.status_code == 201

    forbidden = await client.get(
        f"/organizations/{organization_a_id}",
        headers=authorization(user_b["access_token"]),
    )
    assert forbidden.status_code == 404
    assert forbidden.json()["error"]["code"] == "organization_not_found"

    listed = await client.get(
        "/organizations", headers=authorization(user_b["access_token"])
    )
    assert listed.status_code == 200
    assert [item["slug"] for item in listed.json()] == ["organization-b"]
