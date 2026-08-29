from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select

from app.command.adapters.github import GitHubReadAdapter, GitHubReadClient
from app.command.application import refresh as refresh_module
from app.command.application.queries import list_projection_views
from app.command.application.refresh import refresh_due_sources
from app.command.domain.observation import (
    FreshnessState,
    ObservationStatus,
    SourceType,
)
from app.command.infrastructure.models import CommandSourceModel
from app.command.infrastructure.refresh_models import CommandRefreshPolicyModel
from app.organizations.infrastructure.models import OrganizationModel
from app.shared.security.passwords import hash_password
from app.users.infrastructure.models import UserModel
from tests.conftest import TestSessionLocal

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_refresh_is_backend_owned_and_preserves_per_source_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ok"):
            return httpx.Response(
                200,
                headers={"ETag": '"rev-ok"'},
                json={"id": "ok", "state": "open"},
            )
        return httpx.Response(503, json={"message": "provider unavailable"})

    adapter = GitHubReadAdapter(
        GitHubReadClient(transport=httpx.MockTransport(provider))
    )
    monkeypatch.setattr(
        refresh_module,
        "_adapter_for_source",
        lambda _source_type, _settings: adapter,
    )

    now = datetime(2026, 8, 29, 3, 0, tzinfo=UTC)
    async with TestSessionLocal() as session:
        user = UserModel(
            email="refresh-founder@example.com",
            password_hash=hash_password("private-refresh-password"),
            display_name="Refresh Founder",
            is_active=True,
        )
        session.add(user)
        await session.flush()
        organization = OrganizationModel(
            name="REIS OS",
            slug="reis-os",
            created_by=user.id,
        )
        session.add(organization)
        await session.flush()

        source_ok = CommandSourceModel(
            organization_id=organization.id,
            source_type=SourceType.GITHUB,
            display_name="refresh-ok",
            authority_scope="read_only",
            enabled=True,
        )
        source_error = CommandSourceModel(
            organization_id=organization.id,
            source_type=SourceType.GITHUB,
            display_name="refresh-error",
            authority_scope="read_only",
            enabled=True,
        )
        session.add_all([source_ok, source_error])
        await session.flush()

        policy_ok = CommandRefreshPolicyModel(
            organization_id=organization.id,
            source_id=source_ok.id,
            fact_class="workflow_run",
            object_key="github:test:ok",
            object_type="workflow_run",
            source_object_type="workflow_run",
            source_object_id="ok",
            source_reference="https://api.github.com/test/ok",
            freshness_expectation_seconds=60,
            refresh_interval_seconds=60,
            stale_threshold_seconds=120,
        )
        policy_error = CommandRefreshPolicyModel(
            organization_id=organization.id,
            source_id=source_error.id,
            fact_class="workflow_run",
            object_key="github:test:error",
            object_type="workflow_run",
            source_object_type="workflow_run",
            source_object_id="error",
            source_reference="https://api.github.com/test/error",
            freshness_expectation_seconds=60,
            refresh_interval_seconds=60,
            stale_threshold_seconds=120,
        )
        session.add_all([policy_ok, policy_error])
        await session.commit()

        refreshed = await refresh_due_sources(session, now=now)
        assert refreshed == 2

        ok = await session.scalar(
            select(CommandRefreshPolicyModel).where(
                CommandRefreshPolicyModel.id == policy_ok.id
            )
        )
        error = await session.scalar(
            select(CommandRefreshPolicyModel).where(
                CommandRefreshPolicyModel.id == policy_error.id
            )
        )
        assert ok is not None
        assert error is not None
        assert ok.last_result == ObservationStatus.OBSERVED.value
        assert ok.last_attempted_observation_at == now
        assert ok.last_successful_observation_at == now
        assert ok.next_eligible_at is not None
        assert error.last_result == ObservationStatus.ERROR.value
        assert error.last_attempted_observation_at == now
        assert error.last_successful_observation_at is None

        views = await list_projection_views(
            session,
            organization_id=organization.id,
        )
        reliability = {item.object_key: item.reliability_status for item in views}
        assert reliability["github:test:ok"] is ObservationStatus.OBSERVED
        assert reliability["github:test:error"] is ObservationStatus.ERROR

        ok.stale_threshold_seconds = 0
        await session.commit()
        aged_views = await list_projection_views(
            session,
            organization_id=organization.id,
        )
        view_by_key = {item.object_key: item for item in aged_views}
        assert view_by_key["github:test:ok"].freshness_state is FreshnessState.STALE
        assert view_by_key["github:test:ok"].trusted_current is False
