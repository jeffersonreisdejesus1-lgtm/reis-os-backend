from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from app.command.adapters.base import (
    ProviderReadResult,
    ReadAdapterRequest,
    SourceReadError,
)
from app.command.adapters.github import GitHubReadAdapter, GitHubReadClient
from app.command.adapters.notion import NotionReadAdapter, NotionReadClient
from app.command.domain.observation import (
    FreshnessState,
    ObservationStatus,
    SourceContract,
    SourceType,
)


class RecordingReadClient:
    def __init__(
        self,
        payload: dict[str, object] | ProviderReadResult,
    ) -> None:
        self.payload = payload
        self.references: list[str] = []

    async def fetch(self, reference: str) -> dict[str, object] | ProviderReadResult:
        self.references.append(reference)
        if isinstance(self.payload, ProviderReadResult):
            return self.payload
        return self.payload.copy()


class FailingReadClient:
    async def fetch(self, reference: str) -> dict[str, object]:
        del reference
        raise RuntimeError("provider unavailable")


def make_source(source_type: SourceType) -> SourceContract:
    return SourceContract(
        source_id=uuid4(),
        source_type=source_type,
        display_name=source_type.value,
        authority_scope="read_only",
    )


def make_request(source_type: SourceType) -> ReadAdapterRequest:
    return ReadAdapterRequest(
        source=make_source(source_type),
        source_object_type="resource",
        source_object_id="resource-1",
        source_reference=f"{source_type.value}://resource/1",
        source_revision="rev-1",
    )


@pytest.mark.asyncio
async def test_github_read_adapter_builds_fresh_observation() -> None:
    client = RecordingReadClient({"state": "open"})
    adapter = GitHubReadAdapter(client)
    request = make_request(SourceType.GITHUB)

    observation = await adapter.observe(request)

    assert client.references == [request.source_reference]
    assert observation.source_id == request.source.source_id
    assert observation.source_revision == "rev-1"
    assert observation.payload_normalized == {"state": "open"}
    assert observation.observation_status is ObservationStatus.OBSERVED
    assert observation.freshness_state is FreshnessState.FRESH
    assert observation.current_confirmed is True


@pytest.mark.asyncio
async def test_notion_read_adapter_builds_observation() -> None:
    client = RecordingReadClient({"status": "observed"})
    adapter = NotionReadAdapter(client)
    request = make_request(SourceType.NOTION)

    observation = await adapter.observe(request)

    assert client.references == [request.source_reference]
    assert observation.payload_normalized == {"status": "observed"}
    assert observation.current_confirmed is True


@pytest.mark.asyncio
async def test_partial_provider_result_never_becomes_current_confirmed() -> None:
    adapter = GitHubReadAdapter(
        RecordingReadClient(
            ProviderReadResult(
                payload={"state": "partial"},
                observation_status=ObservationStatus.PARTIAL,
            )
        )
    )

    observation = await adapter.observe(make_request(SourceType.GITHUB))

    assert observation.observation_status is ObservationStatus.PARTIAL
    assert observation.freshness_state is FreshnessState.FRESH
    assert observation.current_confirmed is False


@pytest.mark.asyncio
async def test_adapter_rejects_mismatched_source_before_provider_call() -> None:
    client = RecordingReadClient({"state": "open"})
    adapter = GitHubReadAdapter(client)

    with pytest.raises(SourceReadError):
        await adapter.observe(make_request(SourceType.NOTION))

    assert client.references == []


@pytest.mark.asyncio
async def test_provider_failure_maps_to_fail_closed_error_observation() -> None:
    adapter = GitHubReadAdapter(FailingReadClient())

    observation = await adapter.observe(make_request(SourceType.GITHUB))

    assert observation.observation_status is ObservationStatus.ERROR
    assert observation.freshness_state is FreshnessState.UNKNOWN
    assert observation.current_confirmed is False
    assert observation.payload_normalized == {"source_error": True}


def test_observe_adapters_expose_no_mutation_methods() -> None:
    client = RecordingReadClient({})
    adapters = (GitHubReadAdapter(client), NotionReadAdapter(client))

    for adapter in adapters:
        assert not hasattr(adapter, "create")
        assert not hasattr(adapter, "update")
        assert not hasattr(adapter, "delete")
        assert not hasattr(adapter, "merge")


@pytest.mark.asyncio
async def test_concrete_github_client_is_get_only_and_preserves_revision() -> None:
    recorded_methods: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        recorded_methods.append(request.method)
        return httpx.Response(
            200,
            headers={"ETag": '"github-revision"'},
            json={
                "id": 1,
                "state": "open",
                "updated_at": "2026-08-28T20:00:00Z",
            },
        )

    client = GitHubReadClient(transport=httpx.MockTransport(handler))
    result = await client.fetch("https://api.github.com/repos/openai/openai")

    assert recorded_methods == ["GET"]
    assert result.observation_status is ObservationStatus.OBSERVED
    assert result.source_revision == '"github-revision"'
    assert result.source_updated_at == datetime(2026, 8, 28, 20, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_concrete_notion_client_is_get_only_and_injected() -> None:
    recorded_methods: list[str] = []
    authorization: list[str | None] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        recorded_methods.append(request.method)
        authorization.append(request.headers.get("Authorization"))
        return httpx.Response(
            200,
            json={
                "object": "page",
                "id": "page-1",
                "last_edited_time": "2026-08-28T20:01:00Z",
            },
        )

    client = NotionReadClient(
        token="injected-test-token",
        transport=httpx.MockTransport(handler),
    )
    result = await client.fetch("https://api.notion.com/v1/pages/page-1")

    assert recorded_methods == ["GET"]
    assert authorization == ["Bearer injected-test-token"]
    assert result.observation_status is ObservationStatus.OBSERVED
    assert result.source_revision == "2026-08-28T20:01:00Z"
    assert result.source_updated_at == datetime(2026, 8, 28, 20, 1, tzinfo=UTC)


def test_notion_client_rejects_missing_injected_token() -> None:
    with pytest.raises(ValueError):
        NotionReadClient(token="")
