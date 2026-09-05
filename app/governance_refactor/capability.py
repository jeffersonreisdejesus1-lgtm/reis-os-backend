from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
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
    capability_version: str
    validated_at: datetime
    max_age_seconds: int | None = None
    expires_at: datetime | None = None
    drift_detected: bool = False
    drifted_actions: frozenset[str] = field(default_factory=frozenset)
    drifted_targets: frozenset[str] = field(default_factory=frozenset)
    drifted_source_roles: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class IntegrationUseRequest:
    connector: str
    action: str
    target: str
    source_role: str
    authority_ref: str | None
    capability_version: str | None = None
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
    *,
    now: datetime | None = None,
) -> IntegrationUseDecision:
    """Validate current capability prerequisites before any external material effect."""
    evaluation_time = now or datetime.now(UTC)
    reasons: list[str] = []

    if evaluation_time.tzinfo is None:
        reasons.append("evaluation_time_not_timezone_aware")
    if snapshot.validated_at.tzinfo is None:
        reasons.append("validated_at_not_timezone_aware")
    elif evaluation_time.tzinfo is not None:
        if snapshot.validated_at > evaluation_time:
            reasons.append("validated_at_in_future")
        if snapshot.max_age_seconds is None and snapshot.expires_at is None:
            reasons.append("capability_expiry_policy_required")
        if snapshot.max_age_seconds is not None:
            if snapshot.max_age_seconds <= 0:
                reasons.append("max_age_seconds_invalid")
            elif evaluation_time - snapshot.validated_at > timedelta(
                seconds=snapshot.max_age_seconds
            ):
                reasons.append("capability_snapshot_stale")

    if snapshot.expires_at is not None:
        if snapshot.expires_at.tzinfo is None:
            reasons.append("expires_at_not_timezone_aware")
        elif evaluation_time.tzinfo is not None and snapshot.expires_at <= evaluation_time:
            reasons.append("capability_snapshot_expired")

    if not snapshot.capability_version.strip():
        reasons.append("capability_version_required")
    if not request.capability_version:
        reasons.append("capability_version_expectation_required")
    elif request.capability_version != snapshot.capability_version:
        reasons.append("capability_version_mismatch")

    if snapshot.drift_detected:
        reasons.append("capability_drift_detected")
    if request.action in snapshot.drifted_actions:
        reasons.append("action_drift_detected")
    if request.target in snapshot.drifted_targets:
        reasons.append("target_drift_detected")
    if request.source_role in snapshot.drifted_source_roles:
        reasons.append("source_role_drift_detected")

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
