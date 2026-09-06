from __future__ import annotations

import json
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from time import time
from typing import Any

from app.ocs_instances.contracts import (
    BootstrapAck,
    InstanceStatus,
    PrepareInstanceRequest,
)
from app.ocs_instances.lease_store import AuthenticatedLeaseSnapshotStore
from app.ocs_instances.recovery import OCSInstanceRecovery
from app.ocs_instances.service import OCSInstanceBinder
from app.ocs_instances.store import InstanceBindingStore
from app.ocs_instances.work_bridge import WorkInstanceBridge, WorkSpawnReceipt
from app.profile_bindings.profiles import PROFILES
from app.universal_kernel.governance import AuthorityLease, AuthorityLeaseManager
from app.universal_kernel.hazel_continuity import HazelBoundContinuity
from app.universal_kernel.identity import IdentityAuditLog, IdentityKernelGuard


@dataclass(frozen=True, slots=True)
class IB7FullStateComparison:
    continuity_invariants_match: bool
    generation_transition_valid: bool
    business_state_match: bool
    business_state_hash_match: bool
    lineage_valid: bool
    authority_context_valid: bool
    namespace_continuity_valid: bool
    excluded_fields_with_reason: tuple[str, ...]

    @property
    def overall_equivalent(self) -> bool:
        return all(
            (
                self.continuity_invariants_match,
                self.generation_transition_valid,
                self.business_state_match,
                self.business_state_hash_match,
                self.lineage_valid,
                self.authority_context_valid,
                self.namespace_continuity_valid,
            )
        )


class FakeHazelTransport:
    def __init__(self) -> None:
        self.latest: dict[tuple[str, str, str], dict[str, Any]] = {}

    @staticmethod
    def _hash(value: dict[str, Any]) -> str:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        return sha256(encoded).hexdigest()

    def persist(self, envelope: dict[str, Any]) -> dict[str, Any]:
        key = (
            str(envelope["run_id"]),
            str(envelope["ocs_id"]),
            str(envelope["state_namespace"]),
        )
        previous = self.latest.get(key)
        if previous is None:
            assert envelope["state_version"] == 1
            assert envelope["predecessor_hash"] is None
        else:
            assert envelope["state_version"] == previous["state_version"] + 1
            assert envelope["predecessor_hash"] == previous["event_hash"]
        payload = dict(envelope["payload"])
        payload_hash = self._hash(payload)
        event_hash = self._hash(
            {
                key: value
                for key, value in envelope.items()
                if key != "payload"
            }
            | {"payload_hash": payload_hash}
        )
        receipt = {
            **envelope,
            "accepted": True,
            "payload_hash": payload_hash,
            "event_hash": event_hash,
        }
        self.latest[key] = receipt
        return receipt

    def recover(self, request: dict[str, Any]) -> dict[str, Any]:
        key = (
            str(request["run_id"]),
            str(request["ocs_id"]),
            str(request["state_namespace"]),
        )
        return dict(self.latest[key])


def _hash(value: dict[str, Any]) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return sha256(encoded).hexdigest()


def _request(*, lease_id: str, idempotency_key: str) -> PrepareInstanceRequest:
    return PrepareInstanceRequest(
        mission_id="mission:ib7:one-ocs",
        organization_id="org:reis-os",
        ocs_id="SOFIA",
        capability="software_implementation_via_valid_envelope_lease_effector",
        lease_id=lease_id,
        host="ChatGPT Work",
        scope=("repo:reis-os-backend",),
        idempotency_key=idempotency_key,
        correlation_id=f"corr:{idempotency_key}",
        actor="NÓESIS",
        context_ref="mission:ib7:one-ocs",
        policy_snapshot="policy:ib7",
        trace_ref="trace:ib7",
    )


def _leases() -> AuthorityLeaseManager:
    leases = AuthorityLeaseManager()
    profile = PROFILES["SOFIA"]
    now = time()
    for lease_id, action_binding in (
        ("lease:ib7:prepare", "ocs_instance_binding"),
        ("lease:ib7:checkpoint", "ocs_instance_checkpoint"),
        ("lease:ib7:replace", "ocs_instance_binding"),
    ):
        leases.issue(
            AuthorityLease(
                lease_id=lease_id,
                ocs="SOFIA",
                capability="software_implementation_via_valid_envelope_lease_effector",
                expires_at=now + 3600,
                actor="NÓESIS",
                issued_at=now,
                not_before=now,
                scope=("repo:reis-os-backend",),
                tenant="org:reis-os",
                context_ref="mission:ib7:one-ocs",
                authority_ref=profile.authority_envelope_ref,
                policy_snapshot="policy:ib7",
                action_binding=action_binding,
                object_ref_or_selector="mission:ib7:one-ocs",
                trace_ref="trace:ib7",
                max_uses=1,
                single_use=True,
            )
        )
    return leases


