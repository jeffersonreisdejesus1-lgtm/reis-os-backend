from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.infrastructure.models import AuditEventModel


def add_audit_event(
    session: AsyncSession,
    *,
    organization_id: UUID,
    actor_user_id: UUID,
    action: str,
    entity_type: str,
    entity_id: UUID,
    before_data: dict[str, Any] | None,
    after_data: dict[str, Any] | None,
) -> AuditEventModel:
    event = AuditEventModel(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_data=before_data,
        after_data=after_data,
    )
    session.add(event)
    return event
