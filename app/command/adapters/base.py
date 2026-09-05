from dataclasses import dataclass
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


@dataclass(frozen=True)
class ProviderReadResult:
    payload: dict[str, object]
    observation_status: ObservationStatus = ObservationStatus.OBSERVED
    source_revision: str | None = None
    source_updated_at: datetime | None = None


class ReadClient(Protocol):
    async def fetch(
        self, reference: str
    ) -> dict[str, object] | ProviderReadResult: ...


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

        now = datetime.now(UTC)
        try:
            raw_result = await self._client.fetch(request.source_reference)
        except Exception:
            return ObservationContract(
                source_id=request.source.source_id,
                source_object_type=request.source_object_type,
                source_object_id=request.source_object_id,
                source_reference=request.source_reference,
                source_revision=request.source_revision,
                observed_at=now,
                source_updated_at=request.source_updated_at,
                retrieved_at=now,
                payload_normalized={"source_error": True},
                observation_status=ObservationStatus.ERROR,
                freshness_state=FreshnessState.UNKNOWN,
                freshness_reason="source_read_failed",
                current_confirmed=False,
            )

        if isinstance(raw_result, ProviderReadResult):
            payload = raw_result.payload
            status = raw_result.observation_status
            source_revision = raw_result.source_revision or request.source_revision
            source_updated_at = (
                raw_result.source_updated_at or request.source_updated_at
            )
        else:
            payload = raw_result
            status = ObservationStatus.OBSERVED
            source_revision = request.source_revision
            source_updated_at = request.source_updated_at

        if status is ObservationStatus.CONFLICT:
            freshness_state = FreshnessState.CONFLICT
            freshness_reason = "source_conflict"
        elif status is ObservationStatus.ERROR:
            freshness_state = FreshnessState.UNKNOWN
            freshness_reason = "source_read_failed"
        else:
            freshness_state = FreshnessState.FRESH
            freshness_reason = "provider_read_completed"

        return ObservationContract(
            source_id=request.source.source_id,
            source_object_type=request.source_object_type,
            source_object_id=request.source_object_id,
            source_reference=request.source_reference,
            source_revision=source_revision,
            observed_at=now,
            source_updated_at=source_updated_at,
            retrieved_at=now,
            payload_normalized=dict(payload),
            observation_status=status,
            freshness_state=freshness_state,
            freshness_reason=freshness_reason,
            current_confirmed=(
                status is ObservationStatus.OBSERVED
                and freshness_state is FreshnessState.FRESH
            ),
        )
