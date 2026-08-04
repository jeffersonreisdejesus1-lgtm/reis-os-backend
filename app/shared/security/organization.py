from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api.dependencies import CurrentUser
from app.memberships.domain.enums import MembershipStatus
from app.memberships.infrastructure.models import MembershipModel
from app.shared.database.session import get_db_session
from app.shared.errors.exceptions import AppError


async def get_current_organization_id(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    organization_id: Annotated[UUID | None, Header(alias="X-Organization-ID")] = None,
) -> UUID:
    if organization_id is None:
        raise AppError(
            "X-Organization-ID header is required.",
            code="organization_context_required",
            status_code=400,
        )
    membership = await session.scalar(
        select(MembershipModel.id).where(
            MembershipModel.organization_id == organization_id,
            MembershipModel.user_id == current_user.id,
            MembershipModel.status == MembershipStatus.ACTIVE,
        )
    )
    if membership is None:
        raise AppError(
            "Organization not found or access denied.",
            code="organization_not_found",
            status_code=404,
        )
    return organization_id


CurrentOrganizationId = Annotated[UUID, Depends(get_current_organization_id)]
