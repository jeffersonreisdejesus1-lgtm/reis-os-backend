from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AssuranceStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"


class AssuranceVerdict(StrEnum):
    PASS = "pass"
    HOLD = "hold"
    FAIL = "fail"
    INDETERMINATE = "indeterminate"


class HomologationState(StrEnum):
    NOT_HOMOLOGATED = "not_homologated"
    HOMOLOGATED = "homologated"
    UNKNOWN = "unknown"


class AssuranceResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    assurance_id: UUID = Field(default_factory=uuid4)
    object_key: str = Field(min_length=1, max_length=255)
    scope: str = Field(min_length=1, max_length=500)
    status: AssuranceStatus
    material: bool
    verdict: AssuranceVerdict | None = None
    evidence_refs: tuple[str, ...] = ()
    performer_ref: str = Field(min_length=1, max_length=255)
    completed_at: datetime | None = None
    source_reference: str | None = None
    source_revision: str | None = None
    homologation_state: HomologationState = HomologationState.UNKNOWN

    @model_validator(mode="after")
    def validate_assurance_integrity(self) -> Self:
        if self.status is AssuranceStatus.COMPLETED:
            if self.completed_at is None:
                raise ValueError("Completed assurance requires completion timestamp")
            if self.material and self.verdict is None:
                raise ValueError("Material completed assurance requires a verdict")
            if self.material and not self.evidence_refs:
                raise ValueError(
                    "Material completed assurance requires evidence references"
                )
        else:
            if self.verdict is not None:
                raise ValueError(
                    "Pending/running assurance cannot carry a final verdict"
                )
            if self.completed_at is not None:
                raise ValueError("Pending/running assurance cannot be completed")

        if self.source_reference is not None and not self.source_reference.strip():
            raise ValueError("External assurance provenance reference cannot be blank")

        return self
