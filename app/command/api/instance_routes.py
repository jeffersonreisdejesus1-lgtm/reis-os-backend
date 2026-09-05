from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.command.api.dependencies import CommandReadAccess
from app.command.instance_views import (
    CommandInstanceViews,
    InstanceFilter,
    encode_instance_sse,
)
from app.shared.config.settings import Settings, get_settings
from app.shared.errors.exceptions import AppError

router = APIRouter(prefix="/v1/command", tags=["command-instances"])


def _views(settings: Settings) -> CommandInstanceViews:
    return CommandInstanceViews(settings.ocs_instance_store_path)


def _filters(
    mission_id: str | None,
    ocs_id: str | None,
    canonical_status: str | None,
    operational_phase: str | None,
) -> InstanceFilter:
    return InstanceFilter(
        mission_id=mission_id,
        ocs_id=ocs_id,
        canonical_status=canonical_status,
        operational_phase=operational_phase,
    )


def _projection_error(exc: ValueError) -> AppError:
    return AppError(
        "Command instance projection request is invalid.",
        code=str(exc),
        status_code=409,
    )


@router.get("/instances")
async def list_instances(
    command_read_access: CommandReadAccess,
    settings: Annotated[Settings, Depends(get_settings)],
    mission_id: str | None = None,
    ocs_id: str | None = None,
    canonical_status: str | None = None,
    operational_phase: str | None = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> dict[str, Any]:
    try:
        return _views(settings).list_instances(
            filters=_filters(mission_id, ocs_id, canonical_status, operational_phase),
            cursor=cursor,
            limit=limit,
        )
    except ValueError as exc:
        raise _projection_error(exc) from exc


@router.get("/instances/realtime")
async def stream_instances(
    command_read_access: CommandReadAccess,
    settings: Annotated[Settings, Depends(get_settings)],
    cursor: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> StreamingResponse:
    try:
        batch = _views(settings).journal_feed(cursor=cursor, limit=limit)
    except ValueError as exc:
        raise _projection_error(exc) from exc
    return StreamingResponse(
        encode_instance_sse(batch),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Command-Cursor": str(batch["next_cursor"]),
            "X-Command-Freshness": str(batch["freshness"]),
            "X-Command-Fallback": "/v1/command/instances",
        },
    )


@router.get("/instances/{binding_id}")
async def get_instance(
    binding_id: str,
    command_read_access: CommandReadAccess,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    return _views(settings).get(binding_id)


@router.get("/instances/{binding_id}/lineage")
async def get_instance_lineage(
    binding_id: str,
    command_read_access: CommandReadAccess,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    return _views(settings).lineage(binding_id)


@router.get("/instances/{binding_id}/comparison")
async def compare_instance_recovery(
    binding_id: str,
    command_read_access: CommandReadAccess,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    return _views(settings).comparison(binding_id)


@router.get("/recovery-center")
async def get_recovery_center(
    command_read_access: CommandReadAccess,
    settings: Annotated[Settings, Depends(get_settings)],
    mission_id: str | None = None,
    ocs_id: str | None = None,
    canonical_status: str | None = None,
    operational_phase: str | None = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> dict[str, Any]:
    try:
        return _views(settings).recovery_center(
            filters=_filters(mission_id, ocs_id, canonical_status, operational_phase),
            cursor=cursor,
            limit=limit,
        )
    except ValueError as exc:
        raise _projection_error(exc) from exc
