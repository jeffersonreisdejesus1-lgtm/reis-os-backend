from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.tasks.domain.enums import TaskStatus


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    assignee_id: UUID | None = None
    due_date: datetime | None = None


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    assignee_id: UUID | None = None
    due_date: datetime | None = None


class TaskTransitionRequest(BaseModel):
    target_status: TaskStatus


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: TaskStatus
    assignee_id: UUID | None
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime
