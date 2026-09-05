from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api.dependencies import CurrentUser
from app.memberships.domain.enums import MembershipRole, MembershipStatus
from app.memberships.infrastructure.models import MembershipModel
from app.shared.database.session import get_db_session
from app.shared.errors.exceptions import AppError
from app.shared.security.organization import CurrentOrganizationId

COMMAND_READ_ROLES = frozenset({MembershipRole.OWNER, MembershipRole.ADMIN})


async def require_command_read_access(
    current_user: CurrentUser,
    organization_id: CurrentOrganizationId,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    role = await session.scalar(
        select(MembershipModel.role).where(
            MembershipModel.organization_id == organization_id,
            MembershipModel.user_id == current_user.id,
            MembershipModel.status == MembershipStatus.ACTIVE,
        )
    )
    if role not in COMMAND_READ_ROLES:
        raise AppError(
            "Command read access requires an owner or admin membership.",
            code="command_read_forbidden",
            status_code=403,
        )


CommandReadAccess = Annotated[None, Depends(require_command_read_access)]
