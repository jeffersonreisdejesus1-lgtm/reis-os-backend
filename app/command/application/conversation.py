from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.command.application.assurance import AssuranceView, list_assurance_views
from app.command.application.queries import (
    AttentionView,
    ObjectDetailView,
    ProjectionView,
    get_object_detail,
    list_attention_views,
    list_projection_views,
)
from app.command.domain.attention import AttentionClass


@dataclass(frozen=True)
class ConversationContext:
    query_text: str
    mode: str
    conclusion: str
    situation: tuple[ProjectionView, ...]
    attention: tuple[AttentionView, ...]
    blockers: tuple[AttentionView, ...]
    decisions: tuple[AttentionView, ...]
    assurances: tuple[AssuranceView, ...]
    objects: tuple[ObjectDetailView, ...]


def _build_conclusion(
    *,
    projections: tuple[ProjectionView, ...],
    blockers: tuple[AttentionView, ...],
    decisions: tuple[AttentionView, ...],
    assurances: tuple[AssuranceView, ...],
) -> str:
    return (
        f"Observed {len(projections)} projected object(s), "
        f"{len(blockers)} blocker(s), "
        f"{len(decisions)} decision-context item(s), and "
        f"{len(assurances)} assurance result(s)."
    )


async def query_conversation_context(
    session: AsyncSession,
    *,
    organization_id: UUID,
    query_text: str,
    object_keys: tuple[str, ...] = (),
    limit: int = 20,
) -> ConversationContext:
    """Build read-only conversational context from Command read models."""
    projections = tuple(
        await list_projection_views(
            session,
            organization_id=organization_id,
            limit=limit,
        )
    )
    attention = tuple(
        await list_attention_views(
            session,
            organization_id=organization_id,
            limit=limit,
        )
    )
    assurances = tuple(
        await list_assurance_views(
            session,
            organization_id=organization_id,
            limit=limit,
        )
    )
    blockers = tuple(
        item for item in attention if item.attention_class is AttentionClass.BLOCKER
    )
    decisions = tuple(
        item
        for item in attention
        if item.attention_class is AttentionClass.DECISION_PENDING
    )

    details: list[ObjectDetailView] = []
    for object_key in dict.fromkeys(object_keys):
        details.append(
            await get_object_detail(
                session,
                organization_id=organization_id,
                object_key=object_key,
            )
        )

    return ConversationContext(
        query_text=query_text,
        mode="read_only",
        conclusion=_build_conclusion(
            projections=projections,
            blockers=blockers,
            decisions=decisions,
            assurances=assurances,
        ),
        situation=projections,
        attention=attention,
        blockers=blockers,
        decisions=decisions,
        assurances=assurances,
        objects=tuple(details),
    )
