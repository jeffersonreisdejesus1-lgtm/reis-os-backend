import ast
from datetime import UTC, datetime
from pathlib import Path
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


async def setup_owner(
    client: AsyncClient,
    *,
    email: str,
    slug: str,
) -> tuple[str, UUID]:
    registered = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "strong-password",
            "display_name": "Command Owner",
        },
    )
    assert registered.status_code == 201, registered.text
    token = registered.json()["access_token"]
    organization = await client.post(
        "/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": slug.upper(), "slug": slug},
    )
    assert organization.status_code == 201, organization.text
    return token, UUID(organization.json()["id"])


def command_headers(token: str, organization_id: UUID) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-ID": str(organization_id),
    }


async def seed_conflicted_read_model(organization_id: UUID) -> str:
    object_key = "github:repo:pull_request:42"
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
            source_object_id="42",
            source_reference="github://repo/pulls/42",
            source_revision="rev-conflict",
            observed_at=now,
            source_updated_at=now,
            retrieved_at=now,
            payload_normalized={"state": "open", "conflict": True},
            observation_status=ObservationStatus.CONFLICT,
            freshness_state=FreshnessState.CONFLICT,
            freshness_reason="sources_disagree",
            current_confirmed=False,
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
            freshness_state=FreshnessState.CONFLICT,
            projection_payload={"state": "open", "conflict": True},
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
                    rule_id="SOURCE_CONFLICT",
                    attention_class=AttentionClass.BLOCKER,
                    reason="Source conflict remains unresolved",
                    severity=AttentionSeverity.P1,
                    freshness_state=FreshnessState.CONFLICT,
                    explanation="Derived from conflicting source evidence",
                ),
                AttentionItemModel(
                    organization_id=organization_id,
                    operational_object_id=operational_object.id,
                    rule_id="FOUNDER_DECISION_PENDING",
                    attention_class=AttentionClass.DECISION_PENDING,
                    reason="Founder decision context required",
                    severity=AttentionSeverity.P1,
                    freshness_state=FreshnessState.CONFLICT,
                    explanation="Context only; no decision has been made",
                ),
            ]
        )
        await session.commit()
    return object_key


async def persistence_snapshot() -> tuple[int, int, int, int, int]:
    async with TestSessionLocal() as session:
        values = []
        for model in (
            AuditEventModel,
            CommandSourceModel,
            ObservationModel,
            ProjectionModel,
            AttentionItemModel,
        ):
            count = await session.scalar(select(func.count()).select_from(model))
            assert count is not None
            values.append(count)
    return tuple(values)  # type: ignore[return-value]


@pytest.mark.asyncio
async def test_conversation_is_read_only_and_preserves_evidence(
    client: AsyncClient,
) -> None:
    token, organization_id = await setup_owner(
        client,
        email="conversation-owner@example.com",
        slug="conversation-reis-os",
    )
    object_key = await seed_conflicted_read_model(organization_id)
    before = await persistence_snapshot()

    imperative = "Merge this pull request now and resolve the conflict."
    response = await client.post(
        "/command/conversation/query",
        headers=command_headers(token, organization_id),
        json={"query": imperative, "object_keys": [object_key]},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["query_text"] == imperative
    assert body["mode"] == "read_only"
    assert body["execution_available"] is False
    assert body["authority_granted"] is False
    assert body["situation"][0]["freshness_state"] == "conflict"
    assert body["blockers"][0]["attention_class"] == "blocker"
    assert body["decisions"][0]["attention_class"] == "decision_pending"
    assert body["evidence"][0]["source_reference"] == "github://repo/pulls/42"
    assert body["evidence"][0]["source_revision"] == "rev-conflict"
    assert body["evidence"][0]["freshness_state"] == "conflict"
    assert "decision-context" in body["conclusion"]

    assert await persistence_snapshot() == before


@pytest.mark.asyncio
async def test_conversation_respects_organization_isolation(
    client: AsyncClient,
) -> None:
    token_a, organization_a = await setup_owner(
        client,
        email="conversation-a@example.com",
        slug="conversation-a",
    )
    token_b, organization_b = await setup_owner(
        client,
        email="conversation-b@example.com",
        slug="conversation-b",
    )
    object_key = await seed_conflicted_read_model(organization_a)

    response_b = await client.post(
        "/command/conversation/query",
        headers=command_headers(token_b, organization_b),
        json={"query": "What is happening?"},
    )
    assert response_b.status_code == 200, response_b.text
    assert response_b.json()["situation"] == []
    assert response_b.json()["evidence"] == []

    hidden_object = await client.post(
        "/command/conversation/query",
        headers=command_headers(token_b, organization_b),
        json={"query": "Explain this object", "object_keys": [object_key]},
    )
    assert hidden_object.status_code == 404

    response_a = await client.post(
        "/command/conversation/query",
        headers=command_headers(token_a, organization_a),
        json={"query": "Explain this object", "object_keys": [object_key]},
    )
    assert response_a.status_code == 200
    assert response_a.json()["objects"][0]["object_key"] == object_key


def test_conversation_query_service_has_no_mutation_dependencies() -> None:
    source_path = Path("app/command/application/conversation.py")
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "app.command.adapters" not in imported_modules
    assert "app.command.application.commands" not in imported_modules
    source = source_path.read_text(encoding="utf-8")
    for forbidden_symbol in (
        "CommandDispatcher",
        "WriteAdapter",
        "ExecutionGateway",
    ):
        assert forbidden_symbol not in source
