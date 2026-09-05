from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.command.api.dependencies import CommandReadAccess
from app.command.api.schemas import OCSListResponse, OCSProfileResponse
from app.command.application import get_ocs_profile, list_ocs_profiles
from app.command.dossiers import CommandDossierService
from app.command.event_store import CommandEventStore
from app.command.read_models import CommandReadModels
from app.command.realtime import CommandRealtimeFeed, encode_sse
from app.shared.config.settings import Settings, get_settings
from app.shared.errors.exceptions import AppError

router = APIRouter(prefix="/v1/command", tags=["command"])


def _read_models(settings: Settings) -> CommandReadModels:
    return CommandReadModels(settings.command_event_store_path)


def _require_material[T](value: T, resource: str) -> T:
    if value in ({}, []):
        raise AppError(
            f"Command {resource} has no material projection.",
            code="command_projection_not_materialized",
            status_code=404,
        )
    return value


@router.get("/institution")
async def get_institution(
    command_read_access: CommandReadAccess,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    return _require_material(_read_models(settings).institution(), "institution")


@router.get("/ocs", response_model=OCSListResponse)
async def list_ocs(command_read_access: CommandReadAccess) -> OCSListResponse:
    return list_ocs_profiles()


@router.get("/ocs/{ocs_slug}", response_model=OCSProfileResponse)
async def get_ocs(
    ocs_slug: str,
    command_read_access: CommandReadAccess,
) -> OCSProfileResponse:
    profile = get_ocs_profile(ocs_slug)
    if profile is None:
        raise AppError(
            "OCS profile not found.",
            code="ocs_profile_not_found",
            status_code=404,
        )
    return profile


@router.get("/dossiers")
async def list_dossiers(
    command_read_access: CommandReadAccess,
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, Any]]:
    return CommandDossierService(settings.command_event_store_path).list()


@router.get("/dossiers/{ocs_slug}")
async def get_dossier(
    ocs_slug: str,
    command_read_access: CommandReadAccess,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    dossier = CommandDossierService(settings.command_event_store_path).get(ocs_slug)
    if dossier is None:
        raise AppError(
            "OCS dossier not found.",
            code="ocs_dossier_not_found",
            status_code=404,
        )
    return dossier


@router.get("/operations")
async def list_operations(
    command_read_access: CommandReadAccess,
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, Any]]:
    return _require_material(_read_models(settings).operations(), "operations")


@router.get("/gates")
async def list_gates(
    command_read_access: CommandReadAccess,
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, Any]]:
    return _require_material(_read_models(settings).gates(), "gates")


@router.get("/events")
async def list_events(
    command_read_access: CommandReadAccess,
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, Any]]:
    return _require_material(_read_models(settings).events(), "events")


@router.get("/realtime")
async def stream_realtime(
    command_read_access: CommandReadAccess,
    settings: Annotated[Settings, Depends(get_settings)],
    cursor: Annotated[int, Query(ge=0)] = 0,
) -> StreamingResponse:
    store = CommandEventStore(settings.command_event_store_path)
    try:
        batch = CommandRealtimeFeed(store).read(cursor=cursor)
    except ValueError as exc:
        raise AppError(
            "Command realtime cursor is invalid for the current projection.",
            code=str(exc),
            status_code=409,
        ) from exc
    return StreamingResponse(
        encode_sse(batch),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Command-Cursor": str(batch.next_cursor),
            "X-Command-Freshness": batch.freshness.value,
            "X-Command-Connection": "connected",
        },
    )


@router.get("/evidence")
async def list_evidence(
    command_read_access: CommandReadAccess,
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, Any]]:
    return _require_material(_read_models(settings).evidence(), "evidence")


@router.get("/system-health")
async def get_system_health(
    command_read_access: CommandReadAccess,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    return _read_models(settings).system_health()


@router.get("/maps")
async def list_maps(
    command_read_access: CommandReadAccess,
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, Any]]:
    return _require_material(_read_models(settings).maps(), "maps")
