from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.memberships.domain.enums import MembershipRole, MembershipStatus


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=100)


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    role: MembershipRole
    status: MembershipStatus


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class OrganizationCreatedResponse(OrganizationResponse):
    membership: MembershipResponse
