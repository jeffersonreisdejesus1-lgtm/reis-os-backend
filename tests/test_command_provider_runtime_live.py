import json
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.command.adapters.base import ReadAdapterRequest
from app.command.adapters.github import GitHubReadAdapter, GitHubReadClient
from app.command.application.ingestion import ingest_provider_read
from app.command.domain.observation import SourceContract, SourceType
from tests.conftest import TestSessionLocal

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("COMMAND_LIVE_GITHUB_EVIDENCE") != "1",
        reason="live GitHub provider evidence is opt-in",
    ),
]


async def setup_owner(client: AsyncClient) -> tuple[str, UUID]:
    registered = await client.post(
        "/auth/register",
        json={
            "email": "pa6-live-github@example.com",
            "password": "strong-password",
            "display_name": "PA6 Live GitHub",
        },
    )
    assert registered.status_code == 201, registered.text
    token = registered.json()["access_token"]
    organization = await client.post(
        "/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "PA6 LIVE GITHUB", "slug": "pa6-live-github"},
    )
    assert organization.status_code == 201, organization.text
    return token, UUID(organization.json()["id"])


def headers(token: str, organization_id: UUID) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-ID": str(organization_id),
    }


@pytest.mark.asyncio
async def test_real_github_provider_crosses_observation_pipeline(
    client: AsyncClient,
) -> None:
    github_token = os.getenv("COMMAND_GITHUB_TOKEN")
    assert github_token, "live GitHub evidence requires injected runtime token"
    token, organization_id = await setup_owner(client)

    source = SourceContract(
        source_id=uuid4(),
        source_type=SourceType.GITHUB,
        display_name="GitHub runtime evidence",
        authority_scope="read_only",
    )
    source_reference = (
        "https://api.github.com/repos/jeffersonreisdejesus1-lgtm/reis-os-backend"
    )
    request = ReadAdapterRequest(
        source=source,
        source_object_type="repository",
        source_object_id="reis-os-backend",
        source_reference=source_reference,
    )
    object_key = "github:repository:reis-os-backend"

    async with TestSessionLocal() as session:
        receipt = await ingest_provider_read(
            session,
            organization_id=organization_id,
            adapter=GitHubReadAdapter(GitHubReadClient(token=github_token)),
            request=request,
            object_key=object_key,
            object_type="repository",
        )

    detail = await client.get(
        f"/command/objects/{object_key}",
        headers=headers(token, organization_id),
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["projection"] is not None
    assert body["provenance"]
    assert body["provenance"][0]["source_reference"] == source_reference
    assert body["provenance"][0]["source_revision"]
    assert body["projection"]["reliability_status"] == "observed"
    assert body["projection"]["trusted_current"] is True

    evidence = {
        "provider": "github",
        "real_provider_object": "jeffersonreisdejesus1-lgtm/reis-os-backend",
        "source_reference": source_reference,
        "source_revision": body["provenance"][0]["source_revision"],
        "observed_at": body["provenance"][0]["observed_at"],
        "observation_id": str(receipt.observation_id),
        "projection_id": str(receipt.projection_id),
        "object_key": receipt.object_key,
        "freshness_state": receipt.freshness_state.value,
        "reliability_status": receipt.reliability_status.value,
        "trusted_current": receipt.trusted_current,
        "presentation_readback": body["projection"],
        "external_mutation": False,
    }
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/github-live-provider.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True),
        encoding="utf-8",
    )
