from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CapabilityDecision(StrEnum):
    ALLOW_ATTEMPT = "ALLOW_ATTEMPT"
    HOLD = "HOLD"


@dataclass(frozen=True, slots=True)
class IntegrationCapabilitySnapshot:
    connector: str
    connected: bool
    actions: frozenset[str]
    readable_targets: frozenset[str]
    writable_targets: frozenset[str]
    canonical_source_roles: frozenset[str]


@dataclass(frozen=True, slots=True)
class IntegrationUseRequest:
    connector: str
    action: str
    target: str
    source_role: str
    authority_ref: str | None
    write: bool = False
    promote: bool = False


@dataclass(frozen=True, slots=True)
class IntegrationUseDecision:
    decision: CapabilityDecision
    reasons: tuple[str, ...]
    material_effect_performed: bool = False
    canonical_state_reconciled: bool = False
    grants_authority: bool = False


def evaluate_integration_use(
    snapshot: IntegrationCapabilitySnapshot,
    request: IntegrationUseRequest,
) -> IntegrationUseDecision:
    """Validate capability prerequisites before any external material effect."""
    reasons: list[str] = []
    if request.connector != snapshot.connector:
        reasons.append("connector_mismatch")
    if not snapshot.connected:
        reasons.append("connector_not_connected")
    if request.action not in snapshot.actions:
        reasons.append("action_not_available")
    if not request.authority_ref:
        reasons.append("authority_ref_required")
    if request.write:
        if request.target not in snapshot.writable_targets:
            reasons.append("target_not_writable")
    elif request.target not in snapshot.readable_targets:
        reasons.append("target_not_readable")
    if request.source_role not in snapshot.canonical_source_roles:
        reasons.append("source_role_not_confirmed")
    if request.promote:
        reasons.append("capability_cannot_promote")
    return IntegrationUseDecision(
        decision=(
            CapabilityDecision.HOLD
            if reasons
            else CapabilityDecision.ALLOW_ATTEMPT
        ),
        reasons=tuple(reasons),
    )


def reconcile_receipt(
    decision: IntegrationUseDecision,
    *,
    effect_receipt_ref: str | None,
    readback_ref: str | None,
    canonical_reconciliation_ref: str | None,
) -> IntegrationUseDecision:
    """Represent post-effect proof without converting capability into authority."""
    if decision.decision is not CapabilityDecision.ALLOW_ATTEMPT:
        return decision
    reasons: list[str] = []
    if not effect_receipt_ref:
        reasons.append("effect_receipt_required")
    if not readback_ref:
        reasons.append("readback_required")
    if not canonical_reconciliation_ref:
        reasons.append("canonical_reconciliation_required")
    if reasons:
        return IntegrationUseDecision(
            decision=CapabilityDecision.HOLD,
            reasons=tuple(reasons),
            material_effect_performed=bool(effect_receipt_ref),
        )
    return IntegrationUseDecision(
        decision=CapabilityDecision.ALLOW_ATTEMPT,
        reasons=("receipt_readback_and_reconciliation_present",),
        material_effect_performed=True,
        canonical_state_reconciled=True,
    )
