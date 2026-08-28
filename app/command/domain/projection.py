from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.command.domain.observation import FreshnessState, ObservationContract


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
    projection_payload: dict[str, object]


_FRESHNESS_PRECEDENCE = {
    FreshnessState.FRESH: 0,
    FreshnessState.AGING: 1,
    FreshnessState.UNKNOWN: 2,
    FreshnessState.STALE: 3,
    FreshnessState.CONFLICT: 4,
}


def freshness_priority(state: FreshnessState) -> int:
    return _FRESHNESS_PRECEDENCE[state]


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
        return ProjectionContract(
            object_key=operational_object.object_key,
            object_type=operational_object.object_type,
            projection_type=projection_type,
            observation_refs=tuple(item.observation_id for item in observations),
            built_at=datetime.now(UTC),
            projection_version=projection_version,
            freshness_state=freshness_state,
            projection_payload=dict(projection_payload),
        )
