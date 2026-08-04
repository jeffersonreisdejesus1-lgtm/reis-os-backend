from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.projects.domain.enums import ProjectStatus


class ProjectCreateRequest(BaseModel):
    workspace_id: UUID
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)


class ProjectUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    progress: int | None = Field(default=None, ge=0, le=100)


class ProjectTransitionRequest(BaseModel):
    target_status: ProjectStatus


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    workspace_id: UUID
    title: str
    description: str | None
    status: ProjectStatus
    progress: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime
