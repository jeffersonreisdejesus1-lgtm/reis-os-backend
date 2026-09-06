from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from time import time
from typing import Any

import pytest

from app.ocs_instances.contracts import (
    BootstrapAck,
    InstanceBindingError,
    InstanceStatus,
    PrepareInstanceRequest,
)
from app.ocs_instances.lease_store import AuthenticatedLeaseSnapshotStore
from app.ocs_instances.recovery import OCSInstanceRecovery
from app.ocs_instances.service import OCSInstanceBinder
from app.ocs_instances.store import InstanceBindingStore
from app.ocs_instances.work_bridge import WorkInstanceBridge, WorkSpawnReceipt
from app.profile_bindings.profiles import PROFILES, validate_profiles
from app.universal_kernel.governance import AuthorityLease, AuthorityLeaseManager
from app.universal_kernel.hazel_continuity import HazelBoundContinuity, HazelIntegrationError
from app.universal_kernel.identity import IdentityAuditLog, IdentityKernelGuard

OCS_IDS = tuple(PROFILES)
DIRECTIONAL_PAIRS = tuple((a, b) for a in OCS_IDS for b in OCS_IDS if a != b)
CAPABILITY = "ib8_parametric_instance_binding_proof"
ORG = "org:reis-os"
HOST = "ChatGPT Work"
SCOPE = ("repo:reis-os-backend",)


class FakeHazelTransport:
    def __init__(self) -> None:
        self.latest: dict[tuple[str, str, str], dict[str, Any]] = {}
        self.last_persist: dict[str, Any] | None = None

    @staticmethod
    def _hash(value: dict[str, Any]) -> str:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return sha256(raw.encode()).hexdigest()

    def persist(self, envelope: dict[str, Any]) -> dict[str, Any]:
        self.last_persist = dict(envelope)
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
            {k: v for k, v in envelope.items() if k != "payload"}
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


def _mission(ocs_id: str) -> str:
    slug = ocs_id.lower().replace("ê", "e").replace("ý", "y").replace("ó", "o").replace("í", "i").replace("á", "a")
    return f"mission:ib8:{slug}"


def _request(ocs_id: str, *, lease_id: str, idempotency_key: str) -> PrepareInstanceRequest:
    return PrepareInstanceRequest(
        mission_id=_mission(ocs_id),
        organization_id=ORG,
        ocs_id=ocs_id,
        capability=CAPABILITY,
        lease_id=lease_id,
        host=HOST,
        scope=SCOPE,
        idempotency_key=idempotency_key,
        correlation_id=f"corr:{idempotency_key}",
        actor="NÓESIS",
        context_ref=_mission(ocs_id),
        policy_snapshot="policy:ib8",
        trace_ref=f"trace:ib8:{ocs_id}",
    )


def _leases(ocs_id: str) -> AuthorityLeaseManager:
    manager = AuthorityLeaseManager()
    profile = PROFILES[ocs_id]
    now = time()
    for suffix, action_binding in (
        ("prepare", "ocs_instance_binding"),
        ("checkpoint", "ocs_instance_checkpoint"),
        ("replace", "ocs_instance_binding"),
    ):
        lease_id = f"lease:ib8:{ocs_id}:{suffix}"
        manager.issue(
            AuthorityLease(
                lease_id=lease_id,
                ocs=ocs_id,
                capability=CAPABILITY,
                expires_at=now + 3600,
                actor="NÓESIS",
                issued_at=now,
                not_before=now,
                scope=SCOPE,
                tenant=ORG,
                context_ref=_mission(ocs_id),
                authority_ref=profile.authority_envelope_ref,
                policy_snapshot="policy:ib8",
                action_binding=action_binding,
                object_ref_or_selector=_mission(ocs_id),
                trace_ref=f"trace:ib8:{ocs_id}",
                max_uses=1,
                single_use=True,
            )
        )
    return manager


def _new_guard(tmp_path: Path, name: str) -> IdentityKernelGuard:
    return IdentityKernelGuard(audit_log=IdentityAuditLog(tmp_path / f"{name}.jsonl"))


