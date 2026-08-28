from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceType(StrEnum):
    GITHUB = "github"
    NOTION = "notion"


class ObservationStatus(StrEnum):
    OBSERVED = "observed"
    PARTIAL = "partial"
    ERROR = "error"
    CONFLICT = "conflict"


class FreshnessState(StrEnum):
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


class SourceContract(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: UUID
    source_type: SourceType
    display_name: str = Field(min_length=1, max_length=160)
    authority_scope: str = Field(min_length=1, max_length=500)
    enabled: bool = True


class ObservationContract(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: UUID
    source_object_type: str = Field(min_length=1, max_length=100)
    source_object_id: str = Field(min_length=1, max_length=255)
    source_reference: str = Field(min_length=1)
    source_revision: str | None = None
    observed_at: datetime
    source_updated_at: datetime | None = None
    retrieved_at: datetime
    payload_normalized: dict[str, object]
    observation_status: ObservationStatus = ObservationStatus.OBSERVED
    freshness_state: FreshnessState = FreshnessState.UNKNOWN
    freshness_reason: str | None = None
    current_confirmed: bool = False

    @model_validator(mode="after")
    def validate_observation_invariants(self) -> Self:
        if not self.source_reference.strip():
            raise ValueError("External observations require a source reference")

        unreliable_current_states = {
            FreshnessState.STALE,
            FreshnessState.UNKNOWN,
            FreshnessState.CONFLICT,
        }
        if self.current_confirmed and self.freshness_state in unreliable_current_states:
            raise ValueError(
                "Stale, unknown, or conflicting observations cannot be current-confirmed"
            )

        if (
            self.observation_status is ObservationStatus.CONFLICT
            and self.freshness_state is not FreshnessState.CONFLICT
        ):
            raise ValueError("Conflicting observations must preserve conflict freshness")

        return self
