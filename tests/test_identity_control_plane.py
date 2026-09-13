from __future__ import annotations

from dataclasses import replace
from time import time

import pytest

from app.identity_control_plane import (
    AuthoritativeIdentityReferenceMonitor,
    HandoffIdentityReceipt,
    IdentityControlPlaneError,
    ModelActionProposal,
)
from app.ocs_instances.contracts import BindingMaturity, InstanceBinding, InstanceStatus
from app.universal_kernel.governance import AuthorityLease, AuthorityLeaseManager
from app.universal_kernel.identity import IdentityAuditLog, IdentityKernelGuard


class BindingReader:
    def __init__(self, binding: InstanceBinding) -> None:
        self.binding = binding

    def get(self, binding_id: str) -> InstanceBinding:
        if binding_id != self.binding.binding_id:
            from app.ocs_instances.contracts import InstanceBindingError

            raise InstanceBindingError("instance_binding_not_found")
        return self.binding


def build_monitor(*, ocs: str = "ÁGORA", generation: int = 3):
    now = time()
    guard = IdentityKernelGuard(audit_log=IdentityAuditLog())
    active = guard.bind_active_identity(
        run_id="run:material-reality-audit",
        ocs_id=ocs,
        host="work-runtime",
        session_context="context:external-authoritative",
    )
    identity_hash = IdentityAuditLog.binding_hash(active)
    leases = AuthorityLeaseManager()
    lease = AuthorityLease(
        lease_id="lease:identity-test",
        ocs=ocs,
        capability="independent_technical_verification",
        expires_at=now + 3600,
        actor=ocs,
        issued_at=now - 1,
        not_before=now - 1,
        scope=("handoff", "audit"),
        tenant="REIS OS",
        context_ref="context:external-authoritative",
        authority_ref="authority:material-reality-audit",
        policy_snapshot="policy:identity-control-plane",
        action_binding="handoff",
        object_ref_or_selector="REIS-OS-MATERIAL-REALITY-AUDIT-001",
        trace_ref="trace:identity-test",
        max_uses=10,
    )
    leases.issue(lease)
    binding = InstanceBinding(
        binding_id="binding:agora:material-reality",
        mission_id="MATERIAL_REALITY_AUDIT",
        run_id="run:material-reality-audit",
        organization_id="REIS OS",
        ocs_id=ocs,
        profile_version=active.profile_version,
        profile_hash="profile-hash",
        identity_binding_hash=identity_hash,
        request_hash="request-hash",
        maturity=BindingMaturity.OPERATIONALLY_BOUND_L1,
        host="work-runtime",
        capability="independent_technical_verification",
        lease_id=lease.lease_id,
        authority_ref=lease.authority_ref,
        scope=("handoff", "audit"),
        state_namespace=active.state_namespace,
        memory_namespace=active.memory_namespace,
        generation=generation,
        platform_instance_id="instance:agora:3",
        challenge_hash="challenge",
        bootstrap_hash="bootstrap",
        status=InstanceStatus.ACTIVE,
        version=4,
        predecessor_binding_id="binding:agora:2",
        checkpoint_version=2,
        checkpoint_hash="checkpoint",
        hazel_event_hash="event:previous",
        idempotency_key="idem:binding",
        correlation_id="corr:1",
        causation_id="cause:1",
        created_at=now - 100,
        updated_at=now,
    )
    reader = BindingReader(binding)
    monitor = AuthoritativeIdentityReferenceMonitor(
        bindings=reader,
        identity_guard=guard,
        leases=leases,
        receipt_key=b"test-key-outside-model-context",
    )
    return monitor, reader, guard, leases


def proposal(**overrides):
    values = dict(
        requested_target="NÓESIS",
        object_id="REIS-OS-MATERIAL-REALITY-AUDIT-001",
        action_type="handoff",
        payload={"result": "candidate"},
        model_source_ocs=None,
        model_source_instance_id=None,
        model_generation=None,
    )
    values.update(overrides)
    return ModelActionProposal(**values)


