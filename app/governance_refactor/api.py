from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from starlette.concurrency import run_in_threadpool

from app.command.api.dependencies import (
    CommandInstitutionOrganizationId,
    CommandReadAccess,
)
from app.governance_refactor.projections import (
    CandidateFilter,
    GovernanceCommandViews,
    GovernanceProjectionError,
)
from app.shared.config.settings import Settings, get_settings
from app.shared.errors.exceptions import AppError

router = APIRouter(prefix="/v1/command/governance", tags=["command-governance"])


def _views(settings: Settings) -> GovernanceCommandViews:
    return GovernanceCommandViews(settings.governance_candidate_store_path)


def _error(exc: GovernanceProjectionError) -> AppError:
    code = str(exc)
    status = 404 if code == "candidate_record_not_found" else 409
    return AppError(
        "Governance candidate projection failed.", code=code, status_code=status
    )


@router.get("/candidates")
async def list_candidates(
    command_read_access: CommandReadAccess,
    institution_organization_id: CommandInstitutionOrganizationId,
    settings: Annotated[Settings, Depends(get_settings)],
    record_type: str | None = None,
    mission_id: str | None = None,
    ocs_id: str | None = None,
    cursor: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> dict[str, Any]:
    try:
        return await run_in_threadpool(
            _views(settings).list_candidates,
            organization_id=str(institution_organization_id),
            filters=CandidateFilter(record_type, mission_id, ocs_id),
            cursor=cursor,
            limit=limit,
        )
    except GovernanceProjectionError as exc:
        raise _error(exc) from exc


@router.get("/candidates/{record_type}/{record_id}")
async def get_candidate(
    record_type: str,
    record_id: str,
    command_read_access: CommandReadAccess,
    institution_organization_id: CommandInstitutionOrganizationId,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    try:
        return await run_in_threadpool(
            _views(settings).get_candidate,
            organization_id=str(institution_organization_id),
            record_type=record_type,
            record_id=record_id,
        )
    except GovernanceProjectionError as exc:
        raise _error(exc) from exc


@router.get("/events")
async def list_candidate_events(
    command_read_access: CommandReadAccess,
    institution_organization_id: CommandInstitutionOrganizationId,
    settings: Annotated[Settings, Depends(get_settings)],
    cursor: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> dict[str, Any]:
    try:
        return await run_in_threadpool(
            _views(settings).events,
            organization_id=str(institution_organization_id),
            cursor=cursor,
            limit=limit,
        )
    except GovernanceProjectionError as exc:
        raise _error(exc) from exc


@router.get("/summary")
async def governance_summary(
    command_read_access: CommandReadAccess,
    institution_organization_id: CommandInstitutionOrganizationId,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    try:
        return await run_in_threadpool(
            _views(settings).summary,
            organization_id=str(institution_organization_id),
        )
    except GovernanceProjectionError as exc:
        raise _error(exc) from exc


@router.get("/capabilities")
async def capability_health(
    command_read_access: CommandReadAccess,
    institution_organization_id: CommandInstitutionOrganizationId,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    """Read-only capability/integration/federated-seat health projection."""
    try:
        return await run_in_threadpool(
            _views(settings).capability_health,
            organization_id=str(institution_organization_id),
        )
    except GovernanceProjectionError as exc:
        raise _error(exc) from exc
