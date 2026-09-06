from __future__ import annotations

import json
from dataclasses import dataclass, replace
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


@dataclass(frozen=True, slots=True)
class ActionReceipt:
    idempotency_key: str
    mission_id: str
    ocs_id: str
    payload_hash: str
    effect_number: int


class IdempotentActionLedger:
    """Bounded test effector proving receipt/readback/replay and generation fencing."""

    def __init__(self, store: InstanceBindingStore) -> None:
        self._store = store
        self._receipts: dict[str, ActionReceipt] = {}
        self.effect_count = 0

    def execute(
        self,
        binding: InstanceBinding,
        *,
        generation: int,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> ActionReceipt:
        current = self._store.get(binding.binding_id)
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        payload_hash = sha256(encoded).hexdigest()
        existing = self._receipts.get(idempotency_key)
        if existing is not None:
            if (
                existing.mission_id != binding.mission_id
                or existing.ocs_id != binding.ocs_id
                or existing.payload_hash != payload_hash
            ):
                raise InstanceBindingError("action_idempotency_conflict")
            return existing
        if current.status is not InstanceStatus.ACTIVE:
            raise InstanceBindingError("action_instance_not_active")
        if current.generation != generation:
            raise InstanceBindingError("action_generation_fenced")
        self.effect_count += 1
        receipt = ActionReceipt(
            idempotency_key=idempotency_key,
            mission_id=binding.mission_id,
            ocs_id=binding.ocs_id,
            payload_hash=payload_hash,
            effect_number=self.effect_count,
        )
        self._receipts[idempotency_key] = receipt
        return receipt

    def readback(self, idempotency_key: str) -> ActionReceipt:
        return self._receipts[idempotency_key]


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


def test_ib7_one_ocs_generational_e2e(tmp_path: Path) -> None:
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
    action_ledger = IdempotentActionLedger(store)

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
    assert active_n.status is InstanceStatus.ACTIVE
    assert active_n.generation == 1

    business_state = {"counter": 1, "slice": "IB7", "mission": active_n.mission_id}
    receipt_n = action_ledger.execute(
        active_n,
        generation=1,
        idempotency_key="idem:ib7:action:1",
        payload=business_state,
    )
    assert action_ledger.readback(receipt_n.idempotency_key) == receipt_n

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
    assert checkpoint_n.status is InstanceStatus.CHECKPOINTED

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
    assert store.get(active_n.binding_id).status is InstanceStatus.REPLACED
    assert successor.generation == 2

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
    assert recovered.binding.binding_id == successor.binding_id
    assert recovered.binding.generation == 2

    recovered_state = continuity.recover_state(
        run_id=successor.run_id,
        expected_ocs="SOFIA",
        host=successor.host,
        authority_ref=successor.authority_ref,
    )
    recovered_payload = recovered_state["payload"]["recovered_payload"]
    assert recovered_payload["binding_id"] == checkpoint_n.binding_id
    assert recovered_payload["generation"] == checkpoint_n.generation
    assert recovered_payload["mission_id"] == checkpoint_n.mission_id
    assert recovered_payload["state"] == business_state

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
    assert active_n1.status is InstanceStatus.ACTIVE

    action_ledger._store = restarted_store
    replay = action_ledger.execute(
        active_n1,
        generation=2,
        idempotency_key="idem:ib7:action:1",
        payload=business_state,
    )
    assert replay == receipt_n
    assert action_ledger.effect_count == 1

    with pytest.raises(InstanceBindingError, match="action_instance_not_active"):
        action_ledger.execute(
            store.get(active_n.binding_id),
            generation=1,
            idempotency_key="idem:ib7:old-generation-effect",
            payload={"counter": 2},
        )

    assert active_n.mission_id == active_n1.mission_id
    assert active_n.ocs_id == active_n1.ocs_id == "SOFIA"
    assert active_n.binding_id != active_n1.binding_id
    assert active_n.generation + 1 == active_n1.generation
    assert transport.persist_calls == 2
