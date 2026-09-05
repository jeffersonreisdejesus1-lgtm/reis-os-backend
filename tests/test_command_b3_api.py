from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient

from app.command.api.dependencies import get_command_institution_organization_id
from app.command.event_store import CommandEventStore
from app.command.events import CommandEvent, Freshness
from app.main import app
from app.shared.config.settings import Settings, get_settings

pytestmark = pytest.mark.integration


async def _register(client: AsyncClient) -> dict[str, Any]:
    response = await client.post(
        "/auth/register",
        json={
            "email": "command-b3-founder@example.com",
            "password": "strong-password",
            "display_name": "Command B3 Founder",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _headers(client: AsyncClient) -> dict[str, str]:
    user = await _register(client)
    response = await client.post(
        "/organizations",
        headers={"Authorization": f"Bearer {user['access_token']}"},
        json={"name": "REIS OS Command B3", "slug": "reis-os-command-b3"},
    )
    assert response.status_code == 201, response.text
    organization = response.json()
    institution_id = UUID(organization["id"])
    app.dependency_overrides[get_command_institution_organization_id] = (
        lambda: institution_id
    )
    return {
        "Authorization": f"Bearer {user['access_token']}",
        "X-Organization-ID": organization["id"],
    }


def _event(
    *,
    event_id: str,
    projection: str,
    data: dict[str, object],
    run_id: str,
    ocs_id: str | None = None,
) -> CommandEvent:
    return CommandEvent(
        event_id=event_id,
        event_type=f"command.{projection}.updated",
        schema_version="1.0",
        occurred_at=datetime(2026, 9, 5, 5, 10, tzinfo=UTC),
        source="reis-os-backend",
        source_version="97f45542",
        institution_id="REIS-OS",
        ocs_id=ocs_id,
        project_id="COMMAND",
        run_id=run_id,
        causation_id="cause-b3",
        correlation_id="corr-b3",
        sequence=1,
        idempotency_key=f"idem-{event_id}",
        freshness=Freshness.RECENT,
        evidence_refs=(f"evidence://{event_id}",),
        payload={"projection": projection, "data": data},
    )


def _seed(path: Path) -> None:
    store = CommandEventStore(path)
    events = [
        _event(
            event_id="institution-1",
            projection="institution",
            data={"status": "operational"},
            run_id="institution-run",
        ),
        _event(
            event_id="operation-1",
            projection="operation",
            data={"status": "executed"},
            run_id="operation-run",
            ocs_id="ÁGORA",
        ),
        _event(
            event_id="gate-1",
            projection="gate",
            data={"gate_id": "founder-merge", "status": "closed"},
            run_id="gate-run",
        ),
        _event(
            event_id="evidence-1",
            projection="receipt",
            data={"evidence_id": "receipt-1", "status": "verified"},
            run_id="evidence-run",
        ),
        _event(
            event_id="health-1",
            projection="system_health",
            data={"status": "healthy"},
            run_id="health-run",
        ),
        _event(
            event_id="map-1",
            projection="map",
            data={"map_id": "institution-map", "status": "material"},
            run_id="map-run",
        ),
    ]
    for item in events:
        assert store.append(item) is True


@pytest.mark.asyncio
async def test_b3_authenticated_query_preserves_provenance(
    client: AsyncClient,
    tmp_path: Path,
) -> None:
    database = tmp_path / "command-b3.sqlite3"
    _seed(database)
    app.dependency_overrides[get_settings] = lambda: Settings(
        command_event_store_path=str(database)
    )
    headers = await _headers(client)

    for path in (
        "/v1/command/institution",
        "/v1/command/operations",
        "/v1/command/gates",
        "/v1/command/events",
        "/v1/command/evidence",
        "/v1/command/system-health",
        "/v1/command/maps",
    ):
        response = await client.get(path, headers=headers)
        assert response.status_code == 200, (path, response.text)

    operation = (await client.get("/v1/command/operations", headers=headers)).json()[0]
    assert operation["source"] == "reis-os-backend"
    assert operation["source_version"] == "97f45542"
    assert operation["freshness"] == "recent"
    assert operation["evidence_refs"] == ["evidence://operation-1"]


@pytest.mark.asyncio
async def test_b3_routes_require_authentication(
    client: AsyncClient,
) -> None:
    response = await client.get("/v1/command/operations")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_b3_empty_projection_fails_closed(
    client: AsyncClient,
    tmp_path: Path,
) -> None:
    database = tmp_path / "empty-command-b3.sqlite3"
    app.dependency_overrides[get_settings] = lambda: Settings(
        command_event_store_path=str(database)
    )
    headers = await _headers(client)

    response = await client.get("/v1/command/operations", headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "command_projection_not_materialized"

    health = await client.get("/v1/command/system-health", headers=headers)
    assert health.status_code == 200
    assert health.json()["status"] == "unknown"
    assert health.json()["freshness"] == "unknown"
