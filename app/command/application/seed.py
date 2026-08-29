from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.command.domain.observation import SourceType
from app.command.infrastructure.models import CommandSourceModel
from app.command.infrastructure.refresh_models import CommandRefreshPolicyModel
from app.organizations.infrastructure.models import OrganizationModel
from app.shared.config.settings import Settings, get_settings


@dataclass(frozen=True)
class ObservationSeedResult:
    sources_created: int
    policies_created: int


async def ensure_initial_observation_seed(
    session: AsyncSession,
    *,
    settings: Settings | None = None,
) -> ObservationSeedResult:
    """Idempotently seed the initial private read-only observation contracts."""
    runtime_settings = settings or get_settings()
    organization = await session.scalar(
        select(OrganizationModel).where(
            OrganizationModel.slug == runtime_settings.canonical_institution_slug
        )
    )
    if organization is None:
        return ObservationSeedResult(sources_created=0, policies_created=0)

    source_specs = (
        {
            "source_type": SourceType.GITHUB,
            "display_name": "GitHub · reis-os-backend",
            "authority_scope": "read_only:repository_metadata",
            "fact_class": "repository",
            "object_key": "github:repository:reis-os-backend",
            "object_type": "repository",
            "source_object_type": "repository",
            "source_object_id": "jeffersonreisdejesus1-lgtm/reis-os-backend",
            "source_reference": (
                "https://api.github.com/repos/"
                "jeffersonreisdejesus1-lgtm/reis-os-backend"
            ),
            "freshness_expectation_seconds": 300,
            "refresh_interval_seconds": 300,
            "stale_threshold_seconds": 900,
        },
        {
            "source_type": SourceType.NOTION,
            "display_name": "Notion · Evolution Core · Institucional",
            "authority_scope": "read_only:page_metadata",
            "fact_class": "page",
            "object_key": "notion:evolution-core:institucional",
            "object_type": "notion_page",
            "source_object_type": "page",
            "source_object_id": "3cad31bc-7b67-8177-9aef-c4eb3c4ddfd7",
            "source_reference": (
                "https://api.notion.com/v1/pages/"
                "3cad31bc-7b67-8177-9aef-c4eb3c4ddfd7"
            ),
            "freshness_expectation_seconds": 300,
            "refresh_interval_seconds": 300,
            "stale_threshold_seconds": 900,
        },
    )

    sources_created = 0
    policies_created = 0
    for spec in source_specs:
        source = await session.scalar(
            select(CommandSourceModel).where(
                CommandSourceModel.organization_id == organization.id,
                CommandSourceModel.source_type == spec["source_type"],
                CommandSourceModel.display_name == spec["display_name"],
            )
        )
        if source is None:
            source = CommandSourceModel(
                organization_id=organization.id,
                source_type=spec["source_type"],
                display_name=spec["display_name"],
                authority_scope=spec["authority_scope"],
                enabled=True,
            )
            session.add(source)
            await session.flush()
            sources_created += 1
        else:
            source.authority_scope = spec["authority_scope"]
            source.enabled = True

        policy = await session.scalar(
            select(CommandRefreshPolicyModel).where(
                CommandRefreshPolicyModel.organization_id == organization.id,
                CommandRefreshPolicyModel.source_id == source.id,
                CommandRefreshPolicyModel.object_key == spec["object_key"],
            )
        )
        if policy is None:
            policy = CommandRefreshPolicyModel(
                organization_id=organization.id,
                source_id=source.id,
                fact_class=spec["fact_class"],
                object_key=spec["object_key"],
                object_type=spec["object_type"],
                source_object_type=spec["source_object_type"],
                source_object_id=spec["source_object_id"],
                source_reference=spec["source_reference"],
                freshness_expectation_seconds=spec[
                    "freshness_expectation_seconds"
                ],
                refresh_interval_seconds=spec["refresh_interval_seconds"],
                stale_threshold_seconds=spec["stale_threshold_seconds"],
                enabled=True,
            )
            session.add(policy)
            policies_created += 1
        else:
            policy.fact_class = spec["fact_class"]
            policy.object_type = spec["object_type"]
            policy.source_object_type = spec["source_object_type"]
            policy.source_object_id = spec["source_object_id"]
            policy.source_reference = spec["source_reference"]
            policy.freshness_expectation_seconds = spec[
                "freshness_expectation_seconds"
            ]
            policy.refresh_interval_seconds = spec["refresh_interval_seconds"]
            policy.stale_threshold_seconds = spec["stale_threshold_seconds"]
            policy.failure_behavior = "preserve_last_known_degraded"
            policy.enabled = True

    await session.commit()
    return ObservationSeedResult(
        sources_created=sources_created,
        policies_created=policies_created,
    )
