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
    InstanceBinding,
    InstanceBindingError,
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


class FakeHazelTransport:
    def __init__(self) -> None:
        self.latest: dict[tuple[str, str, str], dict[str, Any]] = {}
        self.persist_calls = 0

    @staticmethod
    def _hash(value: dict[str, Any]) -> str:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        return sha256(encoded).hexdigest()

    def persist(self, envelope: dict[str, Any]) -> dict[str, Any]:
        self.persist_calls += 1
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


class CrashAfterReplacementCommitStore(InstanceBindingStore):
    crash_once = True

    def commit_replacement(
        self,
        *,
        predecessor_id: str,
        predecessor_expected_version: int,
        successor_id: str,
        successor_expected_version: int,
        idempotency_key: str,
        checkpoint_version: int,
        checkpoint_hash: str,
        hazel_event_hash: str,
    ) -> tuple[InstanceBinding, InstanceBinding]:
        result = super().commit_replacement(
            predecessor_id=predecessor_id,
            predecessor_expected_version=predecessor_expected_version,
            successor_id=successor_id,
            successor_expected_version=successor_expected_version,
            idempotency_key=idempotency_key,
            checkpoint_version=checkpoint_version,
            checkpoint_hash=checkpoint_hash,
            hazel_event_hash=hazel_event_hash,
        )
        if self.crash_once:
            self.crash_once = False
            raise RuntimeError("injected_crash_after_local_replacement_commit")
        return result


def request(*, lease_id: str, idempotency_key: str) -> PrepareInstanceRequest:
    return PrepareInstanceRequest(
        mission_id="mission:ib5",
        organization_id="org:reis-os",
        ocs_id="SOFIA",
        capability="software_implementation_via_valid_envelope_lease_effector",
        lease_id=lease_id,
        host="ChatGPT Work",
        scope=("repo:reis-os-backend",),
        idempotency_key=idempotency_key,
        correlation_id=f"corr:{idempotency_key}",
        actor="NÓESIS",
        context_ref="mission:ib5",
        policy_snapshot="policy:ib5",
        trace_ref="trace:ib5",
    )


def issue_leases() -> AuthorityLeaseManager:
    leases = AuthorityLeaseManager()
    profile = PROFILES["SOFIA"]
    now = time()
    for lease_id, action_binding in (
        ("lease:ib5:prepare", "ocs_instance_binding"),
        ("lease:ib5:checkpoint", "ocs_instance_checkpoint"),
        ("lease:ib5:replace", "ocs_instance_binding"),
    ):
        leases.issue(
            AuthorityLease(
                lease_id=lease_id,
                ocs="SOFIA",
                capability=(
                    "software_implementation_via_valid_envelope_lease_effector"
                ),
                expires_at=now + 3600,
                actor="NÓESIS",
                issued_at=now,
                not_before=now,
                scope=("repo:reis-os-backend",),
                tenant="org:reis-os",
                context_ref="mission:ib5",
                authority_ref=profile.authority_envelope_ref,
                policy_snapshot="policy:ib5",
                action_binding=action_binding,
                object_ref_or_selector="mission:ib5",
                trace_ref="trace:ib5",
                max_uses=1,
                single_use=True,
            )
        )
    return leases


def build_runtime(tmp_path: Path) -> tuple[
    OCSInstanceBinder,
    CrashAfterReplacementCommitStore,
    FakeHazelTransport,
    IdentityKernelGuard,
]:
    store = CrashAfterReplacementCommitStore(tmp_path / "instances.sqlite3")
    guard = IdentityKernelGuard(
        audit_log=IdentityAuditLog(tmp_path / "identity.jsonl")
    )
    transport = FakeHazelTransport()
    continuity = HazelBoundContinuity(guard=guard, transport=transport)
    binder = OCSInstanceBinder(
        store=store,
        identity_guard=guard,
        leases=issue_leases(),
        continuity=continuity,
        binding_secret=b"ib5-binding-secret",
    )
    return binder, store, transport, guard


