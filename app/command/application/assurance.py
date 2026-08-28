from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.command.domain.assurance import (
    AssuranceStatus,
    AssuranceVerdict,
    HomologationState,
)
from app.command.infrastructure.models import (
    AssuranceResultModel,
    OperationalObjectModel,
)


@dataclass(frozen=True)
class AssuranceView:
    assurance_id: UUID
    object_key: str
    scope: str
    status: AssuranceStatus
    material: bool
    verdict: AssuranceVerdict | None
    evidence_refs: tuple[str, ...]
    performer_ref: str
    completed_at: datetime | None
    source_reference: str | None
    source_revision: str | None
    homologation_state: HomologationState


async def list_assurance_views(
    session: AsyncSession,
    *,
    organization_id: UUID,
    limit: int = 20,
) -> list[AssuranceView]:
    rows = (
        await session.execute(
            select(AssuranceResultModel, OperationalObjectModel.object_key)
            .join(
                OperationalObjectModel,
                OperationalObjectModel.id
                == AssuranceResultModel.operational_object_id,
            )
            .where(
                AssuranceResultModel.organization_id == organization_id,
                OperationalObjectModel.organization_id == organization_id,
            )
            .order_by(AssuranceResultModel.created_at.desc())
            .limit(limit)
        )
    ).all()

    return [
        AssuranceView(
            assurance_id=item.id,
            object_key=object_key,
            scope=item.scope,
            status=item.status,
            material=item.material,
            verdict=item.verdict,
            evidence_refs=tuple(item.evidence_refs),
            performer_ref=item.performer_ref,
            completed_at=item.completed_at,
            source_reference=item.source_reference,
            source_revision=item.source_revision,
            homologation_state=item.homologation_state,
        )
        for item, object_key in rows
    ]
