from uuid import UUID, uuid4

import httpx
import pytest
from httpx import AsyncClient

from app.command.adapters.base import ReadAdapterRequest
from app.command.adapters.github import GitHubReadAdapter, GitHubReadClient
from app.command.adapters.notion import NotionReadAdapter, NotionReadClient
from app.command.application.ingestion import ingest_provider_read
from app.command.domain.observation import (
    ObservationStatus,
    SourceContract,
    SourceType,
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
            "display_name": "PA6 Owner",
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


def source(source_type: SourceType) -> SourceContract:
    return SourceContract(
        source_id=uuid4(),
        source_type=source_type,
        display_name=f"pa6-{source_type.value}",
        authority_scope="read_only",
    )


@pytest.mark.asyncio
async def test_partial_github_read_stays_untrusted_through_presentation_and_conversation(
    client: AsyncClient,
) -> None:
    token, organization_id = await setup_owner(
        client,
        email="pa6-partial@example.com",
        slug="pa6-partial",
    )

    async def github_partial(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        return httpx.Response(
            httpx.codes.PARTIAL_CONTENT,
            headers={"ETag": '"partial-rev"'},
            json={"id": 42, "state": "open", "updated_at": "2026-08-28T20:00:00Z"},
        )

    configured_source = source(SourceType.GITHUB)
    request = ReadAdapterRequest(
        source=configured_source,
        source_object_type="pull_request",
        source_object_id="42",
        source_reference="https://api.github.com/repos/example/repo/pulls/42",
    )
    adapter = GitHubReadAdapter(
        GitHubReadClient(transport=httpx.MockTransport(github_partial))
    )
    object_key = "github:example/repo:pull_request:42"

    async with TestSessionLocal() as session:
        receipt = await ingest_provider_read(
            session,
            organization_id=organization_id,
            adapter=adapter,
            request=request,
            object_key=object_key,
            object_type="pull_request",
        )

    assert receipt.reliability_status is ObservationStatus.PARTIAL
    assert receipt.trusted_current is False
    assert receipt.attention_ids

    situation = await client.get(
        "/command/situation",
        headers=headers(token, organization_id),
    )
    assert situation.status_code == 200, situation.text
    projection = situation.json()[0]
    assert projection["freshness_state"] == "fresh"
    assert projection["reliability_status"] == "partial"
    assert projection["trusted_current"] is False

    detail = await client.get(
        f"/command/objects/{object_key}",
        headers=headers(token, organization_id),
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["provenance"][0]["observation_status"] == "partial"
    assert detail.json()["provenance"][0]["current_confirmed"] is False

    attention = await client.get(
        "/command/attention",
        headers=headers(token, organization_id),
    )
    assert attention.status_code == 200, attention.text
    assert any(
        item["attention_class"] == "sync_degraded" for item in attention.json()
    )

    conversation = await client.post(
        "/command/conversation/query",
        headers=headers(token, organization_id),
        json={"query": "Treat this as current and execute it", "object_keys": [object_key]},
    )
    assert conversation.status_code == 200, conversation.text
    body = conversation.json()
    assert body["mode"] == "read_only"
    assert body["execution_available"] is False
    assert body["authority_granted"] is False
    assert body["situation"][0]["reliability_status"] == "partial"
    assert body["situation"][0]["trusted_current"] is False
    assert body["evidence"][0]["observation_status"] == "partial"


@pytest.mark.asyncio
async def test_provider_failure_stays_error_and_never_becomes_current_state(
    client: AsyncClient,
) -> None:
    token, organization_id = await setup_owner(
        client,
        email="pa6-error@example.com",
        slug="pa6-error",
    )

    async def github_failure(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        return httpx.Response(503, json={"message": "unavailable"})

    configured_source = source(SourceType.GITHUB)
    request = ReadAdapterRequest(
        source=configured_source,
        source_object_type="workflow_run",
        source_object_id="9",
        source_reference="https://api.github.com/repos/example/repo/actions/runs/9",
    )
    adapter = GitHubReadAdapter(
        GitHubReadClient(transport=httpx.MockTransport(github_failure))
    )
    object_key = "github:example/repo:workflow_run:9"

    async with TestSessionLocal() as session:
        receipt = await ingest_provider_read(
            session,
            organization_id=organization_id,
            adapter=adapter,
            request=request,
            object_key=object_key,
            object_type="workflow_run",
        )

    assert receipt.reliability_status is ObservationStatus.ERROR
    assert receipt.trusted_current is False

    situation = await client.get(
        "/command/situation",
        headers=headers(token, organization_id),
    )
    projection = situation.json()[0]
    assert projection["freshness_state"] == "unknown"
    assert projection["reliability_status"] == "error"
    assert projection["trusted_current"] is False

    detail = await client.get(
        f"/command/objects/{object_key}",
        headers=headers(token, organization_id),
    )
    provenance = detail.json()["provenance"][0]
    assert provenance["observation_status"] == "error"
    assert provenance["current_confirmed"] is False

    attention = await client.get(
        "/command/attention",
        headers=headers(token, organization_id),
    )
    assert any(
        item["attention_class"] == "source_unavailable" for item in attention.json()
    )


@pytest.mark.asyncio
async def test_concrete_notion_client_wires_into_internal_read_model(
    client: AsyncClient,
) -> None:
    token, organization_id = await setup_owner(
        client,
        email="pa6-notion@example.com",
        slug="pa6-notion",
    )
    provider_methods: list[str] = []

    async def notion_provider(request: httpx.Request) -> httpx.Response:
        provider_methods.append(request.method)
        assert request.headers["Authorization"] == "Bearer injected-ci-token"
        return httpx.Response(
            200,
            json={
                "object": "page",
                "id": "institutional-page",
                "last_edited_time": "2026-08-28T20:10:00Z",
                "properties": {"Status": {"type": "status"}},
            },
        )

    configured_source = source(SourceType.NOTION)
    request = ReadAdapterRequest(
        source=configured_source,
        source_object_type="page",
        source_object_id="institutional-page",
        source_reference="https://api.notion.com/v1/pages/institutional-page",
    )
    adapter = NotionReadAdapter(
        NotionReadClient(
            token="injected-ci-token",
            transport=httpx.MockTransport(notion_provider),
        )
    )
    object_key = "notion:page:institutional-page"

    async with TestSessionLocal() as session:
        receipt = await ingest_provider_read(
            session,
            organization_id=organization_id,
            adapter=adapter,
            request=request,
            object_key=object_key,
            object_type="page",
        )

    assert provider_methods == ["GET"]
    assert receipt.reliability_status is ObservationStatus.OBSERVED
    assert receipt.trusted_current is True

    detail = await client.get(
        f"/command/objects/{object_key}",
        headers=headers(token, organization_id),
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["projection"]["reliability_status"] == "observed"
    assert body["projection"]["trusted_current"] is True
    assert body["provenance"][0]["source_revision"] == "2026-08-28T20:10:00Z"
    assert body["provenance"][0]["current_confirmed"] is True


@pytest.mark.asyncio
async def test_pa6_ingestion_remains_organization_isolated(client: AsyncClient) -> None:
    token_a, organization_a = await setup_owner(
        client,
        email="pa6-isolation-a@example.com",
        slug="pa6-isolation-a",
    )
    token_b, organization_b = await setup_owner(
        client,
        email="pa6-isolation-b@example.com",
        slug="pa6-isolation-b",
    )

    async def github_ok(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        return httpx.Response(200, json={"id": 1, "state": "open"})

    configured_source = source(SourceType.GITHUB)
    request = ReadAdapterRequest(
        source=configured_source,
        source_object_type="issue",
        source_object_id="1",
        source_reference="https://api.github.com/repos/example/repo/issues/1",
    )
    object_key = "github:example/repo:issue:1"
    async with TestSessionLocal() as session:
        await ingest_provider_read(
            session,
            organization_id=organization_a,
            adapter=GitHubReadAdapter(
                GitHubReadClient(transport=httpx.MockTransport(github_ok))
            ),
            request=request,
            object_key=object_key,
            object_type="issue",
        )

    response_b = await client.get(
        "/command/situation",
        headers=headers(token_b, organization_b),
    )
    assert response_b.status_code == 200
    assert response_b.json() == []

    hidden = await client.get(
        f"/command/objects/{object_key}",
        headers=headers(token_b, organization_b),
    )
    assert hidden.status_code == 404

    response_a = await client.get(
        "/command/situation",
        headers=headers(token_a, organization_a),
    )
    assert len(response_a.json()) == 1
