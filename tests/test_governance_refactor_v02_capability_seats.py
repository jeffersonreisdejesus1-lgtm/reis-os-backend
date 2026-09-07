from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.governance_refactor.capability import (
    CapabilityDecision,
    IntegrationCapabilitySnapshot,
    IntegrationUseRequest,
    evaluate_integration_use,
    reconcile_receipt,
)
from app.governance_refactor.contracts import (
    AuxiliaryAgentEvidenceContract,
    CapabilityClass,
    ChatInstitutionalRoutingContract,
    IntegrationCapabilityRecord,
    RoutingState,
)

NOW = datetime(2026, 9, 7, 3, 30, tzinfo=UTC)


def seat_snapshot(**changes: object) -> IntegrationCapabilitySnapshot:
    values: dict[str, object] = {
        "connector": "grok-seat",
        "connected": True,
        "actions": frozenset({"source_read", "model_invoke"}),
        "readable_targets": frozenset({"repo:reis-os-backend", "model:grok"}),
        "writable_targets": frozenset(),
        "canonical_source_roles": frozenset({"CODE_TRUTH", "FEDERATED_ASSURANCE"}),
        "capability_version": "seat-cap-v02",
        "validated_at": NOW - timedelta(seconds=30),
        "max_age_seconds": 300,
        "capability_class": "FEDERATED_SEAT",
        "seat_ref": "GROK",
        "host_ref": "xAI",
    }
    values.update(changes)
    return IntegrationCapabilitySnapshot(**values)  # type: ignore[arg-type]


def request(**changes: object) -> IntegrationUseRequest:
    values: dict[str, object] = {
        "connector": "grok-seat",
        "action": "model_invoke",
        "target": "model:grok",
        "source_role": "FEDERATED_ASSURANCE",
        "authority_ref": "mission-authority:1",
        "capability_version": "seat-cap-v02",
        "model_invoke": True,
    }
    values.update(changes)
    return IntegrationUseRequest(**values)  # type: ignore[arg-type]


def test_host_or_seat_label_does_not_prove_live_model_invocation() -> None:
    decision = evaluate_integration_use(seat_snapshot(), request(), now=NOW)
    assert decision.decision is CapabilityDecision.HOLD
    assert "model_invocation_not_available" in decision.reasons
    assert "provider_adapter_not_validated" in decision.reasons
    assert "machine_receipt_not_supported" in decision.reasons


def test_source_access_and_model_invocation_are_independent_dimensions() -> None:
    source_only = replace(seat_snapshot(), source_access_validated=True)
    source_request = IntegrationUseRequest(
        connector="grok-seat",
        action="source_read",
        target="repo:reis-os-backend",
        source_role="CODE_TRUTH",
        authority_ref="mission-authority:1",
        capability_version="seat-cap-v02",
        source_access_required=True,
    )
    source_decision = evaluate_integration_use(source_only, source_request, now=NOW)
    assert source_decision.decision is CapabilityDecision.ALLOW_ATTEMPT

    model_decision = evaluate_integration_use(source_only, request(), now=NOW)
    assert model_decision.decision is CapabilityDecision.HOLD
    assert "source_access_not_validated" not in model_decision.reasons
    assert "provider_adapter_not_validated" in model_decision.reasons


def test_live_model_invocation_requires_validated_adapter_and_machine_receipt() -> None:
    live = replace(
        seat_snapshot(),
        model_invocation_available=True,
        provider_adapter_validated=True,
        machine_receipt_supported=True,
    )
    decision = evaluate_integration_use(live, request(), now=NOW)
    assert decision.decision is CapabilityDecision.ALLOW_ATTEMPT
    assert not decision.material_effect_performed
    assert not decision.grants_authority

    partial = reconcile_receipt(
        decision,
        effect_receipt_ref="effect:1",
        readback_ref=None,
        canonical_reconciliation_ref=None,
    )
    assert partial.decision is CapabilityDecision.HOLD

    reconciled = reconcile_receipt(
        decision,
        effect_receipt_ref="effect:1",
        readback_ref="readback:1",
        canonical_reconciliation_ref="canonical:1",
    )
    assert reconciled.material_effect_performed
    assert reconciled.canonical_state_reconciled
    assert not reconciled.grants_authority


def test_capability_still_cannot_promote_even_when_live_adapter_is_valid() -> None:
    live = replace(
        seat_snapshot(),
        model_invocation_available=True,
        provider_adapter_validated=True,
        machine_receipt_supported=True,
    )
    decision = evaluate_integration_use(live, request(promote=True), now=NOW)
    assert decision.decision is CapabilityDecision.HOLD
    assert "capability_cannot_promote" in decision.reasons


def test_integration_record_cannot_claim_live_invocation_from_label_only() -> None:
    with pytest.raises(ValueError, match="live_model_invocation_requires_host_adapter"):
        IntegrationCapabilityRecord(
            integration_id="seat:grok",
            provider="xAI",
            category="federated-seat",
            purpose="assurance",
            connection_status="VISIBLE",
            validation_status="PARTIAL",
            read_capabilities=("repo",),
            write_capabilities=(),
            supported_artifacts=("source",),
            authentication_boundary="seat-session",
            canonical_source_role=None,
            primary_ocs_users=("NOESIS",),
            authorized_use_cases=("assurance",),
            prohibited_use_cases=("promotion",),
            known_limitations=("no_host_adapter",),
            security_risks=(),
            data_risks=(),
            reversibility="REVERSIBLE",
            evidence_capability="SOURCE_READ",
            last_validated_at=NOW,
            capability_version="v02",
            source_links=(),
            provenance_refs=("receipt:grok",),
            capability_class=CapabilityClass.FEDERATED_SEAT,
            seat_ref="GROK",
            host_ref="xAI",
            model_invoke_capabilities=("grok",),
            live_model_invocation_status="AVAILABLE",
            host_adapter_available=False,
            machine_verifiable_receipt=False,
        )


def test_chat_native_execution_remains_unproven() -> None:
    with pytest.raises(ValueError, match="chat_native_execution_unproven"):
        ChatInstitutionalRoutingContract(
            route_id="route:1",
            addressed_ocs_id="NOESIS",
            mission_id="mission:1",
            resolved_instance_id="instance:1",
            generation=1,
            routing_state=RoutingState.ADDRESSABLE,
            route_receipt_ref="receipt:1",
            response_correlation_id="corr:1",
            chat_addressable=True,
            chat_native_execution=True,
            source_links=(),
            provenance_refs=("receipt:1",),
            contract_version="v02",
        )


def test_auxiliary_scope_cannot_escape_parent_authority() -> None:
    with pytest.raises(ValueError, match="auxiliary_authority_escapes_parent"):
        AuxiliaryAgentEvidenceContract(
            evidence_id="aux:1",
            parent_ocs_id="NOESIS",
            auxiliary_id="aux:noesis:1",
            mission_id="mission:1",
            requested_scope=("read", "promote"),
            parent_authority_scope=("read",),
            produced_evidence_refs=(),
            created_new_ocs_identity=False,
            source_links=(),
            provenance_refs=(),
            contract_version="v02",
        )