def reach_checkpoint(
    binder: OCSInstanceBinder, store: InstanceBindingStore
) -> InstanceBinding:
    prepared, envelope = binder.prepare(
        request(lease_id="lease:ib5:prepare", idempotency_key="idem:ib5:prepare")
    )
    bridge = WorkInstanceBridge(store)
    bridge.attach(
        prepared.binding_id,
        WorkSpawnReceipt("work:ib5:1", "sofia__ib5"),
        expected_version=2,
        idempotency_key="idem:ib5:attach",
    )
    active = bridge.acknowledge(
        BootstrapAck(
            prepared.binding_id,
            "work:ib5:1",
            1,
            envelope.digest(),
            prepared.identity_binding_hash,
            envelope.challenge_nonce,
            "idem:ib5:ack",
        ),
        expected_version=3,
    )
    return binder.checkpoint(
        active.binding_id,
        authority=request(
            lease_id="lease:ib5:checkpoint",
            idempotency_key="idem:ib5:checkpoint-authority",
        ),
        platform_instance_id="work:ib5:1",
        generation=1,
        expected_version=4,
        state={"slice": "IB5", "ready": True},
        idempotency_key="idem:ib5:checkpoint",
    )


def test_cold_recovery_finishes_post_commit_saga_without_duplicate_hazel(
    tmp_path: Path,
) -> None:
    binder, store, transport, _ = build_runtime(tmp_path)
    checkpoint = reach_checkpoint(binder, store)
    replacement_request = replace(
        request(
            lease_id="lease:ib5:replace",
            idempotency_key="idem:ib5:replacement-prepare",
        ),
        causation_id=checkpoint.hazel_event_hash,
    )

    with pytest.raises(
        RuntimeError, match="injected_crash_after_local_replacement_commit"
    ):
        binder.replace_instance(
            checkpoint.binding_id,
            replacement_request,
            platform_instance_id="work:ib5:1",
            generation=1,
            expected_version=5,
            replacement_idempotency_key="idem:ib5:replacement",
        )

    writes_at_crash = transport.persist_calls
    predecessor = store.get(checkpoint.binding_id)
    assert predecessor.status is InstanceStatus.REPLACED
    saga = store.action_saga("idem:ib5:replacement")
    assert saga["state"] == "READBACK_VERIFIED"

    snapshots = AuthenticatedLeaseSnapshotStore(
        tmp_path / "leases.json", b"ib5-lease-snapshot-key"
    )
    snapshots.save(binder._leases)
    restarted_store = InstanceBindingStore(tmp_path / "instances.sqlite3")
    recovery = OCSInstanceRecovery(
        store=restarted_store,
        leases=snapshots.load(),
        continuity=binder._continuity,
    )

    result = recovery.recover_instance("org:reis-os", "mission:ib5", "SOFIA")

    assert result.binding.generation == 2
    assert result.binding.status is InstanceStatus.PERSISTED
    assert result.saga_state == "LEASE_FINALIZED"
    assert transport.persist_calls == writes_at_crash
    assert restarted_store.get(checkpoint.binding_id).status is InstanceStatus.REPLACED
    assert (
        restarted_store.action_saga("idem:ib5:replacement")["state"]
        == "LEASE_FINALIZED"
    )


def test_cold_recovery_rejects_local_hazel_hash_divergence(tmp_path: Path) -> None:
    binder, store, _, _ = build_runtime(tmp_path)
    checkpoint = reach_checkpoint(binder, store)
    replacement_request = replace(
        request(
            lease_id="lease:ib5:replace",
            idempotency_key="idem:ib5:replacement-prepare",
        ),
        causation_id=checkpoint.hazel_event_hash,
    )
    store.crash_once = False
    successor, _ = binder.replace_instance(
        checkpoint.binding_id,
        replacement_request,
        platform_instance_id="work:ib5:1",
        generation=1,
        expected_version=5,
        replacement_idempotency_key="idem:ib5:replacement",
    )
    snapshots = AuthenticatedLeaseSnapshotStore(
        tmp_path / "leases.json", b"ib5-lease-snapshot-key"
    )
    snapshots.save(binder._leases)
    restarted_store = InstanceBindingStore(tmp_path / "instances.sqlite3")
    with restarted_store._connect() as connection:
        connection.execute(
            "UPDATE ocs_instance_bindings SET checkpoint_hash = ? WHERE binding_id = ?",
            ("tampered-local-hash", successor.binding_id),
        )
    recovery = OCSInstanceRecovery(
        store=restarted_store,
        leases=snapshots.load(),
        continuity=binder._continuity,
    )

    with pytest.raises(InstanceBindingError, match="recovery_payload_hash_mismatch"):
        recovery.recover_instance("org:reis-os", "mission:ib5", "SOFIA")
