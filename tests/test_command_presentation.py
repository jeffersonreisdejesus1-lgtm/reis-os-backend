from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.audit.infrastructure.models import AuditEventModel
from app.command.domain.attention import AttentionClass, AttentionSeverity
from app.command.domain.observation import (
    FreshnessState,
    ObservationStatus,
    SourceType,
)
from app.command.infrastructure.models import (
    AttentionItemModel,
    CommandSourceModel,
    ObservationModel,
    OperationalObjectModel,
    ProjectionModel,
    ProjectionObservationModel,
)
from tests.conftest import TestSessionLocal

pytestmark = pytest.mark.integration


async def setup_owner(client: AsyncClient) -> tuple[str, UUID]:
    registered = await client.post(
        "/auth/register",
        json={
            "email": "command-owner@example.com",
            "password": "strong-password",
            "display_name": "Command Owner",
        },
    )
    assert registered.status_code == 201, registered.text
    token = registered.json()["access_token"]
    organization = await client.post(
        "/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "REIS OS", "slug": "reis-os-command"},
    )
    assert organization.status_code == 201, organization.text
    return token, UUID(organization.json()["id"])


def command_headers(token: str, organization_id: UUID) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-ID": str(organization_id),
    }


async def seed_command_read_model(organization_id: UUID) -> str:
    object_key = "github:repo:pull_request:1"
    now = datetime.now(UTC)
    async with TestSessionLocal() as session:
        source = CommandSourceModel(
            organization_id=organization_id,
            source_type=SourceType.GITHUB,
            display_name="GitHub",
            authority_scope="read_only",
            enabled=True,
        )
        session.add(source)
        await session.flush()

        observation = ObservationModel(
            organization_id=organization_id,
            source_id=source.id,
            source_object_type="pull_request",
            source_object_id="1",
            source_reference="github://repo/pulls/1",
            source_revision="abc123",
            observed_at=now,
            source_updated_at=now,
            retrieved_at=now,
            payload_normalized={"state": "open", "blocked": True},
            observation_status=ObservationStatus.OBSERVED,
            freshness_state=FreshnessState.FRESH,
            freshness_reason="source_current",
            current_confirmed=True,
        )
        operational_object = OperationalObjectModel(
            organization_id=organization_id,
            object_key=object_key,
            object_type="pull_request",
        )
        session.add_all([observation, operational_object])
        await session.flush()

        projection = ProjectionModel(
            organization_id=organization_id,
            operational_object_id=operational_object.id,
            projection_type="status",
            built_at=now,
            projection_version=1,
            freshness_state=FreshnessState.FRESH,
            projection_payload={"state": "open", "blocked": True},
        )
        session.add(projection)
        await session.flush()
        session.add(
            ProjectionObservationModel(
                projection_id=projection.id,
                observation_id=observation.id,
            )
        )
        session.add_all(
            [
                AttentionItemModel(
                    organization_id=organization_id,
                    operational_object_id=operational_object.id,
                    rule_id="BLOCKER_OPEN",
                    attention_class=AttentionClass.BLOCKER,
                    reason="Bloqueio material ativo",
                    severity=AttentionSeverity.P1,
                    freshness_state=FreshnessState.FRESH,
                    explanation="Derived from projection",
                ),
                AttentionItemModel(
                    organization_id=organization_id,
                    operational_object_id=operational_object.id,
                    rule_id="DECISION_PENDING",
                    attention_class=AttentionClass.DECISION_PENDING,
                    reason="Decisão pendente",
                    severity=AttentionSeverity.P1,
                    freshness_state=FreshnessState.FRESH,
                    explanation="Derived from projection",
                ),
            ]
        )
        await session.commit()
    return object_key


async def audit_count() -> int:
    async with TestSessionLocal() as session:
        value = await session.scalar(select(func.count()).select_from(AuditEventModel))
    assert value is not None
    return value


@pytest.mark.asyncio
async def test_command_presentation_is_read_only_and_provenanced(
    client: AsyncClient,
) -> None:
    token, organization_id = await setup_owner(client)
    object_key = await seed_command_read_model(organization_id)
    headers = command_headers(token, organization_id)
    before = await audit_count()

    endpoints = (
        "/command/situation",
        "/command/changes",
        "/command/attention",
        "/command/blockers",
        "/command/decisions",
    )
    results: dict[str, list[dict[str, Any]]] = {}
    for endpoint in endpoints:
        response = await client.get(endpoint, headers=headers)
        assert response.status_code == 200, response.text
        results[endpoint] = response.json()

    assert results["/command/situation"][0]["freshness_state"] == "fresh"
    assert len(results["/command/attention"]) == 2
    assert results["/command/blockers"][0]["attention_class"] == "blocker"
    assert (
        results["/command/decisions"][0]["attention_class"]
        == "decision_pending"
    )

    detail = await client.get(f"/command/objects/{object_key}", headers=headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["projection"]["freshness_state"] == "fresh"
    assert body["provenance"][0]["source_name"] == "GitHub"
    assert body["provenance"][0]["source_revision"] == "abc123"

    assert await audit_count() == before
