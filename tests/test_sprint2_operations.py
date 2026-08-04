from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.audit.infrastructure.models import AuditEventModel
from app.projects.domain.enums import ProjectStatus
from app.tasks.domain.enums import TaskStatus
from tests.conftest import TestSessionLocal



pytestmark = pytest.mark.integration

async def register(client: AsyncClient, email: str) -> dict[str, Any]:
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": "strong-password", "display_name": email},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_org(client: AsyncClient, token: str, name: str, slug: str) -> dict[str, Any]:
    response = await client.post(
        "/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "slug": slug},
    )
    assert response.status_code == 201, response.text
    return response.json()


def headers(token: str, organization_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Organization-ID": organization_id}


@pytest.mark.asyncio
async def test_complete_workspace_project_task_flow(client: AsyncClient) -> None:
    user = await register(client, "owner@example.com")
    organization = await create_org(client, user["access_token"], "REIS OS", "reis-os")
    scoped = headers(user["access_token"], organization["id"])

    workspace_response = await client.post(
        "/workspaces",
        headers=scoped,
        json={"name": "Engineering", "slug": "engineering", "type": "atelier", "description": "Product engineering"},
    )
    assert workspace_response.status_code == 201, workspace_response.text
    workspace = workspace_response.json()
    assert workspace["status"] == "active"

    project_response = await client.post(
        "/projects",
        headers=scoped,
        json={"workspace_id": workspace["id"], "title": "Sprint 2", "description": "Operational core"},
    )
    assert project_response.status_code == 201, project_response.text
    project = project_response.json()
    assert project["status"] == ProjectStatus.DRAFT

    invalid = await client.post(
        f"/projects/{project['id']}/transition",
        headers=scoped,
        json={"target_status": "completed"},
    )
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "invalid_project_transition"

    for target in ("planned", "active"):
        response = await client.post(
            f"/projects/{project['id']}/transition",
            headers=scoped,
            json={"target_status": target},
        )
        assert response.status_code == 200, response.text

    task_response = await client.post(
        f"/projects/{project['id']}/tasks",
        headers=scoped,
        json={"title": "Implement domain transitions", "assignee_id": user["user"]["id"]},
    )
    assert task_response.status_code == 201, task_response.text
    task = task_response.json()
    assert task["status"] == TaskStatus.BACKLOG

    invalid_task = await client.post(
        f"/tasks/{task['id']}/transition",
        headers=scoped,
        json={"target_status": "done"},
    )
    assert invalid_task.status_code == 409

    for target in ("ready", "in_progress", "review", "done"):
        response = await client.post(
            f"/tasks/{task['id']}/transition",
            headers=scoped,
            json={"target_status": target},
        )
        assert response.status_code == 200, response.text

    listed = await client.get(f"/projects/{project['id']}/tasks", headers=scoped)
    assert listed.status_code == 200
    assert listed.json()[0]["status"] == "done"

    async with TestSessionLocal() as session:
        actions = list((await session.scalars(select(AuditEventModel.action).where(AuditEventModel.organization_id == UUID(organization["id"])))).all())
        assert "WorkspaceCreated" in actions
        assert "ProjectCreated" in actions
        assert "ProjectTransitioned" in actions
        assert "TaskCreated" in actions
        assert "TaskTransitioned" in actions
        assert await session.scalar(select(func.count()).select_from(AuditEventModel)) >= 10


@pytest.mark.asyncio
async def test_organization_isolation_for_operational_resources(client: AsyncClient) -> None:
    user_a = await register(client, "a@example.com")
    org_a = await create_org(client, user_a["access_token"], "Organization A", "org-a")
    a_headers = headers(user_a["access_token"], org_a["id"])
    workspace = (await client.post("/workspaces", headers=a_headers, json={"name": "A", "slug": "a", "type": "department"})).json()
    project = (await client.post("/projects", headers=a_headers, json={"workspace_id": workspace["id"], "title": "Secret"})).json()

    user_b = await register(client, "b@example.com")
    org_b = await create_org(client, user_b["access_token"], "Organization B", "org-b")
    b_headers = headers(user_b["access_token"], org_b["id"])

    cross_org_header = headers(user_b["access_token"], org_a["id"])
    denied_context = await client.get(f"/projects/{project['id']}", headers=cross_org_header)
    assert denied_context.status_code == 404
    assert denied_context.json()["error"]["code"] == "organization_not_found"

    hidden_resource = await client.get(f"/projects/{project['id']}", headers=b_headers)
    assert hidden_resource.status_code == 404
    assert hidden_resource.json()["error"]["code"] == "project_not_found"


@pytest.mark.asyncio
async def test_project_requires_workspace_from_same_organization(client: AsyncClient) -> None:
    user_a = await register(client, "one@example.com")
    org_a = await create_org(client, user_a["access_token"], "One", "one")
    workspace_a = (await client.post("/workspaces", headers=headers(user_a["access_token"], org_a["id"]), json={"name": "One", "slug": "one", "type": "project_space"})).json()

    user_b = await register(client, "two@example.com")
    org_b = await create_org(client, user_b["access_token"], "Two", "two")
    response = await client.post(
        "/projects",
        headers=headers(user_b["access_token"], org_b["id"]),
        json={"workspace_id": workspace_a["id"], "title": "Invalid"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "workspace_not_found"


@pytest.mark.asyncio
async def test_failed_workspace_creation_rolls_back_audit_event(
    client: AsyncClient,
) -> None:
    user = await register(client, "rollback@example.com")
    organization = await create_org(
        client,
        user["access_token"],
        "Rollback Organization",
        "rollback-organization",
    )
    scoped = headers(user["access_token"], organization["id"])

    first = await client.post(
        "/workspaces",
        headers=scoped,
        json={"name": "Engineering", "slug": "engineering", "type": "atelier"},
    )
    assert first.status_code == 201, first.text

    async with TestSessionLocal() as session:
        audit_count_before = await session.scalar(
            select(func.count()).select_from(AuditEventModel)
        )

    duplicate = await client.post(
        "/workspaces",
        headers=scoped,
        json={"name": "Duplicate", "slug": "engineering", "type": "department"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "workspace_slug_conflict"

    async with TestSessionLocal() as session:
        audit_count_after = await session.scalar(
            select(func.count()).select_from(AuditEventModel)
        )

    assert audit_count_after == audit_count_before
