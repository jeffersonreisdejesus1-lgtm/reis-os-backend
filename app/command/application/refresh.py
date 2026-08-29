import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.command.adapters.base import BaseReadAdapter, ReadAdapterRequest
from app.command.adapters.github import GitHubReadAdapter, GitHubReadClient
from app.command.adapters.notion import NotionReadAdapter, NotionReadClient
from app.command.application.ingestion import ingest_provider_read
from app.command.domain.observation import ObservationStatus, SourceContract, SourceType
from app.command.infrastructure.models import CommandSourceModel
from app.command.infrastructure.refresh_models import CommandRefreshPolicyModel
from app.shared.config.settings import Settings, get_settings
from app.shared.database.session import SessionLocal


def _adapter_for_source(
    source_type: SourceType,
    settings: Settings,
) -> BaseReadAdapter:
    if source_type is SourceType.GITHUB:
        token = (
            settings.command_github_token.get_secret_value()
            if settings.command_github_token is not None
            else None
        )
        return GitHubReadAdapter(GitHubReadClient(token=token))
    if source_type is SourceType.NOTION:
        if settings.command_notion_token is None:
            raise RuntimeError("Notion refresh requires server-side credentials")
        return NotionReadAdapter(
            NotionReadClient(
                token=settings.command_notion_token.get_secret_value(),
                notion_version=settings.command_notion_version,
            )
        )
    raise RuntimeError("Unsupported Command source type")


async def refresh_due_sources(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    settings: Settings | None = None,
) -> int:
    """Refresh due material facts through server-side read adapters only.

    The policy is persisted, so restart/hydration never treats an existing
    projection as current merely because it exists. Each source/fact class
    carries its own next eligibility and result.
    """
    current_time = now or datetime.now(UTC)
    runtime_settings = settings or get_settings()
    policies = (
        await session.scalars(
            select(CommandRefreshPolicyModel)
            .where(
                CommandRefreshPolicyModel.enabled.is_(True),
                or_(
                    CommandRefreshPolicyModel.next_eligible_at.is_(None),
                    CommandRefreshPolicyModel.next_eligible_at <= current_time,
                ),
            )
            .order_by(CommandRefreshPolicyModel.next_eligible_at)
        )
    ).all()

    refreshed = 0
    for policy in policies:
        source = await session.scalar(
            select(CommandSourceModel).where(
                CommandSourceModel.id == policy.source_id,
                CommandSourceModel.organization_id == policy.organization_id,
                CommandSourceModel.enabled.is_(True),
            )
        )
        policy.last_attempted_observation_at = current_time
        policy.next_eligible_at = current_time + timedelta(
            seconds=policy.refresh_interval_seconds
        )
        if source is None:
            policy.last_result = ObservationStatus.ERROR.value
            await session.commit()
            continue

        source_contract = SourceContract(
            source_id=source.id,
            source_type=source.source_type,
            display_name=source.display_name,
            authority_scope=source.authority_scope,
            enabled=source.enabled,
        )
        request = ReadAdapterRequest(
            source=source_contract,
            source_object_type=policy.source_object_type,
            source_object_id=policy.source_object_id,
            source_reference=policy.source_reference,
        )
        try:
            adapter = _adapter_for_source(source.source_type, runtime_settings)
            receipt = await ingest_provider_read(
                session,
                organization_id=policy.organization_id,
                adapter=adapter,
                request=request,
                object_key=policy.object_key,
                object_type=policy.object_type,
            )
        except Exception:
            # Provider/config failures are contained per source. Never promote
            # another source's success to global success.
            policy.last_result = ObservationStatus.ERROR.value
            await session.commit()
            continue

        policy.last_result = receipt.reliability_status.value
        if receipt.reliability_status is ObservationStatus.OBSERVED:
            policy.last_successful_observation_at = current_time
        await session.commit()
        refreshed += 1

    return refreshed


async def refresh_supervisor() -> None:
    """Backend scheduler for the observation lifecycle; no frontend trigger."""
    settings = get_settings()
    while True:
        try:
            async with SessionLocal() as session:
                await refresh_due_sources(session, settings=settings)
        except Exception:
            # The supervisor is fail-contained. Individual source reliability
            # remains visible through persisted policy/observation state.
            pass
        await asyncio.sleep(settings.command_refresh_poll_seconds)
