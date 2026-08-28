from uuid import uuid4

import pytest

from app.command.adapters.base import (
    ReadAdapterRequest,
    SourceReadError,
)
from app.command.adapters.github import GitHubReadAdapter
from app.command.adapters.notion import NotionReadAdapter
from app.command.domain.observation import (
    FreshnessState,
    SourceContract,
    SourceType,
)


class RecordingReadClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.references: list[str] = []

    async def fetch(self, reference: str) -> dict[str, object]:
        self.references.append(reference)
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
async def test_github_read_adapter_builds_unknown_freshness_observation() -> None:
    client = RecordingReadClient({"state": "open"})
    adapter = GitHubReadAdapter(client)
    request = make_request(SourceType.GITHUB)

    observation = await adapter.observe(request)

    assert client.references == [request.source_reference]
    assert observation.source_id == request.source.source_id
    assert observation.source_revision == "rev-1"
    assert observation.payload_normalized == {"state": "open"}
    assert observation.freshness_state is FreshnessState.UNKNOWN
    assert observation.current_confirmed is False


@pytest.mark.asyncio
async def test_notion_read_adapter_builds_observation() -> None:
    client = RecordingReadClient({"status": "observed"})
    adapter = NotionReadAdapter(client)
    request = make_request(SourceType.NOTION)

    observation = await adapter.observe(request)

    assert client.references == [request.source_reference]
    assert observation.payload_normalized == {"status": "observed"}


@pytest.mark.asyncio
async def test_adapter_rejects_mismatched_source_before_provider_call() -> None:
    client = RecordingReadClient({"state": "open"})
    adapter = GitHubReadAdapter(client)

    with pytest.raises(SourceReadError):
        await adapter.observe(make_request(SourceType.NOTION))

    assert client.references == []


@pytest.mark.asyncio
async def test_provider_failure_maps_to_source_read_error() -> None:
    adapter = GitHubReadAdapter(FailingReadClient())

    with pytest.raises(SourceReadError):
        await adapter.observe(make_request(SourceType.GITHUB))


def test_observe_adapters_expose_no_mutation_methods() -> None:
    client = RecordingReadClient({})
    adapters = (GitHubReadAdapter(client), NotionReadAdapter(client))

    for adapter in adapters:
        assert not hasattr(adapter, "create")
        assert not hasattr(adapter, "update")
        assert not hasattr(adapter, "delete")
        assert not hasattr(adapter, "merge")
