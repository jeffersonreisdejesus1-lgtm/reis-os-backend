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
from app.governance_refactor.metrics import (
    MetricsValidationError,
    MissionTimingInput,
    instrument_mission,
)
from app.governance_refactor.policy import (
    GatePolicyInput,
    GovernanceGate,
    PolicyState,
    evaluate_gate,
)

NOW = datetime(2026, 9, 5, 22, 45, tzinfo=UTC)


def test_r5_gates_never_promote_or_grant_authority() -> None:
    for gate in GovernanceGate:
        decision = evaluate_gate(
            GatePolicyInput(
                gate=gate,
                evidence_refs=("evidence:1",),
                technical_checks_passed=True,
                assurance_required=False,
                required_domains=("backend",),
                completed_domains=("backend",),
                founder_decision_ref="founder-decision:1",
                external_authority_verified=True,
                authority_readback_ref="authority-readback:1",
            )
        )
        assert not decision.promotes
        assert not decision.grants_authority


def test_r5_quality_and_founder_gates_fail_closed() -> None:
    quality = evaluate_gate(GatePolicyInput(gate=GovernanceGate.G1_TECHNICAL_QUALITY))
    assert quality.state is PolicyState.HOLD
    assert "technical_evidence_required" in quality.reasons

    founder = evaluate_gate(
        GatePolicyInput(
            gate=GovernanceGate.G4_FOUNDER_APPROVAL,
            founder_decision_ref="record-only",
        )
    )
    assert founder.state is PolicyState.HOLD
    assert "founder_authority_not_externally_verified" in founder.reasons


def test_r5_assurance_is_conditional_and_policy_bound() -> None:
    not_required = evaluate_gate(
        GatePolicyInput(
            gate=GovernanceGate.G2_INDEPENDENT_ASSURANCE,
            assurance_required=False,
        )
    )
    assert not_required.state is PolicyState.SATISFIED
    required = evaluate_gate(
        GatePolicyInput(
            gate=GovernanceGate.G2_INDEPENDENT_ASSURANCE,
            assurance_required=True,
        )
    )
    assert required.state is PolicyState.HOLD


def _capability() -> IntegrationCapabilitySnapshot:
    return IntegrationCapabilitySnapshot(
        connector="github",
        connected=True,
        actions=frozenset({"read", "write"}),
        readable_targets=frozenset({"repo:a"}),
        writable_targets=frozenset({"repo:a"}),
        canonical_source_roles=frozenset({"CODE_TRUTH"}),
        capability_version="github-cap-v3",
        validated_at=NOW - timedelta(seconds=30),
        max_age_seconds=300,
    )


def _request(**changes: object) -> IntegrationUseRequest:
    values: dict[str, object] = {
        "connector": "github",
        "action": "write",
        "target": "repo:a",
        "source_role": "CODE_TRUTH",
        "authority_ref": "mission-authority:1",
        "capability_version": "github-cap-v3",
        "write": True,
    }
    values.update(changes)
    return IntegrationUseRequest(**values)  # type: ignore[arg-type]


def test_r6_capability_prerequisites() -> None:
    allowed = evaluate_integration_use(_capability(), _request(), now=NOW)
    assert allowed.decision is CapabilityDecision.ALLOW_ATTEMPT
    assert not allowed.material_effect_performed
    assert not allowed.grants_authority

    denied = evaluate_integration_use(
        _capability(),
        _request(authority_ref=None),
        now=NOW,
    )
    assert denied.decision is CapabilityDecision.HOLD
    assert "authority_ref_required" in denied.reasons


def test_r6_freshness_and_expiry_fail_closed() -> None:
    future = evaluate_integration_use(
        replace(_capability(), validated_at=NOW + timedelta(seconds=1)),
        _request(),
        now=NOW,
    )
    assert future.decision is CapabilityDecision.HOLD
    assert "validated_at_in_future" in future.reasons

    stale = evaluate_integration_use(
        replace(_capability(), validated_at=NOW - timedelta(seconds=301)),
        _request(),
        now=NOW,
    )
    assert stale.decision is CapabilityDecision.HOLD
    assert "capability_snapshot_stale" in stale.reasons

    expired = evaluate_integration_use(
        replace(_capability(), max_age_seconds=None, expires_at=NOW),
        _request(),
        now=NOW,
    )
    assert expired.decision is CapabilityDecision.HOLD
    assert "capability_snapshot_expired" in expired.reasons

    missing_policy = evaluate_integration_use(
        replace(_capability(), max_age_seconds=None),
        _request(),
        now=NOW,
    )
    assert missing_policy.decision is CapabilityDecision.HOLD
    assert "capability_expiry_policy_required" in missing_policy.reasons


