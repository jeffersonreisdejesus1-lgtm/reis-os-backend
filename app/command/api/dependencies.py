from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api.dependencies import CurrentUser
from app.memberships.domain.enums import MembershipRole, MembershipStatus
from app.memberships.infrastructure.models import MembershipModel
from app.shared.config.settings import Settings, get_settings
from app.shared.database.session import get_db_session
from app.shared.errors.exceptions import AppError
from app.shared.security.organization import CurrentOrganizationId

COMMAND_READ_ROLES = frozenset({MembershipRole.OWNER, MembershipRole.ADMIN})


def get_command_institution_organization_id(
    settings: Annotated[Settings, Depends(get_settings)],
) -> UUID:
    organization_id = settings.command_institution_organization_id
    if organization_id is None:
        raise AppError(
            "Command institutional organization is not configured.",
            code="command_institution_not_configured",
            status_code=503,
        )
    return organization_id


CommandInstitutionOrganizationId = Annotated[
    UUID, Depends(get_command_institution_organization_id)
]


async def _active_command_role(
    *,
    current_user: CurrentUser,
    organization_id: UUID,
    session: AsyncSession,
) -> MembershipRole | None:
    return await session.scalar(
        select(MembershipModel.role).where(
            MembershipModel.organization_id == organization_id,
            MembershipModel.user_id == current_user.id,
            MembershipModel.status == MembershipStatus.ACTIVE,
        )
    )


def _require_institution_binding(
    organization_id: UUID,
    institution_organization_id: UUID,
) -> None:
    if organization_id != institution_organization_id:
        raise AppError(
            "Organization is not authorized for REIS OS Command.",
            code="command_organization_forbidden",
            status_code=403,
        )


async def require_command_read_access(
    current_user: CurrentUser,
    organization_id: CurrentOrganizationId,
    institution_organization_id: CommandInstitutionOrganizationId,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    _require_institution_binding(organization_id, institution_organization_id)
    role = await _active_command_role(
        current_user=current_user,
        organization_id=institution_organization_id,
        session=session,
    )
    if role not in COMMAND_READ_ROLES:
        raise AppError(
            "Command read access requires an owner or admin membership.",
            code="command_read_forbidden",
            status_code=403,
        )


async def require_command_founder_access(
    current_user: CurrentUser,
    organization_id: CurrentOrganizationId,
    institution_organization_id: CommandInstitutionOrganizationId,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    _require_institution_binding(organization_id, institution_organization_id)
    role = await _active_command_role(
        current_user=current_user,
        organization_id=institution_organization_id,
        session=session,
    )
    if role is not MembershipRole.OWNER:
        raise AppError(
            "Founder-sensitive Command access requires owner membership.",
            code="command_founder_access_forbidden",
            status_code=403,
        )


CommandReadAccess = Annotated[None, Depends(require_command_read_access)]
CommandFounderAccess = Annotated[None, Depends(require_command_founder_access)]
