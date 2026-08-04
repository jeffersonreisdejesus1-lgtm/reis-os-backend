from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.workspaces.domain.enums import WorkspaceStatus, WorkspaceType


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=100)
    description: str | None = Field(default=None, max_length=4000)
    type: WorkspaceType


class WorkspaceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=100)
    description: str | None = Field(default=None, max_length=4000)
    archive: bool = False


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    slug: str
    description: str | None
    type: WorkspaceType
    status: WorkspaceStatus
    created_at: datetime
    updated_at: datetime