def test_r6_timezone_version_and_drift_fail_closed() -> None:
    naive = evaluate_integration_use(
        replace(_capability(), validated_at=NOW.replace(tzinfo=None)),
        _request(),
        now=NOW,
    )
    assert naive.decision is CapabilityDecision.HOLD
    assert "validated_at_not_timezone_aware" in naive.reasons

    mismatch = evaluate_integration_use(
        _capability(),
        _request(capability_version="github-cap-v2"),
        now=NOW,
    )
    assert mismatch.decision is CapabilityDecision.HOLD
    assert "capability_version_mismatch" in mismatch.reasons

    drift = evaluate_integration_use(
        replace(_capability(), drift_detected=True),
        _request(),
        now=NOW,
    )
    assert drift.decision is CapabilityDecision.HOLD
    assert "capability_drift_detected" in drift.reasons

    action_drift = evaluate_integration_use(
        replace(_capability(), drifted_actions=frozenset({"write"})),
        _request(),
        now=NOW,
    )
    assert action_drift.decision is CapabilityDecision.HOLD
    assert "action_drift_detected" in action_drift.reasons

    target_drift = evaluate_integration_use(
        replace(_capability(), drifted_targets=frozenset({"repo:a"})),
        _request(),
        now=NOW,
    )
    assert target_drift.decision is CapabilityDecision.HOLD
    assert "target_drift_detected" in target_drift.reasons

    role_drift = evaluate_integration_use(
        replace(
            _capability(),
            drifted_source_roles=frozenset({"CODE_TRUTH"}),
        ),
        _request(),
        now=NOW,
    )
    assert role_drift.decision is CapabilityDecision.HOLD
    assert "source_role_drift_detected" in role_drift.reasons


def test_r6_write_and_reconciliation_boundaries() -> None:
    promotion = evaluate_integration_use(
        _capability(),
        _request(promote=True),
        now=NOW,
    )
    assert promotion.decision is CapabilityDecision.HOLD
    assert "capability_cannot_promote" in promotion.reasons

    allowed = evaluate_integration_use(_capability(), _request(), now=NOW)
    partial = reconcile_receipt(
        allowed,
        effect_receipt_ref="receipt:1",
        readback_ref=None,
        canonical_reconciliation_ref=None,
    )
    assert partial.decision is CapabilityDecision.HOLD
    final = reconcile_receipt(
        allowed,
        effect_receipt_ref="receipt:1",
        readback_ref="readback:1",
        canonical_reconciliation_ref="reconcile:1",
    )
    assert final.material_effect_performed
    assert final.canonical_state_reconciled
    assert not final.grants_authority


def _timing(**changes: object) -> MissionTimingInput:
    values: dict[str, object] = {
        "record_id": "metrics-r7-1",
        "mission_id": "mission-r7",
        "ocs_id": "SOFIA",
        "started_at": NOW - timedelta(hours=2),
        "completed_at": NOW,
        "active_execution_seconds": 5400,
        "waiting_seconds": 1200,
        "founder_wait_seconds": 300,
        "external_wait_seconds": 300,
        "retries": 1,
        "failures": 0,
        "refactors": 1,
        "founder_interventions": 0,
        "autonomous_completion": True,
        "source_refs": ("clock:1",),
        "provenance_refs": ("ci:1",),
        "observed_at": NOW,
    }
    values.update(changes)
    return MissionTimingInput(**values)  # type: ignore[arg-type]


def test_r7_uses_actual_timestamps_and_founder_timezone_without_verdict() -> None:
    record, snapshot = instrument_mission(_timing())
    assert snapshot.elapsed_seconds == 7200
    assert snapshot.elapsed_minutes == 120.0
    assert snapshot.elapsed_hours == 2.0
    assert snapshot.throughput_per_hour == 0.5
    assert snapshot.founder_local_started_at.tzinfo is not None
    assert record.measurement_method == "actual_clock_timestamps"
    assert not hasattr(snapshot, "verdict")
    assert not hasattr(snapshot, "authority")


def test_r7_rejects_invalid_time_and_negative_measurements() -> None:
    with pytest.raises(MetricsValidationError, match="completed_before_started"):
        instrument_mission(_timing(completed_at=NOW - timedelta(hours=3)))
    with pytest.raises(MetricsValidationError, match="negative_counter"):
        instrument_mission(_timing(retries=-1))
    with pytest.raises(MetricsValidationError, match="negative_duration"):
        instrument_mission(_timing(waiting_seconds=-1))
