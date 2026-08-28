from datetime import datetime
from urllib.parse import urlparse

import httpx

from app.command.adapters.base import BaseReadAdapter, ProviderReadResult
from app.command.domain.observation import ObservationStatus, SourceType


class GitHubReadClient:
    """Concrete GitHub REST client restricted to GET operations."""

    def __init__(
        self,
        *,
        token: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._token = token
        self._transport = transport
        self._timeout_seconds = timeout_seconds

    async def fetch(self, reference: str) -> ProviderReadResult:
        parsed = urlparse(reference)
        if parsed.scheme != "https" or parsed.netloc != "api.github.com":
            raise ValueError("GitHub read reference must use https://api.github.com")

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        async with httpx.AsyncClient(
            transport=self._transport,
            timeout=self._timeout_seconds,
            follow_redirects=False,
        ) as client:
            response = await client.get(reference, headers=headers)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("GitHub provider response must be a JSON object")

        revision = response.headers.get("etag")
        if revision is None:
            candidate = payload.get("sha")
            if isinstance(candidate, str):
                revision = candidate

        source_updated_at: datetime | None = None
        updated_at = payload.get("updated_at")
        if isinstance(updated_at, str):
            source_updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

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


class GitHubReadAdapter(BaseReadAdapter):
    expected_source_type = SourceType.GITHUB
