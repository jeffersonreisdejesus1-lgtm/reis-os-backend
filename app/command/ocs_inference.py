from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from app.profile_bindings.profiles import PROFILES


class ResponseMode(StrEnum):
    GENERAL_AI = "GENERAL_AI"
    OCS_SPECIALIST = "OCS_SPECIALIST"
    ROUTED_OCS = "ROUTED_OCS"
    TOOL_ASSISTED = "TOOL_ASSISTED"
    AUTHORITY_GATED = "AUTHORITY_GATED"
    HOLD = "HOLD"


class RequestScope(StrEnum):
    AUTO = "AUTO"
    GENERAL = "GENERAL"
    SPECIALIST = "SPECIALIST"


@dataclass(frozen=True, slots=True)
class InferencePlanRequest:
    prompt: str
    request_scope: RequestScope = RequestScope.AUTO
    requested_ocs: str | None = None
    suggested_ocs: str | None = None
    tool_required: bool = False
    material_effect_requested: bool = False
    authority_ref: str | None = None
    routing_hops: int = 0
    prior_ocs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class InferencePlan:
    mode: ResponseMode
    ocs_id: str | None
    may_answer: bool
    may_recommend: bool
    may_prepare_action: bool
    may_execute_material_effect: bool
    tool_capability_required: bool
    authority_gate_required: bool
    canonical_state_write_allowed: bool
    max_routing_hops: int
    routing_hops: int
    reasons: tuple[str, ...]
    epistemic_boundary: dict[str, bool]

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["mode"] = self.mode.value
        return payload


MAX_ROUTING_HOPS = 2


def _normalize_ocs(value: str | None) -> str | None:
    if value is None:
        return None
    key = value.strip().upper()
    return key or None


def plan_inference(request: InferencePlanRequest) -> InferencePlan:
    reasons: list[str] = []
    requested_ocs = _normalize_ocs(request.requested_ocs)
    suggested_ocs = _normalize_ocs(request.suggested_ocs)

    if not request.prompt.strip():
        return _hold("empty_prompt", request)

    for label, value in (("requested", requested_ocs), ("suggested", suggested_ocs)):
        if value is not None and value not in PROFILES:
            return _hold(f"{label}_ocs_unknown", request)

    if request.routing_hops < 0 or request.routing_hops > MAX_ROUTING_HOPS:
        return _hold("routing_hop_limit_exceeded", request)

    prior = tuple(_normalize_ocs(item) or "" for item in request.prior_ocs)
    if requested_ocs is not None and requested_ocs in prior:
        return _hold("same_request_same_ocs_reentry_prohibited", request)

    if request.material_effect_requested:
        reasons.append("material_effect_requires_authority_gate")
        if request.authority_ref is None:
            reasons.append("authority_ref_missing")
        return _plan(
            mode=ResponseMode.AUTHORITY_GATED,
            ocs_id=requested_ocs or suggested_ocs,
            request=request,
            reasons=reasons,
            may_answer=True,
            may_recommend=True,
            may_prepare_action=True,
            tool_required=request.tool_required,
            authority_required=True,
        )

    if request.tool_required:
        reasons.append("tool_or_source_capability_required")
        return _plan(
            mode=ResponseMode.TOOL_ASSISTED,
            ocs_id=requested_ocs or suggested_ocs,
            request=request,
            reasons=reasons,
            may_answer=True,
            may_recommend=True,
            may_prepare_action=False,
            tool_required=True,
            authority_required=False,
        )

    if request.request_scope is RequestScope.GENERAL:
        reasons.append("explicit_general_assistance")
        return _plan(
            mode=ResponseMode.GENERAL_AI,
            ocs_id=None,
            request=request,
            reasons=reasons,
            may_answer=True,
            may_recommend=True,
            may_prepare_action=False,
            tool_required=False,
            authority_required=False,
        )

    if request.request_scope is RequestScope.SPECIALIST:
        target = requested_ocs or suggested_ocs
        if target is None:
            return _hold("specialist_scope_without_ocs", request)
        reasons.append("explicit_specialist_scope")
        return _plan(
            mode=ResponseMode.OCS_SPECIALIST,
            ocs_id=target,
            request=request,
            reasons=reasons,
            may_answer=True,
            may_recommend=True,
            may_prepare_action=False,
            tool_required=False,
            authority_required=False,
        )

    if requested_ocs is not None:
        reasons.append("requested_ocs_binding")
        return _plan(
            mode=ResponseMode.OCS_SPECIALIST,
            ocs_id=requested_ocs,
            request=request,
            reasons=reasons,
            may_answer=True,
            may_recommend=True,
            may_prepare_action=False,
            tool_required=False,
            authority_required=False,
        )

    if suggested_ocs is not None:
        if request.routing_hops >= MAX_ROUTING_HOPS:
            return _hold("routing_hop_limit_exceeded", request)
        if suggested_ocs in prior:
            return _hold("same_request_same_ocs_reentry_prohibited", request)
        reasons.append("better_ocs_available")
        return _plan(
            mode=ResponseMode.ROUTED_OCS,
            ocs_id=suggested_ocs,
            request=request,
            reasons=reasons,
            may_answer=False,
            may_recommend=False,
            may_prepare_action=False,
            tool_required=False,
            authority_required=False,
            routing_hops=request.routing_hops + 1,
        )

    reasons.append("general_fallback")
    return _plan(
        mode=ResponseMode.GENERAL_AI,
        ocs_id=None,
        request=request,
        reasons=reasons,
        may_answer=True,
        may_recommend=True,
        may_prepare_action=False,
        tool_required=False,
        authority_required=False,
    )


def _plan(
    *,
    mode: ResponseMode,
    ocs_id: str | None,
    request: InferencePlanRequest,
    reasons: list[str],
    may_answer: bool,
    may_recommend: bool,
    may_prepare_action: bool,
    tool_required: bool,
    authority_required: bool,
    routing_hops: int | None = None,
) -> InferencePlan:
    return InferencePlan(
        mode=mode,
        ocs_id=ocs_id,
        may_answer=may_answer,
        may_recommend=may_recommend,
        may_prepare_action=may_prepare_action,
        may_execute_material_effect=False,
        tool_capability_required=tool_required,
        authority_gate_required=authority_required,
        canonical_state_write_allowed=False,
        max_routing_hops=MAX_ROUTING_HOPS,
        routing_hops=request.routing_hops if routing_hops is None else routing_hops,
        reasons=tuple(reasons),
        epistemic_boundary={
            "model_is_ocs": False,
            "inference_is_authority": False,
            "inference_is_command": False,
            "requested_is_executed": False,
            "executed_is_verified": False,
            "verified_is_assured": False,
        },
    )


def _hold(reason: str, request: InferencePlanRequest) -> InferencePlan:
    return _plan(
        mode=ResponseMode.HOLD,
        ocs_id=None,
        request=request,
        reasons=[reason],
        may_answer=False,
        may_recommend=False,
        may_prepare_action=False,
        tool_required=request.tool_required,
        authority_required=request.material_effect_requested,
    )
