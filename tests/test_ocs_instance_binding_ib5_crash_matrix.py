from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from app.ocs_instances.contracts import BootstrapAck, InstanceBindingError, InstanceStatus
from app.ocs_instances.lease_store import AuthenticatedLeaseSnapshotStore
from app.ocs_instances.recovery import OCSInstanceRecovery
from app.ocs_instances.store import InstanceBindingStore
from app.ocs_instances.work_bridge import WorkInstanceBridge, WorkSpawnReceipt
from test_ocs_instance_binding_ib5_recovery import build_runtime, reach_checkpoint, request


def restarted_recovery(
    tmp_path: Path,
    binder: object,
) -> tuple[InstanceBindingStore, OCSInstanceRecovery]:
    snapshots = AuthenticatedLeaseSnapshotStore(
        tmp_path / "matrix-leases.json", b"ib5-matrix-lease-key"
    )
    leases = getattr(binder, "_leases")
    continuity = getattr(binder, "_continuity")
    snapshots.save(leases)
    store = InstanceBindingStore(tmp_path / "instances.sqlite3")
    recovery = OCSInstanceRecovery(
        store=store,
        leases=snapshots.load(),
        continuity=continuity,
    )
    return store, recovery


def test_c0_checkpoint_cold_recovery_is_stable(tmp_path: Path) -> None:
    binder, store, transport, _ = build_runtime(tmp_path)
    checkpoint = reach_checkpoint(binder, store)
    writes = transport.persist_calls
    _, recovery = restarted_recovery(tmp_path, binder)

    result = recovery.recover_instance("org:reis-os", "mission:ib5", "SOFIA")

    assert result.binding == checkpoint
    assert result.binding.status is InstanceStatus.CHECKPOINTED
    assert transport.persist_calls == writes


def test_c1_stranded_replacement_saga_fails_closed(tmp_path: Path) -> None:
    binder, store, transport, _ = build_runtime(tmp_path)
    checkpoint = reach_checkpoint(binder, store)
    writes = transport.persist_calls
    store.begin_action_saga(
        idempotency_key="idem:ib5:stranded-replacement",
        binding_id=checkpoint.binding_id,
        operation="ocs_instance_replacement",
        request_fingerprint="fingerprint:stranded",
        payload={"lease_id": "lease:ib5:replace"},
    )
    _, recovery = restarted_recovery(tmp_path, binder)

    with pytest.raises(InstanceBindingError, match="replacement_successor_missing"):
        recovery.recover_instance("org:reis-os", "mission:ib5", "SOFIA")
    assert transport.persist_calls == writes


def test_c2_prepared_successor_resumes_missing_hazel_effect_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binder, store, transport, _ = build_runtime(tmp_path)
    checkpoint = reach_checkpoint(binder, store)
    replacement_request = replace(
        request(
            lease_id="lease:ib5:replace",
            idempotency_key="idem:ib5:c2-prepare",
        ),
        causation_id=checkpoint.hazel_event_hash,
    )
    original_create = store.create

    def crash_after_successor_create(binding: object) -> object:
        created = original_create(binding)  # type: ignore[arg-type]
        if created.predecessor_binding_id is not None:
            raise RuntimeError("injected_c2_after_successor_prepare")
        return created

    monkeypatch.setattr(store, "create", crash_after_successor_create)
    with pytest.raises(RuntimeError, match="injected_c2_after_successor_prepare"):
        binder.replace_instance(
            checkpoint.binding_id,
            replacement_request,
            platform_instance_id="work:ib5:1",
            generation=1,
            expected_version=5,
            replacement_idempotency_key="idem:ib5:c2-replacement",
        )
    writes_at_crash = transport.persist_calls
    successor_id = store.by_idempotency("idem:ib5:c2-prepare")
    assert successor_id is not None
    assert successor_id.status is InstanceStatus.PREPARED

    restarted_store, recovery = restarted_recovery(tmp_path, binder)
    result = recovery.recover_instance("org:reis-os", "mission:ib5", "SOFIA")

    assert result.binding.generation == 2
    assert result.binding.status is InstanceStatus.PERSISTED
    assert result.saga_state == "LEASE_FINALIZED"
    assert transport.persist_calls == writes_at_crash + 1
    assert restarted_store.get(checkpoint.binding_id).status is InstanceStatus.REPLACED


def test_c8_c9_attach_and_ack_remain_recoverable_without_new_hazel_write(
    tmp_path: Path,
) -> None:
    binder, store, transport, _ = build_runtime(tmp_path)
    checkpoint = reach_checkpoint(binder, store)
    store.crash_once = False
    replacement_request = replace(
        request(
            lease_id="lease:ib5:replace",
            idempotency_key="idem:ib5:c8-prepare",
        ),
        causation_id=checkpoint.hazel_event_hash,
    )
    successor, envelope = binder.replace_instance(
        checkpoint.binding_id,
        replacement_request,
        platform_instance_id="work:ib5:1",
        generation=1,
        expected_version=5,
        replacement_idempotency_key="idem:ib5:c8-replacement",
    )
    bridge = WorkInstanceBridge(store)
    bound = bridge.attach(
        successor.binding_id,
        WorkSpawnReceipt("work:ib5:2", "sofia__ib5-generation-2"),
        expected_version=2,
        idempotency_key="idem:ib5:c8-attach",
    )
    writes = transport.persist_calls
    _, recovery = restarted_recovery(tmp_path, binder)
    c8 = recovery.recover_instance("org:reis-os", "mission:ib5", "SOFIA")
    assert c8.binding.status is InstanceStatus.BOUND
    assert transport.persist_calls == writes

    active = bridge.acknowledge(
        BootstrapAck(
            bound.binding_id,
            "work:ib5:2",
            2,
            envelope.digest(),
            bound.identity_binding_hash,
            envelope.challenge_nonce,
            "idem:ib5:c9-ack",
        ),
        expected_version=3,
    )
    _, recovery_after_ack = restarted_recovery(tmp_path, binder)
    c9 = recovery_after_ack.recover_instance(
        "org:reis-os", "mission:ib5", "SOFIA"
    )
    assert c9.binding == active
    assert c9.binding.status is InstanceStatus.ACTIVE
    assert transport.persist_calls == writes
