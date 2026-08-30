from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def auth_headers(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/auth/register",
        json={
            "email": "action-proposals@example.com",
            "password": "strong-password",
            "display_name": "Action Proposals Tester",
        },
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def valid_payload() -> dict[str, Any]:
    return {
        "action_type": "notion.page.update",
        "target": "page-123",
        "payload": {"title": "Proposed title"},
        "requested_by": "founder",
    }


async def create_proposal(client: AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    response = await client.post(
        "/action-proposals", json=valid_payload(), headers=headers
    )
    assert response.status_code == 201
    return response.json()


async def test_create_action_proposal_valid(client: AsyncClient) -> None:
    headers = await auth_headers(client)
    response = await client.post(
        "/action-proposals", json=valid_payload(), headers=headers
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["action_type"] == "notion.page.update"
    assert body["requested_by"] == "founder"
    assert body["created_at"] is not None
    assert body["approved_at"] is None
    assert body["execution_status"] is None


async def test_create_action_proposal_invalid(client: AsyncClient) -> None:
    headers = await auth_headers(client)
    payload = valid_payload()
    payload["action_type"] = "   "

    response = await client.post(
        "/action-proposals", json=payload, headers=headers
    )

    assert response.status_code == 422


async def test_approve_action_proposal_valid(client: AsyncClient) -> None:
    headers = await auth_headers(client)
    proposal = await create_proposal(client, headers)

    response = await client.post(
        f"/action-proposals/{proposal['id']}/approve",
        json={"approved_by": "founder"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["approved_by"] == "founder"
    assert body["approved_at"] is not None


async def test_approve_action_proposal_not_found(client: AsyncClient) -> None:
    headers = await auth_headers(client)

    response = await client.post(
        f"/action-proposals/{uuid4()}/approve",
        json={"approved_by": "founder"},
        headers=headers,
    )

    assert response.status_code == 404


async def test_execute_action_proposal_without_approval(client: AsyncClient) -> None:
    headers = await auth_headers(client)
    proposal = await create_proposal(client, headers)

    response = await client.post(
        f"/action-proposals/{proposal['id']}/execute", headers=headers
    )

    assert response.status_code == 409


async def test_execute_approved_action_proposal(client: AsyncClient) -> None:
    headers = await auth_headers(client)
    proposal = await create_proposal(client, headers)
    approved = await client.post(
        f"/action-proposals/{proposal['id']}/approve",
        json={"approved_by": "founder"},
        headers=headers,
    )
    assert approved.status_code == 200

    response = await client.post(
        f"/action-proposals/{proposal['id']}/execute", headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["execution_status"] == "simulated_success"
    assert body["executed_at"] is not None
    assert body["execution_result"]["simulated"] is True
    assert "no external action" in body["execution_result"]["message"].lower()


async def test_action_proposal_cannot_execute_twice(client: AsyncClient) -> None:
    headers = await auth_headers(client)
    proposal = await create_proposal(client, headers)
    approved = await client.post(
        f"/action-proposals/{proposal['id']}/approve",
        json={"approved_by": "founder"},
        headers=headers,
    )
    assert approved.status_code == 200
    first = await client.post(
        f"/action-proposals/{proposal['id']}/execute", headers=headers
    )
    assert first.status_code == 200

    second = await client.post(
        f"/action-proposals/{proposal['id']}/execute", headers=headers
    )

    assert second.status_code == 409


async def test_read_action_proposal_final_state(client: AsyncClient) -> None:
    headers = await auth_headers(client)
    proposal = await create_proposal(client, headers)
    approved = await client.post(
        f"/action-proposals/{proposal['id']}/approve",
        json={"approved_by": "reviewer"},
        headers=headers,
    )
    assert approved.status_code == 200
    executed = await client.post(
        f"/action-proposals/{proposal['id']}/execute", headers=headers
    )
    assert executed.status_code == 200

    response = await client.get(
        f"/action-proposals/{proposal['id']}", headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == proposal["id"]
    assert body["status"] == "approved"
    assert body["approved_by"] == "reviewer"
    assert body["approved_at"] is not None
    assert body["execution_status"] == "simulated_success"
    assert body["executed_at"] is not None
    assert body["execution_result"]["simulated"] is True
