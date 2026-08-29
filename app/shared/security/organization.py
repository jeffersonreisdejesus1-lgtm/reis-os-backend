from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api.dependencies import CurrentUser
from app.memberships.domain.enums import MembershipStatus
from app.memberships.infrastructure.models import MembershipModel
from app.organizations.infrastructure.models import OrganizationModel
from app.shared.config.settings import get_settings
from app.shared.database.session import get_db_session
from app.shared.errors.exceptions import AppError


async def get_current_organization_id(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    organization_id: Annotated[UUID | None, Header(alias="X-Organization-ID")] = None,
) -> UUID:
    settings = get_settings()

    # The platform can retain its internal multi-org capability behind an
    # explicit gate. COMMAND v0.1 keeps this disabled by default.
    if settings.organization_self_service_enabled:
        if organization_id is None:
            raise AppError(
                "Organization context is required.",
                code="organization_required",
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

    canonical = await session.scalar(
        select(OrganizationModel.id)
        .join(MembershipModel)
        .where(
            OrganizationModel.slug == settings.canonical_institution_slug,
            MembershipModel.organization_id == OrganizationModel.id,
            MembershipModel.user_id == current_user.id,
            MembershipModel.status == MembershipStatus.ACTIVE,
        )
    )
    if canonical is None:
        raise AppError(
            "Institution not found or access denied.",
            code="institution_not_found",
            status_code=404,
        )
    if organization_id is not None and organization_id != canonical:
        raise AppError(
            "Organization context does not grant authority.",
            code="organization_not_found",
            status_code=404,
        )
    return canonical


CurrentOrganizationId = Annotated[UUID, Depends(get_current_organization_id)]
