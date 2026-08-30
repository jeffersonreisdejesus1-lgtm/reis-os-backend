from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.action_proposals.domain.enums import ActionProposalStatus, ExecutionStatus


class ActionProposalCreateRequest(BaseModel):
    action_type: str = Field(min_length=1, max_length=100)
    target: str = Field(min_length=1, max_length=500)
    payload: dict[str, Any]
    requested_by: str = Field(min_length=1, max_length=200)


class ActionProposalApproveRequest(BaseModel):
    approved_by: str = Field(min_length=1, max_length=200)


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
    execution_status: ExecutionStatus | None
    executed_at: datetime | None
    execution_result: dict[str, Any] | None
