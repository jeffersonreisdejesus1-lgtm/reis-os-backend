"""Controlled, idempotent Founder bootstrap for COMMAND v0.1.

Run only from an administrative/deployment context after migrations:

    COMMAND_FOUNDER_EMAIL=... COMMAND_FOUNDER_PASSWORD=... \
    python -m app.command.bootstrap

The bootstrap is deliberately outside the public API surface.
"""

import asyncio
import os

from sqlalchemy import select

from app.memberships.domain.enums import MembershipRole, MembershipStatus
from app.memberships.infrastructure.models import MembershipModel
from app.organizations.infrastructure.models import OrganizationModel
from app.shared.config.settings import get_settings
from app.shared.database.session import SessionLocal, engine
from app.shared.security.passwords import hash_password
from app.users.infrastructure.models import UserModel


async def bootstrap_founder() -> None:
    settings = get_settings()
    email = os.environ.get("COMMAND_FOUNDER_EMAIL", "").strip().lower()
    password = os.environ.get("COMMAND_FOUNDER_PASSWORD", "")
    display_name = os.environ.get("COMMAND_FOUNDER_DISPLAY_NAME", "Founder").strip()
    if not email or not password:
        raise RuntimeError(
            "COMMAND_FOUNDER_EMAIL and COMMAND_FOUNDER_PASSWORD are required"
        )
    if len(password) < 12:
        raise RuntimeError("Founder password must contain at least 12 characters")

    async with SessionLocal() as session:
        user = await session.scalar(select(UserModel).where(UserModel.email == email))
        if user is None:
            user = UserModel(
                email=email,
                password_hash=hash_password(password),
                display_name=display_name or "Founder",
                is_active=True,
            )
            session.add(user)
            await session.flush()

        organization = await session.scalar(
            select(OrganizationModel).where(
                OrganizationModel.slug == settings.canonical_institution_slug
            )
        )
        if organization is None:
            organization = OrganizationModel(
                name=settings.canonical_institution_name,
                slug=settings.canonical_institution_slug,
                created_by=user.id,
            )
            session.add(organization)
            await session.flush()

        membership = await session.scalar(
            select(MembershipModel).where(
                MembershipModel.organization_id == organization.id,
                MembershipModel.user_id == user.id,
            )
        )
        if membership is None:
            session.add(
                MembershipModel(
                    organization_id=organization.id,
                    user_id=user.id,
                    role=MembershipRole.OWNER,
                    status=MembershipStatus.ACTIVE,
                )
            )
        else:
            membership.role = MembershipRole.OWNER
            membership.status = MembershipStatus.ACTIVE

        await session.commit()
        print("Founder bootstrap complete for canonical institution.")


async def _main() -> None:
    try:
        await bootstrap_founder()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
