from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.infrastructure.models import AuditEventModel
from app.memberships.domain.enums import MembershipRole, MembershipStatus
from app.memberships.infrastructure.models import MembershipModel
from app.organizations.infrastructure.models import OrganizationModel
from app.shared.errors.exceptions import AppError
from app.users.infrastructure.models import UserModel


async def create_organization(
    session: AsyncSession,
    *,
    current_user: UserModel,
    name: str,
    slug: str,
) -> tuple[OrganizationModel, MembershipModel]:
    organization = OrganizationModel(
        name=name.strip(), slug=slug.lower(), created_by=current_user.id
    )
    session.add(organization)
    try:
        await session.flush()
        membership = MembershipModel(
            organization_id=organization.id,
            user_id=current_user.id,
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )
        session.add(membership)
        audit_event = AuditEventModel(
            organization_id=organization.id,
            actor_user_id=current_user.id,
            action="organization.created",
            entity_type="organization",
            entity_id=organization.id,
            before_data=None,
            after_data={"name": organization.name, "slug": organization.slug},
        )
        session.add(audit_event)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            "Organization slug is already in use.",
            code="organization_slug_conflict",
            status_code=409,
        ) from exc
    except Exception:
        await session.rollback()
        raise
    await session.refresh(organization)
    await session.refresh(membership)
    return organization, membership