def test_ib7_full_continuity_relevant_state_equivalence(tmp_path: Path) -> None:
    store = InstanceBindingStore(tmp_path / "instances.sqlite3")
    guard = IdentityKernelGuard(audit_log=IdentityAuditLog(tmp_path / "identity.jsonl"))
    transport = FakeHazelTransport()
    continuity = HazelBoundContinuity(guard=guard, transport=transport)
    binder = OCSInstanceBinder(
        store=store,
        identity_guard=guard,
        leases=_leases(),
        continuity=continuity,
        binding_secret=b"ib7-binding-secret",
    )
    bridge = WorkInstanceBridge(store)

    prepared, envelope_n = binder.prepare(
        _request(lease_id="lease:ib7:prepare", idempotency_key="idem:ib7:prepare")
    )
    bound_n = bridge.attach(
        prepared.binding_id,
        WorkSpawnReceipt("work:ib7:n", "sofia__ib7_n"),
        expected_version=prepared.version,
        idempotency_key="idem:ib7:attach:n",
    )
    active_n = bridge.acknowledge(
        BootstrapAck(
            prepared.binding_id,
            "work:ib7:n",
            1,
            envelope_n.digest(),
            prepared.identity_binding_hash,
            envelope_n.challenge_nonce,
            "idem:ib7:ack:n",
        ),
        expected_version=bound_n.version,
    )

    business_state = {"counter": 1, "slice": "IB7", "mission": active_n.mission_id}
    original_business_state_hash = _hash(business_state)
    checkpoint_n = binder.checkpoint(
        active_n.binding_id,
        authority=_request(
            lease_id="lease:ib7:checkpoint",
            idempotency_key="idem:ib7:checkpoint-authority",
        ),
        platform_instance_id="work:ib7:n",
        generation=1,
        expected_version=active_n.version,
        state=business_state,
        idempotency_key="idem:ib7:checkpoint",
    )

    replacement_request = replace(
        _request(
            lease_id="lease:ib7:replace",
            idempotency_key="idem:ib7:replacement-prepare",
        ),
        causation_id=checkpoint_n.hazel_event_hash,
    )
    successor, envelope_n1 = binder.replace_instance(
        checkpoint_n.binding_id,
        replacement_request,
        platform_instance_id="work:ib7:n",
        generation=1,
        expected_version=checkpoint_n.version,
        replacement_idempotency_key="idem:ib7:replacement",
    )

    snapshots = AuthenticatedLeaseSnapshotStore(
        tmp_path / "leases.json", b"ib7-lease-snapshot-key"
    )
    snapshots.save(binder._leases)
    restarted_store = InstanceBindingStore(tmp_path / "instances.sqlite3")
    recovery = OCSInstanceRecovery(
        store=restarted_store,
        leases=snapshots.load(),
        continuity=continuity,
    )
    recovered = recovery.recover_instance(
        "org:reis-os", "mission:ib7:one-ocs", "SOFIA"
    )
    recovered_state = continuity.recover_state(
        run_id=successor.run_id,
        expected_ocs="SOFIA",
        host=successor.host,
        authority_ref=successor.authority_ref,
    )
    recovered_payload = recovered_state["payload"]["recovered_payload"]
    recovered_business_state = recovered_payload["state"]
    recovered_business_state_hash = _hash(recovered_business_state)

    bridge_after_restart = WorkInstanceBridge(restarted_store)
    bound_n1 = bridge_after_restart.attach(
        successor.binding_id,
        WorkSpawnReceipt("work:ib7:n1", "sofia__ib7_n1"),
        expected_version=recovered.binding.version,
        idempotency_key="idem:ib7:attach:n1",
    )
    active_n1 = bridge_after_restart.acknowledge(
        BootstrapAck(
            successor.binding_id,
            "work:ib7:n1",
            2,
            envelope_n1.digest(),
            successor.identity_binding_hash,
            envelope_n1.challenge_nonce,
            "idem:ib7:ack:n1",
        ),
        expected_version=bound_n1.version,
    )
    predecessor_after_replacement = restarted_store.get(checkpoint_n.binding_id)

    # MUST MATCH: institutional identity, profile, authority envelope, scope,
    # externalized namespaces, stable run and preserved business state.
    assert checkpoint_n.organization_id == active_n1.organization_id
    assert checkpoint_n.mission_id == active_n1.mission_id
    assert checkpoint_n.ocs_id == active_n1.ocs_id == "SOFIA"
    assert checkpoint_n.run_id == active_n1.run_id
    assert checkpoint_n.profile_version == active_n1.profile_version
    assert checkpoint_n.profile_hash == active_n1.profile_hash
    assert checkpoint_n.identity_binding_hash == active_n1.identity_binding_hash
    assert checkpoint_n.authority_ref == active_n1.authority_ref
    assert checkpoint_n.scope == active_n1.scope
    assert checkpoint_n.state_namespace == active_n1.state_namespace
    assert checkpoint_n.memory_namespace == active_n1.memory_namespace
    assert recovered_business_state == business_state
    assert original_business_state_hash == recovered_business_state_hash

    # MUST MATCH: causal linkage back to the verified checkpoint.
    assert active_n1.predecessor_binding_id == checkpoint_n.binding_id
    assert active_n1.causation_id == checkpoint_n.hazel_event_hash
    assert recovered_state["predecessor_hash"] == checkpoint_n.hazel_event_hash
    assert recovered_state["payload"]["recovered_from"] == checkpoint_n.binding_id
    assert recovered_payload["binding_id"] == checkpoint_n.binding_id
    assert recovered_payload["generation"] == checkpoint_n.generation
    assert recovered_payload["mission_id"] == checkpoint_n.mission_id

    # MUST CHANGE CORRECTLY: replacement appends the next Hazel checkpoint/event.
    assert active_n1.checkpoint_version == checkpoint_n.checkpoint_version + 1
    assert active_n1.checkpoint_hash != checkpoint_n.checkpoint_hash
    assert active_n1.hazel_event_hash != checkpoint_n.hazel_event_hash

    # MUST CHANGE CORRECTLY: the physical instance and leased generation rotate.
    assert checkpoint_n.binding_id != active_n1.binding_id
    assert checkpoint_n.platform_instance_id == "work:ib7:n"
    assert active_n1.platform_instance_id == "work:ib7:n1"
    assert checkpoint_n.platform_instance_id != active_n1.platform_instance_id
    assert active_n1.generation == checkpoint_n.generation + 1
    assert checkpoint_n.lease_id == "lease:ib7:prepare"
    assert active_n1.lease_id == "lease:ib7:replace"
    assert checkpoint_n.lease_id != active_n1.lease_id
    assert predecessor_after_replacement.status is InstanceStatus.REPLACED
    assert active_n1.status is InstanceStatus.ACTIVE
    assert predecessor_after_replacement.binding_id == active_n1.predecessor_binding_id

    comparison = IB7FullStateComparison(
        continuity_invariants_match=all(
            (
                checkpoint_n.organization_id == active_n1.organization_id,
                checkpoint_n.mission_id == active_n1.mission_id,
                checkpoint_n.ocs_id == active_n1.ocs_id,
                checkpoint_n.run_id == active_n1.run_id,
                checkpoint_n.profile_version == active_n1.profile_version,
                checkpoint_n.profile_hash == active_n1.profile_hash,
                checkpoint_n.identity_binding_hash == active_n1.identity_binding_hash,
            )
        ),
        generation_transition_valid=all(
            (
                checkpoint_n.binding_id != active_n1.binding_id,
                checkpoint_n.platform_instance_id != active_n1.platform_instance_id,
                active_n1.generation == checkpoint_n.generation + 1,
                checkpoint_n.lease_id != active_n1.lease_id,
                active_n1.checkpoint_version == checkpoint_n.checkpoint_version + 1,
                active_n1.checkpoint_hash != checkpoint_n.checkpoint_hash,
                active_n1.hazel_event_hash != checkpoint_n.hazel_event_hash,
                predecessor_after_replacement.status is InstanceStatus.REPLACED,
                active_n1.status is InstanceStatus.ACTIVE,
            )
        ),
        business_state_match=recovered_business_state == business_state,
        business_state_hash_match=(
            original_business_state_hash == recovered_business_state_hash
        ),
        lineage_valid=all(
            (
                active_n1.predecessor_binding_id == checkpoint_n.binding_id,
                active_n1.causation_id == checkpoint_n.hazel_event_hash,
                recovered_state["predecessor_hash"] == checkpoint_n.hazel_event_hash,
                recovered_state["payload"]["recovered_from"] == checkpoint_n.binding_id,
                recovered_payload["binding_id"] == checkpoint_n.binding_id,
                recovered_payload["generation"] == checkpoint_n.generation,
                recovered_payload["mission_id"] == checkpoint_n.mission_id,
            )
        ),
        authority_context_valid=all(
            (
                checkpoint_n.authority_ref == active_n1.authority_ref,
                checkpoint_n.scope == active_n1.scope,
            )
        ),
        namespace_continuity_valid=all(
            (
                checkpoint_n.state_namespace == active_n1.state_namespace,
                checkpoint_n.memory_namespace == active_n1.memory_namespace,
            )
        ),
        excluded_fields_with_reason=(
            "version: lifecycle/CAS version is transition-local and must advance",
            "created_at/updated_at: generation-specific timestamps",
            "request_hash/idempotency_key/correlation_id: generation-request-specific",
        ),
    )
    assert comparison.overall_equivalent is True
