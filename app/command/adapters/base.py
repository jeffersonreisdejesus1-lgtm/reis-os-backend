from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.command.domain.observation import (
    FreshnessState,
    ObservationContract,
    ObservationStatus,
    SourceContract,
    SourceType,
)


class ReadClient(Protocol):
    async def fetch(self, reference: str) -> dict[str, object]: ...


class ReadAdapterRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: SourceContract
    source_object_type: str = Field(min_length=1, max_length=100)
    source_object_id: str = Field(min_length=1, max_length=255)
    source_reference: str = Field(min_length=1)
    source_revision: str | None = None
    source_updated_at: datetime | None = None


class SourceReadError(RuntimeError):
    """Fail-closed error raised when a source cannot be observed safely."""


class BaseReadAdapter:
    expected_source_type: SourceType

    def __init__(self, client: ReadClient) -> None:
        self._client = client

    async def observe(self, request: ReadAdapterRequest) -> ObservationContract:
        if request.source.source_type is not self.expected_source_type:
            raise SourceReadError(
                "Read adapter source type does not match the configured source"
            )

        try:
            payload = await self._client.fetch(request.source_reference)
        except Exception as exc:
            raise SourceReadError(
                f"Unable to read {self.expected_source_type.value} source"
            ) from exc

        now = datetime.now(UTC)
        return ObservationContract(
            source_id=request.source.source_id,
            source_object_type=request.source_object_type,
            source_object_id=request.source_object_id,
            source_reference=request.source_reference,
            source_revision=request.source_revision,
            observed_at=now,
            source_updated_at=request.source_updated_at,
            retrieved_at=now,
            payload_normalized=dict(payload),
            observation_status=ObservationStatus.OBSERVED,
            freshness_state=FreshnessState.UNKNOWN,
            freshness_reason="freshness_policy_not_evaluated",
            current_confirmed=False,
        )