def test_ib8_ten_profiles_are_distinct_and_non_authorizing() -> None:
    validate_profiles()
    assert len(OCS_IDS) == 10
    assert len({PROFILES[o].identity for o in OCS_IDS}) == 10
    assert len({PROFILES[o].authority_envelope_ref for o in OCS_IDS}) == 10
    assert len({PROFILES[o].state_namespace for o in OCS_IDS}) == 10
    assert len({PROFILES[o].memory_namespace for o in OCS_IDS}) == 10
    for profile in PROFILES.values():
        assert "authority_transfer=false" in profile.handoff_policy
        assert "memory_import=false" in profile.handoff_policy
        assert profile.capability_adapters == ()
        assert profile.tool_permissions == ()


@pytest.mark.parametrize("ocs_id", OCS_IDS)
def test_ib8_each_ocs_generation_replacement_fencing_and_recovery(
    tmp_path: Path, ocs_id: str
) -> None:
    profile = PROFILES[ocs_id]
    store = InstanceBindingStore(tmp_path / f"{ocs_id}-instances.sqlite3")
    guard = _new_guard(tmp_path, f"{ocs_id}-identity")
    transport = FakeHazelTransport()
    continuity = HazelBoundContinuity(guard=guard, transport=transport)
    binder = OCSInstanceBinder(
        store=store,
        identity_guard=guard,
        leases=_leases(ocs_id),
        continuity=continuity,
        binding_secret=f"ib8:{ocs_id}".encode(),
    )
    bridge = WorkInstanceBridge(store)

    prepared, envelope_n = binder.prepare(
        _request(
            ocs_id,
            lease_id=f"lease:ib8:{ocs_id}:prepare",
            idempotency_key=f"idem:ib8:{ocs_id}:prepare",
        )
    )
    assert prepared.profile_version == profile.version
    assert prepared.profile_hash
    assert prepared.authority_ref == profile.authority_envelope_ref
    assert prepared.state_namespace == profile.state_namespace
    assert prepared.memory_namespace == profile.memory_namespace
    assert prepared.organization_id == ORG
    assert prepared.mission_id == _mission(ocs_id)
    assert prepared.ocs_id == ocs_id
    assert prepared.generation == 1

    bound_n = bridge.attach(
        prepared.binding_id,
        WorkSpawnReceipt(f"work:ib8:{ocs_id}:n", f"{ocs_id}:n"),
        expected_version=prepared.version,
        idempotency_key=f"idem:ib8:{ocs_id}:attach:n",
    )
    active_n = bridge.acknowledge(
        BootstrapAck(
            prepared.binding_id,
            f"work:ib8:{ocs_id}:n",
            1,
            envelope_n.digest(),
            prepared.identity_binding_hash,
            envelope_n.challenge_nonce,
            f"idem:ib8:{ocs_id}:ack:n",
        ),
        expected_version=bound_n.version,
    )
    checkpoint_n = binder.checkpoint(
        active_n.binding_id,
        authority=_request(
            ocs_id,
            lease_id=f"lease:ib8:{ocs_id}:checkpoint",
            idempotency_key=f"idem:ib8:{ocs_id}:checkpoint-authority",
        ),
        platform_instance_id=f"work:ib8:{ocs_id}:n",
        generation=1,
        expected_version=active_n.version,
        state={"ocs_id": ocs_id, "generation": 1, "mission": _mission(ocs_id)},
        idempotency_key=f"idem:ib8:{ocs_id}:checkpoint",
    )

    replacement_request = replace(
        _request(
            ocs_id,
            lease_id=f"lease:ib8:{ocs_id}:replace",
            idempotency_key=f"idem:ib8:{ocs_id}:replacement-prepare",
        ),
        causation_id=checkpoint_n.hazel_event_hash,
    )
    successor, envelope_n1 = binder.replace_instance(
        checkpoint_n.binding_id,
        replacement_request,
        platform_instance_id=f"work:ib8:{ocs_id}:n",
        generation=1,
        expected_version=checkpoint_n.version,
        replacement_idempotency_key=f"idem:ib8:{ocs_id}:replacement",
    )
    assert successor.generation == 2
    assert successor.predecessor_binding_id == checkpoint_n.binding_id
    assert store.get(checkpoint_n.binding_id).status is InstanceStatus.REPLACED

    with pytest.raises(InstanceBindingError, match="active_instance_required_for_checkpoint"):
        binder.checkpoint(
            checkpoint_n.binding_id,
            authority=_request(
                ocs_id,
                lease_id=f"lease:ib8:{ocs_id}:checkpoint",
                idempotency_key=f"idem:ib8:{ocs_id}:old-generation-denied",
            ),
            platform_instance_id=f"work:ib8:{ocs_id}:n",
            generation=1,
            expected_version=checkpoint_n.version,
            state={"forbidden": True},
            idempotency_key=f"idem:ib8:{ocs_id}:old-generation-effect",
        )

    snapshots = AuthenticatedLeaseSnapshotStore(
        tmp_path / f"{ocs_id}-leases.json", f"ib8-lease-key:{ocs_id}".encode()
    )
    snapshots.save(binder._leases)
    restarted_store = InstanceBindingStore(tmp_path / f"{ocs_id}-instances.sqlite3")
    recovery = OCSInstanceRecovery(
        store=restarted_store,
        leases=snapshots.load(),
        continuity=continuity,
    )
    recovered = recovery.recover_instance(ORG, _mission(ocs_id), ocs_id)
    assert recovered.binding.binding_id == successor.binding_id
    assert recovered.binding.generation == 2
    assert recovered.binding.ocs_id == ocs_id
    assert recovered.binding.state_namespace == profile.state_namespace
    assert recovered.binding.memory_namespace == profile.memory_namespace

    bridge_after_restart = WorkInstanceBridge(restarted_store)
    bound_n1 = bridge_after_restart.attach(
        successor.binding_id,
        WorkSpawnReceipt(f"work:ib8:{ocs_id}:n1", f"{ocs_id}:n1"),
        expected_version=recovered.binding.version,
        idempotency_key=f"idem:ib8:{ocs_id}:attach:n1",
    )
    active_n1 = bridge_after_restart.acknowledge(
        BootstrapAck(
            successor.binding_id,
            f"work:ib8:{ocs_id}:n1",
            2,
            envelope_n1.digest(),
            successor.identity_binding_hash,
            envelope_n1.challenge_nonce,
            f"idem:ib8:{ocs_id}:ack:n1",
        ),
        expected_version=bound_n1.version,
    )
    assert active_n1.status is InstanceStatus.ACTIVE
    assert active_n1.generation == 2