def stamp(monitor, p):
    return monitor.stamp(
        binding_id="binding:agora:material-reality",
        platform_instance_id="instance:agora:3",
        generation=3,
        mission_id="MATERIAL_REALITY_AUDIT",
        proposal=p,
    )


def test_original_incident_wrong_source_is_rejected_without_adoption():
    monitor, *_ = build_monitor()
    with pytest.raises(IdentityControlPlaneError, match="model_source_ocs_conflict"):
        stamp(monitor, proposal(model_source_ocs="NÓESIS"))


def test_source_identity_is_system_stamped_from_authoritative_binding():
    monitor, *_ = build_monitor()
    envelope = stamp(monitor, proposal())
    assert envelope.source_ocs == "ÁGORA"
    assert envelope.source_instance_id == "instance:agora:3"
    assert envelope.generation == 3
    assert envelope.mission_id == "MATERIAL_REALITY_AUDIT"
    assert envelope.authority_ref == "authority:material-reality-audit"


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"platform_instance_id": "instance:forged"}, "platform_instance_fenced"),
        ({"generation": 2}, "instance_generation_fenced"),
        ({"mission_id": "WRONG"}, "mission_identity_mismatch"),
    ],
)
def test_wrong_instance_generation_or_mission_fails_closed(kwargs, reason):
    monitor, *_ = build_monitor()
    call = dict(
        binding_id="binding:agora:material-reality",
        platform_instance_id="instance:agora:3",
        generation=3,
        mission_id="MATERIAL_REALITY_AUDIT",
        proposal=proposal(),
    )
    call.update(kwargs)
    with pytest.raises(IdentityControlPlaneError, match=reason):
        monitor.stamp(**call)


def test_hold_binding_cannot_create_system_stamped_effect():
    monitor, reader, *_ = build_monitor()
    reader.binding = replace(reader.binding, status=InstanceStatus.HOLD)
    with pytest.raises(IdentityControlPlaneError, match="identity_binding_not_active"):
        stamp(monitor, proposal())


def test_revoked_authority_lease_is_denied_under_valid_identity():
    monitor, _, _, leases = build_monitor()
    leases.revoke("lease:identity-test")
    with pytest.raises(IdentityControlPlaneError, match="lease_revoked"):
        stamp(monitor, proposal())


def test_model_cannot_override_instance_or_generation():
    monitor, *_ = build_monitor()
    with pytest.raises(IdentityControlPlaneError, match="model_source_instance_conflict"):
        stamp(monitor, proposal(model_source_instance_id="instance:noesis"))
    with pytest.raises(IdentityControlPlaneError, match="model_generation_conflict"):
        stamp(monitor, proposal(model_generation=99))


def test_handoff_receipt_is_authenticated_and_target_bound():
    monitor, *_ = build_monitor()
    envelope = stamp(monitor, proposal())
    receipt = monitor.issue_handoff_receipt(
        handoff_id="handoff:001",
        envelope=envelope,
        authorized_next_scope=("adopt_audit_result",),
        predecessor_event_hash="event:previous",
    )
    monitor.verify_handoff_receipt(receipt, expected_target_ocs="NÓESIS")

    tampered = replace(receipt, source_ocs_id="NÓESIS")
    with pytest.raises(IdentityControlPlaneError, match="handoff_integrity_proof_invalid"):
        monitor.verify_handoff_receipt(tampered, expected_target_ocs="NÓESIS")

    with pytest.raises(IdentityControlPlaneError, match="handoff_receiver_target_mismatch"):
        monitor.verify_handoff_receipt(receipt, expected_target_ocs="SOFIA")


def test_forged_binding_hash_is_denied():
    monitor, reader, *_ = build_monitor()
    reader.binding = replace(reader.binding, identity_binding_hash="forged")
    with pytest.raises(IdentityControlPlaneError, match="identity_binding_hash_mismatch"):
        stamp(monitor, proposal())
