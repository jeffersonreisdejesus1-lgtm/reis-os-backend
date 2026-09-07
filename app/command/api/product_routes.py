from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.command.api.dependencies import (
    CommandInstitutionOrganizationId,
    CommandReadAccess,
)
from app.command.product_views import CommandProductSources, CommandProductViews
from app.shared.config.settings import Settings, get_settings

router = APIRouter(prefix="/v1/command", tags=["command-b10"])


def _views(settings: Settings) -> CommandProductViews:
    return CommandProductViews(
        CommandProductSources(
            command_event_store_path=settings.command_event_store_path,
            ocs_instance_store_path=settings.ocs_instance_store_path,
            governance_candidate_store_path=settings.governance_candidate_store_path,
        )
    )


@router.get("/cockpit")
async def get_cockpit(
    command_read_access: CommandReadAccess,
    institution_organization_id: CommandInstitutionOrganizationId,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    """B10 aggregate Control Plane projection.

    The endpoint is intentionally GET-only and composes existing read models. It
    does not write canonical mission, authority, execution or governance state.
    """
    return await run_in_threadpool(
        _views(settings).cockpit,
        organization_id=str(institution_organization_id),
    )
