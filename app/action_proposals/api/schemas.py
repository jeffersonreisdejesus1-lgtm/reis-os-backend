from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.action_proposals.domain.enums import (
    ActionExecutionStatus,
    ActionProposalStatus,
)


class ActionProposalCreateRequest(BaseModel):
    action_type: str = Field(min_length=1, max_length=100)
    target: str = Field(min_length=1, max_length=500)
    payload: dict[str, Any]
    requested_by: str = Field(min_length=1, max_length=200)

    @field_validator("action_type", "target", "requested_by")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class ActionProposalApproveRequest(BaseModel):
    approved_by: str = Field(min_length=1, max_length=200)

    @field_validator("approved_by")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class ActionProposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action_type: str
    target: str
    payload: dict[str, Any]
    requested_by: str
    status: ActionProposalStatus
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None
    approved_by: str | None
    execution_status: ActionExecutionStatus | None
    executed_at: datetime | None
    execution_result: dict[str, Any] | None
