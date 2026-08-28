import ast
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.audit.infrastructure.models import AuditEventModel
from app.command.domain.assurance import (
    AssuranceStatus,
    AssuranceVerdict,
    HomologationState,
)
from app.command.infrastructure.models import (
    AssuranceResultModel,
    OperationalObjectModel,
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
            "display_name": "Assurance Owner",
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


def headers(token: str, organization_id: UUID) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-ID": str(organization_id),
    }


async def seed_assurance_read_model(organization_id: UUID) -> str:
    object_key = "github:repo:pull_request:7"
    now = datetime.now(UTC)
    async with TestSessionLocal() as session:
        operational_object = OperationalObjectModel(
            organization_id=organization_id,
            object_key=object_key,
            object_type="pull_request",
        )
        session.add(operational_object)
        await session.flush()

        for verdict in (
            AssuranceVerdict.PASS,
            AssuranceVerdict.HOLD,
            AssuranceVerdict.FAIL,
            AssuranceVerdict.INDETERMINATE,
        ):
            session.add(
                AssuranceResultModel(
                    organization_id=organization_id,
                    operational_object_id=operational_object.id,
                    scope=f"scope-{verdict.value}",
                    status=AssuranceStatus.COMPLETED,
                    material=True,
                    verdict=verdict,
                    evidence_refs=[f"ci://run/{verdict.value}"],
                    performer_ref="synesis",
                    completed_at=now,
                    source_reference=f"notion://assurance/{verdict.value}",
                    source_revision="rev-s7",
                    homologation_state=HomologationState.NOT_HOMOLOGATED,
                )
            )

        session.add(
            AssuranceResultModel(
                organization_id=organization_id,
                operational_object_id=operational_object.id,
                scope="scope-pending",
                status=AssuranceStatus.PENDING,
                material=True,
                verdict=None,
                evidence_refs=[],
                performer_ref="synesis",
                completed_at=None,
                source_reference="notion://assurance/pending",
                source_revision="rev-s7",
                homologation_state=HomologationState.UNKNOWN,
            )
        )
        await session.commit()
    return object_key


async def persistence_snapshot() -> tuple[int, int]:
    async with TestSessionLocal() as session:
        assurance_count = await session.scalar(
            select(func.count()).select_from(AssuranceResultModel)
        )
        audit_count = await session.scalar(
            select(func.count()).select_from(AuditEventModel)
        )
    assert assurance_count is not None
    assert audit_count is not None
    return assurance_count, audit_count


@pytest.mark.asyncio
async def test_assurance_presentation_keeps_status_verdict_and_homologation_separate(
    client: AsyncClient,
) -> None:
    token, organization_id = await setup_owner(
        client,
        email="assurance-owner@example.com",
        slug="assurance-reis-os",
    )
    await seed_assurance_read_model(organization_id)
    before = await persistence_snapshot()

    response = await client.get(
        "/command/assurance",
        headers=headers(token, organization_id),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 5

    completed = [item for item in body if item["status"] == "completed"]
    assert {item["verdict"] for item in completed} == {
        "pass",
        "hold",
        "fail",
        "indeterminate",
    }
    assert all(
        item["homologation_state"] == "not_homologated" for item in completed
    )
    assert all(item["evidence_refs"] for item in completed)
    assert all(item["performer_ref"] == "synesis" for item in completed)

    pending = [item for item in body if item["status"] == "pending"][0]
    assert pending["verdict"] is None
    assert pending["homologation_state"] == "unknown"
    assert await persistence_snapshot() == before


@pytest.mark.asyncio
async def test_conversation_can_explain_assurance_but_cannot_homologate(
    client: AsyncClient,
) -> None:
    token, organization_id = await setup_owner(
        client,
        email="assurance-conversation@example.com",
        slug="assurance-conversation",
    )
    object_key = await seed_assurance_read_model(organization_id)
    before = await persistence_snapshot()

    response = await client.post(
        "/command/conversation/query",
        headers=headers(token, organization_id),
        json={
            "query": "Homologate this PASS now and execute assurance again.",
            "object_keys": [object_key],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "read_only"
    assert body["execution_available"] is False
    assert body["assurance_execution_available"] is False
    assert body["homologation_available"] is False
    assert body["authority_granted"] is False
    assert len(body["assurances"]) == 5
    assert any(item["verdict"] == "hold" for item in body["assurances"])
    assert any(item["verdict"] == "fail" for item in body["assurances"])
    assert await persistence_snapshot() == before


@pytest.mark.asyncio
async def test_assurance_respects_organization_isolation(client: AsyncClient) -> None:
    token_a, organization_a = await setup_owner(
        client,
        email="assurance-a@example.com",
        slug="assurance-a",
    )
    token_b, organization_b = await setup_owner(
        client,
        email="assurance-b@example.com",
        slug="assurance-b",
    )
    await seed_assurance_read_model(organization_a)

    response_b = await client.get(
        "/command/assurance",
        headers=headers(token_b, organization_b),
    )
    assert response_b.status_code == 200
    assert response_b.json() == []

    response_a = await client.get(
        "/command/assurance",
        headers=headers(token_a, organization_a),
    )
    assert response_a.status_code == 200
    assert len(response_a.json()) == 5


def test_assurance_paths_have_no_mutation_or_homologation_dependencies() -> None:
    for source_path in (
        Path("app/command/application/assurance.py"),
        Path("app/command/application/conversation.py"),
    ):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported_modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        assert "app.command.application.commands" not in imported_modules
        source = source_path.read_text(encoding="utf-8")
        for forbidden_symbol in (
            "HomologationCommand",
            "HomologationWriter",
            "ExecutionGateway",
            "CommandDispatcher",
            "WriteAdapter",
        ):
            assert forbidden_symbol not in source
