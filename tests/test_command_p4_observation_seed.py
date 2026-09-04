import pytest
from sqlalchemy import func, select

from app.command.application.seed import ensure_initial_observation_seed
from app.command.domain.observation import SourceType
from app.command.infrastructure.models import CommandSourceModel
from app.command.infrastructure.refresh_models import CommandRefreshPolicyModel
from app.organizations.infrastructure.models import OrganizationModel
from app.shared.config.settings import get_settings
from app.shared.security.passwords import hash_password
from app.users.infrastructure.models import UserModel
from tests.conftest import TestSessionLocal

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_initial_observation_seed_is_idempotent_read_only_and_scoped() -> None:
    settings = get_settings()
    async with TestSessionLocal() as session:
        user = UserModel(
            email="seed-founder@example.com",
            password_hash=hash_password("private-seed-password"),
            display_name="Seed Founder",
            is_active=True,
        )
        session.add(user)
        await session.flush()
        organization = OrganizationModel(
            name=settings.canonical_institution_name,
            slug=settings.canonical_institution_slug,
            created_by=user.id,
        )
        session.add(organization)
        await session.commit()

        first = await ensure_initial_observation_seed(session, settings=settings)
        second = await ensure_initial_observation_seed(session, settings=settings)

        assert first.sources_created == 2
        assert first.policies_created == 2
        assert second.sources_created == 0
        assert second.policies_created == 0

        source_count = await session.scalar(
            select(func.count()).select_from(CommandSourceModel)
        )
        policy_count = await session.scalar(
            select(func.count()).select_from(CommandRefreshPolicyModel)
        )
        assert source_count == 2
        assert policy_count == 2

        sources = list((await session.scalars(select(CommandSourceModel))).all())
        assert {source.source_type for source in sources} == {
            SourceType.GITHUB,
            SourceType.NOTION,
        }
        assert all(source.organization_id == organization.id for source in sources)
        assert all(
            source.authority_scope.startswith("read_only:") for source in sources
        )
        assert all(source.enabled for source in sources)

        policies = list(
            (await session.scalars(select(CommandRefreshPolicyModel))).all()
        )
        by_key = {policy.object_key: policy for policy in policies}
        github = by_key["github:repository:reis-os-backend"]
        notion = by_key["notion:evolution-core:institucional"]

        assert github.organization_id == organization.id
        assert github.source_reference == (
            "https://api.github.com/repos/"
            "jeffersonreisdejesus1-lgtm/reis-os-backend"
        )
        assert github.source_object_id == (
            "jeffersonreisdejesus1-lgtm/reis-os-backend"
        )
        assert notion.organization_id == organization.id
        assert notion.source_reference == (
            "https://api.notion.com/v1/pages/"
            "3cad31bc-7b67-8177-9aef-c4eb3c4ddfd7"
        )
        assert notion.source_object_id == "3cad31bc-7b67-8177-9aef-c4eb3c4ddfd7"
        assert all(policy.enabled for policy in policies)
        assert all(
            policy.failure_behavior == "preserve_last_known_degraded"
            for policy in policies
        )


@pytest.mark.asyncio
async def test_initial_observation_seed_waits_for_canonical_institution() -> None:
    settings = get_settings()
    async with TestSessionLocal() as session:
        result = await ensure_initial_observation_seed(session, settings=settings)
        assert result.sources_created == 0
        assert result.policies_created == 0

        source_count = await session.scalar(
            select(func.count()).select_from(CommandSourceModel)
        )
        policy_count = await session.scalar(
            select(func.count()).select_from(CommandRefreshPolicyModel)
        )
        assert source_count == 0
        assert policy_count == 0