@pytest.mark.parametrize("source_ocs,target_ocs", DIRECTIONAL_PAIRS)
def test_ib8_directional_isolation_pair(
    tmp_path: Path, source_ocs: str, target_ocs: str
) -> None:
    source = PROFILES[source_ocs]
    target = PROFILES[target_ocs]
    assert source_ocs != target_ocs
    assert source.state_namespace != target.state_namespace
    assert source.memory_namespace != target.memory_namespace
    assert source.authority_envelope_ref != target.authority_envelope_ref
    assert source.identity != target.identity

    # Production persist has no caller-supplied namespace: both namespaces are derived
    # exclusively from the source binding after Kernel revalidation.
    guard = _new_guard(tmp_path, f"pair-{source_ocs}-{target_ocs}-persist")
    binding = guard.bind_active_identity(
        run_id=f"run:ib8:{source_ocs}:{target_ocs}:persist",
        ocs_id=source_ocs,
        host=HOST,
        session_context="ib8-directional-isolation",
    )
    transport = FakeHazelTransport()
    continuity = HazelBoundContinuity(guard=guard, transport=transport)
    continuity.persist_state(
        run_id=binding.run_id,
        expected_ocs=source_ocs,
        host=HOST,
        authority_ref=source.authority_envelope_ref,
        state_version=1,
        predecessor_hash=None,
        state={"source": source_ocs, "target": target_ocs},
        trace_id=f"trace:ib8:{source_ocs}:{target_ocs}",
    )
    assert transport.last_persist is not None
    assert transport.last_persist["state_namespace"] == source.state_namespace
    assert transport.last_persist["memory_namespace"] == source.memory_namespace
    assert transport.last_persist["state_namespace"] != target.state_namespace
    assert transport.last_persist["memory_namespace"] != target.memory_namespace

    # A cannot use B's authority/lease identity on A's binding.
    guard_authority = _new_guard(tmp_path, f"pair-{source_ocs}-{target_ocs}-authority")
    binding_authority = guard_authority.bind_active_identity(
        run_id=f"run:ib8:{source_ocs}:{target_ocs}:authority",
        ocs_id=source_ocs,
        host=HOST,
        session_context="ib8-directional-isolation",
    )
    with pytest.raises(HazelIntegrationError, match="authority_ref_mismatch"):
        HazelBoundContinuity(
            guard=guard_authority, transport=FakeHazelTransport()
        ).persist_state(
            run_id=binding_authority.run_id,
            expected_ocs=source_ocs,
            host=HOST,
            authority_ref=target.authority_envelope_ref,
            state_version=1,
            predecessor_hash=None,
            state={"forbidden": "foreign-authority"},
            trace_id="trace:ib8:foreign-authority",
        )

    # Name/handoff text cannot impersonate B: expected identity mismatch fails closed.
    guard_identity = _new_guard(tmp_path, f"pair-{source_ocs}-{target_ocs}-identity")
    identity_binding = guard_identity.bind_active_identity(
        run_id=f"run:ib8:{source_ocs}:{target_ocs}:identity",
        ocs_id=source_ocs,
        host=HOST,
        session_context=f"handoff says {target_ocs}",
    )
    result = guard_identity.revalidate(
        run_id=identity_binding.run_id,
        expected_ocs=target_ocs,
        trigger=__import__(
            "app.universal_kernel.identity", fromlist=["IdentityRecheckTrigger"]
        ).IdentityRecheckTrigger.HANDOFF,
        host=HOST,
    )
    assert result.valid is False
    assert result.reason == "active_ocs_identity_mismatch"

    # A cannot recover a checkpoint carrying B's identity, namespaces or binding hash.
    guard_recovery = _new_guard(tmp_path, f"pair-{source_ocs}-{target_ocs}-recovery")
    recovery_binding = guard_recovery.bind_active_identity(
        run_id=f"run:ib8:{source_ocs}:{target_ocs}:recovery",
        ocs_id=source_ocs,
        host=HOST,
        session_context="ib8-directional-isolation",
    )
    recovery_transport = FakeHazelTransport()
    recovery_continuity = HazelBoundContinuity(
        guard=guard_recovery, transport=recovery_transport
    )
    recovery_continuity.persist_state(
        run_id=recovery_binding.run_id,
        expected_ocs=source_ocs,
        host=HOST,
        authority_ref=source.authority_envelope_ref,
        state_version=1,
        predecessor_hash=None,
        state={"checkpoint": source_ocs},
        trace_id="trace:ib8:recovery-source",
    )
    key = (
        recovery_binding.run_id,
        source_ocs,
        source.state_namespace,
    )
    original = dict(recovery_transport.latest[key])

    recovery_transport.latest[key] = {**original, "ocs_id": target_ocs}
    with pytest.raises(HazelIntegrationError, match="recovery_ocs_mismatch"):
        recovery_continuity.recover_state(
            run_id=recovery_binding.run_id,
            expected_ocs=source_ocs,
            host=HOST,
            authority_ref=source.authority_envelope_ref,
        )

    recovery_transport.latest[key] = {**original, "state_namespace": target.state_namespace}
    with pytest.raises(HazelIntegrationError, match="recovery_namespace_mismatch"):
        recovery_continuity.recover_state(
            run_id=recovery_binding.run_id,
            expected_ocs=source_ocs,
            host=HOST,
            authority_ref=source.authority_envelope_ref,
        )

    recovery_transport.latest[key] = {**original, "memory_namespace": target.memory_namespace}
    with pytest.raises(HazelIntegrationError, match="recovery_memory_namespace_mismatch"):
        recovery_continuity.recover_state(
            run_id=recovery_binding.run_id,
            expected_ocs=source_ocs,
            host=HOST,
            authority_ref=source.authority_envelope_ref,
        )

    target_guard = _new_guard(tmp_path, f"pair-{source_ocs}-{target_ocs}-target-hash")
    target_binding = target_guard.bind_active_identity(
        run_id=f"run:ib8:{source_ocs}:{target_ocs}:target",
        ocs_id=target_ocs,
        host=HOST,
        session_context="ib8-target-hash",
    )
    foreign_hash = IdentityAuditLog.binding_hash(target_binding)
    recovery_transport.latest[key] = {**original, "binding_hash": foreign_hash}
    with pytest.raises(HazelIntegrationError, match="recovery_binding_mismatch"):
        recovery_continuity.recover_state(
            run_id=recovery_binding.run_id,
            expected_ocs=source_ocs,
            host=HOST,
            authority_ref=source.authority_envelope_ref,
        )

    assert "memory_import=false" in source.handoff_policy
    assert "authority_transfer=false" in source.handoff_policy


def test_ib8_required_cardinalities() -> None:
    assert len(OCS_IDS) == 10
    assert len(DIRECTIONAL_PAIRS) == 90
