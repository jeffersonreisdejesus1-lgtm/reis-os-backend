import json
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.command.adapters.base import ReadAdapterRequest
from app.command.adapters.notion import NotionReadAdapter, NotionReadClient
from app.command.application.ingestion import ingest_provider_read
from app.command.domain.observation import SourceContract, SourceType
from tests.conftest import TestSessionLocal

_NOTION_TOKEN = os.getenv("COMMAND_NOTION_TOKEN")
_NOTION_PAGE_ID = os.getenv("COMMAND_NOTION_EVIDENCE_PAGE_ID")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _NOTION_TOKEN or not _NOTION_PAGE_ID,
        reason="live Notion evidence requires authorized runtime configuration",
    ),
]


async def setup_owner(client: AsyncClient) -> tuple[str, UUID]:
    registered = await client.post(
        "/auth/register",
        json={
            "email": "pa6-live-notion@example.com",
            "password": "strong-password",
            "display_name": "PA6 Live Notion",
        },
    )
    assert registered.status_code == 201, registered.text
    token = registered.json()["access_token"]
    organization = await client.post(
        "/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "PA6 LIVE NOTION", "slug": "pa6-live-notion"},
    )
    assert organization.status_code == 201, organization.text
    return token, UUID(organization.json()["id"])


def headers(token: str, organization_id: UUID) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-ID": str(organization_id),
    }


@pytest.mark.asyncio
async def test_real_notion_provider_crosses_observation_pipeline(
    client: AsyncClient,
) -> None:
    assert _NOTION_TOKEN is not None
    assert _NOTION_PAGE_ID is not None
    token, organization_id = await setup_owner(client)

    source = SourceContract(
        source_id=uuid4(),
        source_type=SourceType.NOTION,
        display_name="Notion runtime evidence",
        authority_scope="read_only",
    )
    source_reference = f"https://api.notion.com/v1/pages/{_NOTION_PAGE_ID}"
    request = ReadAdapterRequest(
        source=source,
        source_object_type="page",
        source_object_id=_NOTION_PAGE_ID,
        source_reference=source_reference,
    )
    object_key = f"notion:page:{_NOTION_PAGE_ID}"

    async with TestSessionLocal() as session:
        receipt = await ingest_provider_read(
            session,
            organization_id=organization_id,
            adapter=NotionReadAdapter(NotionReadClient(token=_NOTION_TOKEN)),
            request=request,
            object_key=object_key,
            object_type="page",
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
        "provider": "notion",
        "real_provider_object": _NOTION_PAGE_ID,
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
    Path("artifacts/notion-live-provider.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True),
        encoding="utf-8",
    )
