from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.command.api.dependencies import (
    CommandInstitutionOrganizationId,
    CommandReadAccess,
)
from app.command.cupuwa_module import cupuwa_inspired_module_contract
from app.command.ocs_inference import (
    InferencePlanRequest,
    RequestScope,
    plan_inference,
)
from app.command.product_views import CommandProductSources, CommandProductViews
from app.shared.config.settings import Settings, get_settings

router = APIRouter(prefix="/v1/command", tags=["command-b10"])


class InferencePlanBody(BaseModel):
    prompt: str = Field(min_length=1)
    request_scope: RequestScope = RequestScope.AUTO
    requested_ocs: str | None = None
    suggested_ocs: str | None = None
    tool_required: bool = False
    material_effect_requested: bool = False
    authority_ref: str | None = None
    routing_hops: int = Field(default=0, ge=0, le=2)
    prior_ocs: list[str] = Field(default_factory=list)


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
    """B10 aggregate Control Plane projection over existing sources."""
    return await run_in_threadpool(
        _views(settings).cockpit,
        organization_id=str(institution_organization_id),
    )


@router.get("/modules/cupuwa-inspired")
async def get_cupuwa_inspired_module(
    command_read_access: CommandReadAccess,
) -> dict[str, Any]:
    """Return the OURO/PRATA product contract; this endpoint is read-only."""
    return cupuwa_inspired_module_contract()


@router.post("/ocs-inference/plan")
async def create_ocs_inference_plan(
    body: InferencePlanBody,
    command_read_access: CommandReadAccess,
    institution_organization_id: CommandInstitutionOrganizationId,
) -> dict[str, Any]:
    """Plan an OCS/general-AI/tool/authority response without executing it.

    POST is used because the prompt is request data, but the operation has no
    canonical material effect. It cannot grant authority, invoke a provider,
    mutate mission state, promote, or write through the Command surface.
    """
    request = InferencePlanRequest(
        prompt=body.prompt,
        request_scope=body.request_scope,
        requested_ocs=body.requested_ocs,
        suggested_ocs=body.suggested_ocs,
        tool_required=body.tool_required,
        material_effect_requested=body.material_effect_requested,
        authority_ref=body.authority_ref,
        routing_hops=body.routing_hops,
        prior_ocs=tuple(body.prior_ocs),
    )
    result = plan_inference(request).as_dict()
    result["organization_id"] = str(institution_organization_id)
    result["material_effect"] = False
    result["provider_invocation"] = "NOT_EXECUTED"
    return result
