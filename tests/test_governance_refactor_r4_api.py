from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import update

from app.command.api.dependencies import get_command_institution_organization_id
from app.governance_refactor.contracts import Completeness, MissionMetricsRecord
from app.governance_refactor.scoped_store import ScopedGovernanceStore
from app.main import app
from app.memberships.domain.enums import MembershipRole
from app.memberships.infrastructure.models import MembershipModel
from app.shared.config.settings import Settings, get_settings
from conftest import TestSessionLocal

pytestmark = pytest.mark.integration
NOW = datetime(2026, 9, 5, 22, 0, tzinfo=UTC)


def _schema(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE governance_candidate_records (
              position INTEGER PRIMARY KEY, record_type TEXT NOT NULL,
              record_id TEXT NOT NULL, schema_version TEXT NOT NULL,
              payload_json TEXT NOT NULL, payload_hash TEXT NOT NULL,
              source_refs_json TEXT NOT NULL, provenance_refs_json TEXT NOT NULL,
              written_at TEXT NOT NULL,
              UNIQUE(record_type, record_id, schema_version));
            CREATE TABLE governance_candidate_events (
              position INTEGER PRIMARY KEY, event_id TEXT NOT NULL UNIQUE,
              record_type TEXT NOT NULL, record_id TEXT NOT NULL,
              schema_version TEXT NOT NULL, event_type TEXT NOT NULL,
              payload_hash TEXT NOT NULL, payload_json TEXT NOT NULL,
              source_refs_json TEXT NOT NULL, provenance_refs_json TEXT NOT NULL,
              occurred_at TEXT NOT NULL);
            CREATE TABLE governance_candidate_scopes (
              organization_id TEXT NOT NULL, record_type TEXT NOT NULL,
              record_id TEXT NOT NULL, schema_version TEXT NOT NULL,
              bound_at TEXT NOT NULL,
              PRIMARY KEY (organization_id, record_type, record_id, schema_version),
              UNIQUE (record_type, record_id, schema_version));
            """
        )


def _metric(record_id: str, observed_at: datetime = NOW) -> MissionMetricsRecord:
    return MissionMetricsRecord(
        record_id=record_id,
        mission_id="mission-r4",
        ocs_id="SOFIA",
        product_id=None,
        gate_id=None,
        started_at=NOW - timedelta(minutes=5),
        completed_at=NOW,
        active_execution_seconds=240,
        waiting_seconds=60,
        founder_wait_seconds=0,
        external_wait_seconds=0,
        retries=0,
        failures=0,
        refactors=0,
        founder_interventions=0,
        autonomous_completion=True,
        source_refs=("commit:r4",),
        source_links=(),
        provenance_refs=("ci:r4",),
        measurement_method="system_timestamp",
        measurement_version="v0.1",
        observed_at=observed_at,
        completeness=Completeness.COMPLETE,
    )


async def _headers(
    client: AsyncClient,
    *,
    database: Path,
    admin: bool = False,
) -> tuple[dict[str, str], UUID]:
    response = await client.post(
        "/auth/register",
        json={
            "email": (
                "command-r4-admin@example.com"
                if admin
                else "command-r4@example.com"
            ),
            "password": "strong-password",
            "display_name": "Command R4",
        },
    )
    user: dict[str, Any] = response.json()
    organization = await client.post(
        "/organizations",
        headers={"Authorization": f"Bearer {user['access_token']}"},
        json={
            "name": "REIS OS R4",
            "slug": "reis-os-r4-admin" if admin else "reis-os-r4",
        },
    )
    organization_id = UUID(organization.json()["id"])
    if admin:
        async with TestSessionLocal() as session:
            await session.execute(
                update(MembershipModel)
                .where(MembershipModel.organization_id == organization_id)
                .values(role=MembershipRole.ADMIN)
            )
            await session.commit()
    app.dependency_overrides[get_command_institution_organization_id] = (
        lambda: organization_id
    )
    app.dependency_overrides[get_settings] = lambda: Settings(
        command_institution_organization_id=organization_id,
        governance_candidate_store_path=str(database),
    )
    return (
        {
            "Authorization": f"Bearer {user['access_token']}",
            "X-Organization-ID": str(organization_id),
        },
        organization_id,
    )


def _counts(path: Path) -> tuple[int, int, int]:
    with sqlite3.connect(path) as connection:
        return tuple(
            int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in (
                "governance_candidate_records",
                "governance_candidate_events",
                "governance_candidate_scopes",
            )
        )


@pytest.mark.asyncio
async def test_r4_api_401_owner_admin_and_gets_have_zero_mutations(
    client: AsyncClient, tmp_path: Path
) -> None:
    database = tmp_path / "api.sqlite3"
    _schema(database)
    assert (await client.get("/v1/command/governance/summary")).status_code == 401
    owner_headers, organization_id = await _headers(client, database=database)
    writer = ScopedGovernanceStore(database)
    writer.append(
        _metric("metric-1"), organization_id=str(organization_id), occurred_at=NOW
    )
    writer.append(
        _metric("metric-2"), organization_id=str(organization_id), occurred_at=NOW
    )
    before = _counts(database)
    for endpoint in (
        "/v1/command/governance/summary",
        "/v1/command/governance/candidates?limit=1",
        "/v1/command/governance/events?limit=1",
        "/v1/command/governance/candidates/MissionMetricsRecord/metric-1",
    ):
        response = await client.get(endpoint, headers=owner_headers)
        assert response.status_code == 200, response.text
    assert _counts(database) == before

    admin_database = tmp_path / "admin.sqlite3"
    _schema(admin_database)
    admin_headers, _ = await _headers(client, database=admin_database, admin=True)
    assert (
        await client.get("/v1/command/governance/summary", headers=admin_headers)
    ).status_code == 200


@pytest.mark.asyncio
async def test_r4_api_wrong_org_malformed_type_and_pagination(
    client: AsyncClient, tmp_path: Path
) -> None:
    database = tmp_path / "scope.sqlite3"
    _schema(database)
    headers, organization_id = await _headers(client, database=database)
    writer = ScopedGovernanceStore(database)
    for number in range(3):
        writer.append(
            _metric(f"metric-{number}"),
            organization_id=str(organization_id),
            occurred_at=NOW + timedelta(seconds=number),
        )
    page = await client.get(
        "/v1/command/governance/candidates?limit=2", headers=headers
    )
    cursor = page.json()["next_cursor"]
    second = await client.get(
        f"/v1/command/governance/candidates?limit=2&cursor={cursor}",
        headers=headers,
    )
    assert page.status_code == 200 and len(page.json()["items"]) == 2
    assert second.status_code == 200 and len(second.json()["items"]) == 1
    injected = await client.get(
        "/v1/command/governance/candidates?record_type=InjectedType",
        headers=headers,
    )
    assert injected.status_code == 409
    malformed = await client.get(
        "/v1/command/governance/candidates?cursor=-1", headers=headers
    )
    assert malformed.status_code == 422

    foreign = await client.post(
        "/organizations",
        headers={"Authorization": headers["Authorization"]},
        json={"name": "Foreign R4", "slug": "foreign-r4"},
    )
    headers["X-Organization-ID"] = foreign.json()["id"]
    for endpoint in (
        "/v1/command/governance/candidates",
        "/v1/command/governance/events",
        "/v1/command/governance/candidates/MissionMetricsRecord/metric-0",
    ):
        response = await client.get(endpoint, headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "command_organization_forbidden"
