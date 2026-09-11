import pytest

from orchestrator_effect_bridge import (
    OrchestratorEffectAuthorization,
    OrchestratorEffectBridge,
)

NOW = 2_000_000_000.0
MISSION = "REIS-AUTHORITY-GATEWAY-V1-IMPLEMENTATION-001"
RUN = "ORCH-RUN-AUTHORITY-GATEWAY-V1-001"
STAGE = "IMPLEMENTATION"
TARGET = "github:jeffersonreisdejesus1-lgtm/reis-os-backend"
CAP = "GITHUB_CREATE_OR_UPDATE_FILE"
APPROVAL = "FOUNDER-BOOTSTRAP-AUTHORITY-GATEWAY-V1-001"


def auth(**overrides):
    data = dict(
        authorization_id="AUTHZ:AUTHORITY-GATEWAY-V1-001",
        mission_id=MISSION,
        orchestrator_run_id=RUN,
        mission_stage=STAGE,
        actor_id="actor:noesis:authority-gateway-v1",
        canonical_identity="NOESIS",
        authority_ref="AUTH:NOESIS:AUTHORITY-GATEWAY-V1",
        mission_binding=MISSION,
        delegation_ref="DELEGATION:FOUNDER:NOESIS:AUTHORITY-GATEWAY-V1",
        target=TARGET,
        capability=CAP,
        payload_ref="ci/recursive-runtime/authority_gateway.py",
        founder_approval_ref=APPROVAL,
        generation=1,
        fencing_epoch=1,
        request_id="effect:authority-gateway-v1:001",
        evidence_parent="DEDALA-ARCH-ASSURANCE-AUTHORITY-GATEWAY-V1-001",
        issued_at_unix=NOW - 10,
        expires_at_unix=NOW + 600,
    )
    data.update(overrides)
    return OrchestratorEffectAuthorization(**data)


def bridge():
    return OrchestratorEffectBridge(
        expected_mission_id=MISSION,
        expected_run_id=RUN,
        expected_stage=STAGE,
        allowed_identity="NOESIS",
        allowed_target=TARGET,
        allowed_capability=CAP,
        founder_approval_ref=APPROVAL,
        clock=lambda: NOW,
    )


def test_exact_authority_proof_prepares_single_effect_controls():
    prepared = bridge().prepare(auth())
    assert prepared.request.target == TARGET
    assert prepared.request.capability == CAP
    assert prepared.request.authority_ref == "AUTH:NOESIS:AUTHORITY-GATEWAY-V1"
    assert prepared.lease.max_effects == 1
    assert prepared.lease.allowed_targets == frozenset({TARGET})
    assert prepared.policy.allowed_ocs_ids == frozenset({"NOESIS"})
    assert prepared.policy.allow_github_merge is False
    assert prepared.policy.zero_unauthorized_spend is True


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("mission_id", "OTHER", "MISSION_MISMATCH"),
        ("orchestrator_run_id", "OTHER", "ORCHESTRATOR_RUN_MISMATCH"),
        ("mission_stage", "PROMOTION", "MISSION_STAGE_MISMATCH"),
        ("canonical_identity", "SOFIA", "IDENTITY_MISMATCH"),
        ("target", "github:other/repo", "TARGET_MISMATCH"),
        ("capability", "GITHUB_MERGE_PR", "CAPABILITY_MISMATCH"),
        ("founder_approval_ref", "", "FOUNDER_APPROVAL_MISMATCH"),
        ("expires_at_unix", NOW, "AUTHORITY_EXPIRED"),
        ("estimated_incremental_cost_usd", 0.01, "ZERO_SPEND_POLICY_VIOLATION"),
        ("requires_paid_upgrade", True, "PAID_UPGRADE_FORBIDDEN"),
    ],
)
def test_fail_closed_on_scope_or_cost_divergence(field, value, error):
    with pytest.raises(RuntimeError, match=error):
        bridge().prepare(auth(**{field: value}))
