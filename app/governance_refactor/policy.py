from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GovernanceGate(StrEnum):
    G0_EXECUTION = "G0_EXECUTION"
    G1_TECHNICAL_QUALITY = "G1_TECHNICAL_QUALITY"
    G2_INDEPENDENT_ASSURANCE = "G2_INDEPENDENT_ASSURANCE"
    G3_PROMOTION_READINESS = "G3_PROMOTION_READINESS"
    G4_FOUNDER_APPROVAL = "G4_FOUNDER_APPROVAL"


class PolicyState(StrEnum):
    OPEN = "OPEN"
    HOLD = "HOLD"
    SATISFIED = "SATISFIED"
    READY_FOR_EXTERNAL_AUTHORITY_CHECK = "READY_FOR_EXTERNAL_AUTHORITY_CHECK"


@dataclass(frozen=True, slots=True)
class GatePolicyInput:
    gate: GovernanceGate
    evidence_refs: tuple[str, ...] = ()
    technical_checks_passed: bool = False
    assurance_required: bool = False
    assurance_refs: tuple[str, ...] = ()
    open_blockers: tuple[str, ...] = ()
    required_domains: tuple[str, ...] = ()
    completed_domains: tuple[str, ...] = ()
    founder_decision_ref: str | None = None
    external_authority_verified: bool = False
    authority_readback_ref: str | None = None


@dataclass(frozen=True, slots=True)
class GatePolicyDecision:
    gate: GovernanceGate
    state: PolicyState
    reasons: tuple[str, ...]
    promotes: bool = False
    grants_authority: bool = False


def evaluate_gate(request: GatePolicyInput) -> GatePolicyDecision:
    """Evaluate governance gate prerequisites without granting promotion or authority."""
    reasons: list[str] = []

    if request.gate is GovernanceGate.G0_EXECUTION:
        if not request.evidence_refs:
            reasons.append("execution_evidence_required")
        return _decision(request.gate, reasons)

    if request.gate is GovernanceGate.G1_TECHNICAL_QUALITY:
        if not request.evidence_refs:
            reasons.append("technical_evidence_required")
        if not request.technical_checks_passed:
            reasons.append("technical_checks_not_passed")
        return _decision(request.gate, reasons)

    if request.gate is GovernanceGate.G2_INDEPENDENT_ASSURANCE:
        if not request.assurance_required:
            return GatePolicyDecision(
                gate=request.gate,
                state=PolicyState.SATISFIED,
                reasons=("assurance_not_required_by_policy",),
            )
        if not request.assurance_refs:
            reasons.append("independent_assurance_required")
        return _decision(request.gate, reasons)

    if request.gate is GovernanceGate.G3_PROMOTION_READINESS:
        if request.open_blockers:
            reasons.append("open_blockers_present")
        missing = set(request.required_domains) - set(request.completed_domains)
        if missing:
            reasons.append("required_quality_domains_incomplete")
        if request.assurance_required and not request.assurance_refs:
            reasons.append("required_assurance_missing")
        if not request.evidence_refs:
            reasons.append("promotion_evidence_bundle_required")
        return _decision(request.gate, reasons)

    if not request.founder_decision_ref:
        reasons.append("founder_decision_record_required")
    if not request.external_authority_verified:
        reasons.append("founder_authority_not_externally_verified")
    if not request.authority_readback_ref:
        reasons.append("founder_authority_readback_required")
    if reasons:
        return GatePolicyDecision(
            gate=request.gate,
            state=PolicyState.HOLD,
            reasons=tuple(reasons),
        )
    return GatePolicyDecision(
        gate=request.gate,
        state=PolicyState.READY_FOR_EXTERNAL_AUTHORITY_CHECK,
        reasons=("external_authority_prerequisites_present",),
    )


def _decision(gate: GovernanceGate, reasons: list[str]) -> GatePolicyDecision:
    return GatePolicyDecision(
        gate=gate,
        state=PolicyState.HOLD if reasons else PolicyState.SATISFIED,
        reasons=tuple(reasons),
    )
