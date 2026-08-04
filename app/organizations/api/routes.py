from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api.dependencies import CurrentUser
from app.memberships.domain.enums import MembershipStatus
from app.memberships.infrastructure.models import MembershipModel
from app.organizations.api.schemas import (
    MembershipResponse,
    OrganizationCreatedResponse,
    OrganizationCreateRequest,
    OrganizationResponse,
)
from app.organizations.application.service import create_organization
from app.organizations.infrastructure.models import OrganizationModel
from app.shared.database.session import get_db_session
from app.shared.errors.exceptions import AppError

router = APIRouter(prefix="/organizations", tags=["organizations"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("", response_model=OrganizationCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create(
    payload: OrganizationCreateRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> OrganizationCreatedResponse:
    organization, membership = await create_organization(
        session,
        current_user=current_user,
        name=payload.name,
        slug=payload.slug,
    )
    return OrganizationCreatedResponse(
        **OrganizationResponse.model_validate(organization).model_dump(),
        membership=MembershipResponse.model_validate(membership),
    )


@router.get("", response_model=list[OrganizationResponse])
async def list_organizations(
    current_user: CurrentUser, session: DbSession
) -> list[OrganizationResponse]:
    organizations = (
        await session.scalars(
            select(OrganizationModel)
            .join(MembershipModel)
            .where(
                MembershipModel.user_id == current_user.id,
                MembershipModel.status == MembershipStatus.ACTIVE,
            )
            .order_by(OrganizationModel.name)
        )
    ).all()
    return [OrganizationResponse.model_validate(item) for item in organizations]


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> OrganizationResponse:
    organization = await session.scalar(
        select(OrganizationModel)
        .join(MembershipModel)
        .where(
            OrganizationModel.id == organization_id,
            MembershipModel.user_id == current_user.id,
            MembershipModel.status == MembershipStatus.ACTIVE,
        )
    )
    if organization is None:
        raise AppError(
            "Organization not found or access denied.",
            code="organization_not_found",
            status_code=404,
        )
    return OrganizationResponse.model_validate(organization)
