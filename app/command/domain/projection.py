from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.command.domain.observation import (
    FreshnessState,
    ObservationContract,
    ObservationStatus,
)


class OperationalObjectContract(BaseModel):
    model_config = ConfigDict(frozen=True)

    object_key: str = Field(min_length=1, max_length=255)
    object_type: str = Field(min_length=1, max_length=100)
    source_bindings: tuple[str, ...] = ()


class ProjectionContract(BaseModel):
    model_config = ConfigDict(frozen=True)

    projection_id: UUID = Field(default_factory=uuid4)
    object_key: str = Field(min_length=1, max_length=255)
    object_type: str = Field(min_length=1, max_length=100)
    projection_type: str = Field(min_length=1, max_length=100)
    observation_refs: tuple[UUID, ...] = Field(min_length=1)
    built_at: datetime
    projection_version: int = Field(ge=1)
    freshness_state: FreshnessState
    reliability_status: ObservationStatus = ObservationStatus.OBSERVED
    trusted_current: bool = False
    projection_payload: dict[str, object]


_FRESHNESS_PRECEDENCE = {
    FreshnessState.FRESH: 0,
    FreshnessState.AGING: 1,
    FreshnessState.UNKNOWN: 2,
    FreshnessState.STALE: 3,
    FreshnessState.CONFLICT: 4,
}

_RELIABILITY_PRECEDENCE = {
    ObservationStatus.OBSERVED: 0,
    ObservationStatus.PARTIAL: 1,
    ObservationStatus.ERROR: 2,
    ObservationStatus.CONFLICT: 3,
}


def freshness_priority(state: FreshnessState) -> int:
    return _FRESHNESS_PRECEDENCE[state]


def reliability_priority(status: ObservationStatus) -> int:
    return _RELIABILITY_PRECEDENCE[status]


class ProjectionBuilder:
    def build(
        self,
        operational_object: OperationalObjectContract,
        projection_type: str,
        observations: Sequence[ObservationContract],
        projection_payload: dict[str, object],
        projection_version: int = 1,
    ) -> ProjectionContract:
        if not observations:
            raise ValueError("Projection requires at least one observation")

        freshness_state = max(
            (item.freshness_state for item in observations),
            key=freshness_priority,
        )
        reliability_status = max(
            (item.observation_status for item in observations),
            key=reliability_priority,
        )
        trusted_current = (
            freshness_state is FreshnessState.FRESH
            and reliability_status is ObservationStatus.OBSERVED
            and all(item.current_confirmed for item in observations)
        )
        return ProjectionContract(
            object_key=operational_object.object_key,
            object_type=operational_object.object_type,
            projection_type=projection_type,
            observation_refs=tuple(item.observation_id for item in observations),
            built_at=datetime.now(UTC),
            projection_version=projection_version,
            freshness_state=freshness_state,
            reliability_status=reliability_status,
            trusted_current=trusted_current,
            projection_payload=dict(projection_payload),
        )
