from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def create_proposal(client: AsyncClient) -> dict[str, object]:
    response = await client.post(
        "/action-proposals",
        json={
            "action_type": "publish",
            "target": "example-target",
            "payload": {"document_id": "doc-123"},
            "requested_by": "requester@example.test",
        },
    )
    assert response.status_code == 201
    return response.json()


async def test_create_action_proposal_valid(client: AsyncClient) -> None:
    body = await create_proposal(client)

    assert body["id"]
    assert body["status"] == "pending"
    assert body["created_at"]
    assert body["approved_at"] is None
    assert body["executed_at"] is None


async def test_create_action_proposal_invalid(client: AsyncClient) -> None:
    response = await client.post(
        "/action-proposals",
        json={
            "action_type": "",
            "target": "example-target",
            "payload": {},
        },
    )

    assert response.status_code == 422


async def test_approve_action_proposal_valid(client: AsyncClient) -> None:
    proposal = await create_proposal(client)

    response = await client.post(
        f"/action-proposals/{proposal['id']}/approve",
        json={"approved_by": "approver@example.test"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["approved_by"] == "approver@example.test"
    assert body["approved_at"]


async def test_approve_action_proposal_not_found(client: AsyncClient) -> None:
    response = await client.post(
        f"/action-proposals/{uuid4()}/approve",
        json={"approved_by": "approver@example.test"},
    )

    assert response.status_code == 404


async def test_execute_action_proposal_without_approval(client: AsyncClient) -> None:
    proposal = await create_proposal(client)

    response = await client.post(f"/action-proposals/{proposal['id']}/execute")

    assert response.status_code == 409


async def test_execute_approved_action_proposal(client: AsyncClient) -> None:
    proposal = await create_proposal(client)
    await client.post(
        f"/action-proposals/{proposal['id']}/approve",
        json={"approved_by": "approver@example.test"},
    )

    response = await client.post(f"/action-proposals/{proposal['id']}/execute")

    assert response.status_code == 200
    body = response.json()
    assert body["execution_status"] == "simulated"
    assert body["executed_at"]
    assert body["execution_result"] == {
        "simulated": True,
        "message": "Execution simulated; no external action was performed.",
    }


async def test_action_proposal_cannot_execute_twice(client: AsyncClient) -> None:
    proposal = await create_proposal(client)
    await client.post(
        f"/action-proposals/{proposal['id']}/approve",
        json={"approved_by": "approver@example.test"},
    )
    first = await client.post(f"/action-proposals/{proposal['id']}/execute")
    assert first.status_code == 200

    second = await client.post(f"/action-proposals/{proposal['id']}/execute")

    assert second.status_code == 409


async def test_read_final_action_proposal_state(client: AsyncClient) -> None:
    proposal = await create_proposal(client)
    await client.post(
        f"/action-proposals/{proposal['id']}/approve",
        json={"approved_by": "approver@example.test"},
    )
    await client.post(f"/action-proposals/{proposal['id']}/execute")

    response = await client.get(f"/action-proposals/{proposal['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == proposal["id"]
    assert body["status"] == "approved"
    assert body["approved_by"] == "approver@example.test"
    assert body["approved_at"]
    assert body["execution_status"] == "simulated"
    assert body["executed_at"]
    assert body["execution_result"]["simulated"] is True
