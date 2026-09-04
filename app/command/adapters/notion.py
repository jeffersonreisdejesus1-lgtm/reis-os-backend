from datetime import datetime
from urllib.parse import urlparse

import httpx

from app.command.adapters.base import BaseReadAdapter, ProviderReadResult
from app.command.domain.observation import ObservationStatus, SourceType


class NotionReadClient:
    """Concrete Notion REST client restricted to GET operations."""

    def __init__(
        self,
        *,
        token: str,
        notion_version: str = "2022-06-28",
        transport: httpx.AsyncBaseTransport | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        if not token.strip():
            raise ValueError(
                "Notion read client requires an injected integration token"
            )
        self._token = token
        self._notion_version = notion_version
        self._transport = transport
        self._timeout_seconds = timeout_seconds

    async def fetch(self, reference: str) -> ProviderReadResult:
        parsed = urlparse(reference)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "api.notion.com"
            or not parsed.path.startswith("/v1/")
        ):
            raise ValueError("Notion read reference must use https://api.notion.com/v1/")

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Notion-Version": self._notion_version,
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(
            transport=self._transport,
            timeout=self._timeout_seconds,
            follow_redirects=False,
        ) as client:
            response = await client.get(reference, headers=headers)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Notion provider response must be a JSON object")

        revision: str | None = None
        source_updated_at: datetime | None = None
        last_edited_time = payload.get("last_edited_time")
        if isinstance(last_edited_time, str):
            revision = last_edited_time
            source_updated_at = datetime.fromisoformat(
                last_edited_time.replace("Z", "+00:00")
            )
        elif isinstance(payload.get("id"), str):
            revision = str(payload["id"])

        status = (
            ObservationStatus.PARTIAL
            if response.status_code == httpx.codes.PARTIAL_CONTENT
            else ObservationStatus.OBSERVED
        )
        return ProviderReadResult(
            payload=payload,
            observation_status=status,
            source_revision=revision,
            source_updated_at=source_updated_at,
        )


class NotionReadAdapter(BaseReadAdapter):
    expected_source_type = SourceType.NOTION
