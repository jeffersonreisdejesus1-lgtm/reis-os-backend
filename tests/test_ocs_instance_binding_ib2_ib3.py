from __future__ import annotations

import json
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path
from time import time
from typing import Any
from unicodedata import normalize

import pytest

from app.ocs_instances.contracts import (
    BindingMaturity,
    BootstrapAck,
    InstanceBinding,
    InstanceBindingError,
    InstanceStatus,
    PrepareInstanceRequest,
)
from app.ocs_instances.lease_store import AuthenticatedLeaseSnapshotStore
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


class FaultInjectingStore(InstanceBindingStore):
    fail_after_state: str | None = None
    failure_emitted = False

    def advance_action_saga(
        self,
        idempotency_key: str,
        *,
        expected_state: str,
        target_state: str,
    ) -> dict[str, Any]:
        result = super().advance_action_saga(
            idempotency_key,
            expected_state=expected_state,
            target_state=target_state,
        )
        if target_state == self.fail_after_state and not self.failure_emitted:
            self.failure_emitted = True
            raise RuntimeError(f"injected_crash_after:{target_state}")
        return result


def make_binding(
    *,
    binding_id: str = "binding:1",
    idempotency_key: str = "idem:prepare:1",
) -> InstanceBinding:
    return InstanceBinding(
        binding_id=binding_id,
        mission_id="mission:1",
        run_id="REIS OS:org:reis-os:mission:1:SOFIA",
        organization_id="org:reis-os",
        ocs_id="SOFIA",
        profile_version="r2-v0.1.0",
        profile_hash="profile-hash",
        identity_binding_hash="identity-binding-hash",
        request_hash="request-hash",
        maturity=BindingMaturity.OPERATIONALLY_BOUND_L1,
        host="ChatGPT Work",
        capability="software_implementation_via_valid_envelope_lease_effector",
        lease_id="lease:sofia:1",
        authority_ref=PROFILES["SOFIA"].authority_envelope_ref,
        scope=("repo:reis-os-backend",),
        state_namespace=PROFILES["SOFIA"].state_namespace,
        memory_namespace=PROFILES["SOFIA"].memory_namespace,
        generation=1,
        platform_instance_id=None,
        challenge_hash="challenge-hash",
        bootstrap_hash="bootstrap-hash",
        status=InstanceStatus.PREPARED,
        version=1,
        predecessor_binding_id=None,
        checkpoint_version=0,
        checkpoint_hash=None,
        hazel_event_hash=None,
        idempotency_key=idempotency_key,
        correlation_id="correlation:1",
        causation_id=None,
        created_at=1.0,
        updated_at=1.0,
    )


def build_binder(
    tmp_path: Path,
    *,
    store: InstanceBindingStore | None = None,
) -> tuple[OCSInstanceBinder, InstanceBindingStore, FakeHazelTransport]:
    store = store or InstanceBindingStore(tmp_path / "instances.sqlite3")
    identity = IdentityKernelGuard(
        audit_log=IdentityAuditLog(tmp_path / "identity.jsonl")
    )
    leases = AuthorityLeaseManager()
    now = time()
    profile = PROFILES["SOFIA"]
    leases.issue(
        AuthorityLease(
            lease_id="lease:sofia:1",
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
            context_ref="mission:1",
            authority_ref=profile.authority_envelope_ref,
            policy_snapshot="policy:mission:1",
            action_binding="ocs_instance_binding",
            object_ref_or_selector="mission:1",
            trace_ref="trace:mission:1",
            max_uses=1,
            single_use=True,
        )
    )
    leases.issue(
        AuthorityLease(
            lease_id="lease:sofia:checkpoint:1",
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
            context_ref="mission:1",
            authority_ref=profile.authority_envelope_ref,
            policy_snapshot="policy:mission:1",
            action_binding="ocs_instance_checkpoint",
            object_ref_or_selector="mission:1",
            trace_ref="trace:mission:1",
            max_uses=1,
            single_use=True,
        )
    )
    leases.issue(
        AuthorityLease(
            lease_id="lease:sofia:2",
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
            context_ref="mission:1",
            authority_ref=profile.authority_envelope_ref,
            policy_snapshot="policy:mission:1",
            action_binding="ocs_instance_binding",
            object_ref_or_selector="mission:1",
            trace_ref="trace:mission:1",
            max_uses=1,
            single_use=True,
        )
    )
    transport = FakeHazelTransport()
    continuity = HazelBoundContinuity(guard=identity, transport=transport)
    binder = OCSInstanceBinder(
        store=store,
        identity_guard=identity,
        leases=leases,
        continuity=continuity,
        binding_secret=b"test-binding-secret",
    )
    return binder, store, transport


def prepare_request() -> PrepareInstanceRequest:
    return PrepareInstanceRequest(
        mission_id="mission:1",
        organization_id="org:reis-os",
        ocs_id="SOFIA",
        capability="software_implementation_via_valid_envelope_lease_effector",
        lease_id="lease:sofia:1",
        host="ChatGPT Work",
        scope=("repo:reis-os-backend",),
        idempotency_key="idem:prepare:1",
        correlation_id="correlation:1",
        actor="NÓESIS",
        context_ref="mission:1",
        policy_snapshot="policy:mission:1",
        trace_ref="trace:mission:1",
    )


def test_registry_survives_restart_and_journals_prepare(tmp_path: Path) -> None:
    path = tmp_path / "instances.sqlite3"
    first = InstanceBindingStore(path)
    binding = make_binding()
    first.create(binding)

    restarted = InstanceBindingStore(path)

    assert restarted.get(binding.binding_id) == binding
    assert (
        restarted.latest_generation("org:reis-os", "mission:1", "SOFIA") == 1
    )
    journal = restarted.journal(binding.binding_id)
    assert len(journal) == 1
    assert journal[0]["event_type"] == "OCS_INSTANCE_PREPARED"


def test_registry_cas_rejects_stale_writer(tmp_path: Path) -> None:
    store = InstanceBindingStore(tmp_path / "instances.sqlite3")
    binding = store.create(make_binding())
    store.transition(
        binding.binding_id,
        expected_version=1,
        target=InstanceStatus.PERSISTED,
        idempotency_key="idem:persist:1",
        event_type="OCS_INSTANCE_PERSISTED",
    )
    store.transition(
        binding.binding_id,
        expected_version=2,
        target=InstanceStatus.BOUND,
        idempotency_key="idem:attach:1",
        event_type="OCS_PLATFORM_INSTANCE_ATTACHED",
        platform_instance_id="work:1",
    )

    with pytest.raises(
        InstanceBindingError, match="instance_version_conflict"
    ):
        store.transition(
            binding.binding_id,
            expected_version=2,
            target=InstanceStatus.ACTIVE,
            idempotency_key="idem:ack:stale",
            event_type="OCS_BOOTSTRAP_ACKNOWLEDGED",
        )


def test_registry_rejects_second_active_binding_for_same_mission_ocs(
    tmp_path: Path,
) -> None:
    store = InstanceBindingStore(tmp_path / "instances.sqlite3")
    store.create(make_binding())

    with pytest.raises(
        InstanceBindingError, match="active_mission_ocs_binding_exists"
    ):
        store.create(
            make_binding(
                binding_id="binding:2",
                idempotency_key="idem:prepare:2",
            )
        )


def test_binder_reuses_profile_identity_lease_and_hazel(
    tmp_path: Path,
) -> None:
    binder, store, transport = build_binder(tmp_path)

    binding, envelope = binder.prepare(prepare_request())

    assert binding.run_id.startswith("run:")
    assert binding.profile_version == PROFILES["SOFIA"].version
    assert binding.maturity is BindingMaturity.PREPARED_UNVERIFIED
    assert binding.state_namespace == PROFILES["SOFIA"].state_namespace
    assert binding.memory_namespace == PROFILES["SOFIA"].memory_namespace
    assert envelope.tool_permissions == ()
    assert binding.bootstrap_hash == envelope.digest()
    assert store.get(binding.binding_id) == binding
    assert transport.persist_calls == 1


def test_binder_rejects_non_mission_lease(tmp_path: Path) -> None:
    binder, _, _ = build_binder(tmp_path)
    request = replace(prepare_request(), mission_id="mission:forged")

    with pytest.raises(ValueError, match="mission_specific_lease_required"):
        binder.prepare(request)


def test_work_bridge_requires_matching_name_and_challenge(
    tmp_path: Path,
) -> None:
    binder, store, _ = build_binder(tmp_path)
    binding, envelope = binder.prepare(prepare_request())
    bridge = WorkInstanceBridge(store)

    for invalid_name in ("agora__mission-1", "sofiaevil"):
        with pytest.raises(
            InstanceBindingError, match="work_task_name_ocs_mismatch"
        ):
            bridge.attach(
                binding.binding_id,
                WorkSpawnReceipt("work:1", invalid_name),
                expected_version=2,
                idempotency_key=f"idem:attach:wrong:{invalid_name}",
            )

    bound = bridge.attach(
        binding.binding_id,
        WorkSpawnReceipt("work:1", "sofia__mission-1"),
        expected_version=2,
        idempotency_key="idem:attach:1",
    )
    assert bound.status is InstanceStatus.BOUND

    with pytest.raises(InstanceBindingError, match="bootstrap_challenge_failed"):
        bridge.acknowledge(
            BootstrapAck(
                binding_id=binding.binding_id,
                platform_instance_id="work:1",
                generation=1,
                bootstrap_hash=binding.bootstrap_hash,
                identity_binding_hash=binding.identity_binding_hash,
                challenge_nonce="wrong",
                idempotency_key="idem:ack:wrong",
            ),
            expected_version=3,
        )

    active = bridge.acknowledge(
        BootstrapAck(
            binding_id=binding.binding_id,
            platform_instance_id="work:1",
            generation=1,
            bootstrap_hash=envelope.digest(),
            identity_binding_hash=binding.identity_binding_hash,
            challenge_nonce=envelope.challenge_nonce,
            idempotency_key="idem:ack:1",
        ),
        expected_version=3,
    )
    assert active.status is InstanceStatus.ACTIVE
    assert active.maturity is BindingMaturity.OPERATIONALLY_BOUND_L1
    assert active.platform_instance_id == "work:1"


@pytest.mark.parametrize("ocs_id", tuple(PROFILES))
def test_all_ten_profiles_bind_identity_namespace_and_authority(
    tmp_path: Path, ocs_id: str
) -> None:
    from app.ocs_instances.contracts import canonical_hash, stable_run_id

    profile = PROFILES[ocs_id]
    run_id = stable_run_id("REIS OS", "org:all", "mission:all", ocs_id)
    assert run_id != stable_run_id(
        "REIS OS", "org:other", "mission:all", ocs_id
    )
    guard = IdentityKernelGuard(
        audit_log=IdentityAuditLog(tmp_path / f"{ocs_id}.jsonl")
    )
    binding = guard.bind_active_identity(
        run_id=run_id,
        ocs_id=ocs_id,
        host="ChatGPT Work",
        session_context="mission:all",
    )
    assert binding.ocs_id == profile.ocs_id
    assert binding.state_namespace == profile.state_namespace
    assert binding.memory_namespace == profile.memory_namespace
    assert binding.authority_envelope_ref == profile.authority_envelope_ref
    assert canonical_hash(asdict(profile))


def test_prepare_replay_recovers_same_bootstrap_without_second_hazel_write(
    tmp_path: Path,
) -> None:
    binder, _, transport = build_binder(tmp_path)

    first_binding, first_envelope = binder.prepare(prepare_request())
    second_binding, second_envelope = binder.prepare(prepare_request())

    assert second_binding == first_binding
    assert second_envelope == first_envelope
    assert transport.persist_calls == 1


def test_checkpoint_replacement_restart_and_old_generation_fencing(
    tmp_path: Path,
) -> None:
    binder, store, transport = build_binder(tmp_path)
    binding, envelope = binder.prepare(prepare_request())
    bridge = WorkInstanceBridge(store)
    bridge.attach(
        binding.binding_id,
        WorkSpawnReceipt("work:1", "sofia__mission-1"),
        expected_version=2,
        idempotency_key="idem:attach:1",
    )
    active = bridge.acknowledge(
        BootstrapAck(
            binding.binding_id,
            "work:1",
            1,
            envelope.digest(),
            binding.identity_binding_hash,
            envelope.challenge_nonce,
            "idem:ack:1",
        ),
        expected_version=3,
    )
    checkpoint = binder.checkpoint(
        active.binding_id,
        authority=replace(
            prepare_request(), lease_id="lease:sofia:checkpoint:1"
        ),
        platform_instance_id="work:1",
        generation=1,
        expected_version=4,
        state={"slice": "IB3", "completed": True},
        idempotency_key="idem:checkpoint:1",
    )
    assert checkpoint.checkpoint_version == 2
    lease_store = AuthenticatedLeaseSnapshotStore(
        tmp_path / "leases.json", b"lease-snapshot-test-key"
    )
    lease_store.save(binder._leases)
    restored_leases = lease_store.load()
    assert restored_leases.uses_consumed("lease:sofia:checkpoint:1") == 1
    writes_after_checkpoint = transport.persist_calls
    replay = binder.checkpoint(
        active.binding_id,
        authority=replace(
            prepare_request(), lease_id="lease:sofia:checkpoint:1"
        ),
        platform_instance_id="work:1",
        generation=1,
        expected_version=4,
        state={"slice": "IB3", "completed": True},
        idempotency_key="idem:checkpoint:1",
    )
    assert replay == checkpoint
    assert transport.persist_calls == writes_after_checkpoint
    with pytest.raises(InstanceBindingError, match="instance_idempotency_conflict"):
        binder.checkpoint(
            active.binding_id,
            authority=replace(
                prepare_request(), lease_id="lease:sofia:checkpoint:1"
            ),
            platform_instance_id="work:1",
            generation=1,
            expected_version=4,
            state={"slice": "IB3", "completed": False},
            idempotency_key="idem:checkpoint:1",
        )
    replacement_request = replace(
        prepare_request(),
        lease_id="lease:sofia:2",
        idempotency_key="idem:prepare:2",
        correlation_id="correlation:2",
        causation_id=checkpoint.hazel_event_hash,
    )
    replacement, recovered_envelope = binder.replace_instance(
        checkpoint.binding_id,
        replacement_request,
        platform_instance_id="work:1",
        generation=1,
        expected_version=5,
        replacement_idempotency_key="idem:replace:1",
    )
    assert replacement.generation == 2
    assert replacement.predecessor_binding_id == binding.binding_id
    assert replacement.checkpoint_version == 3
    assert replacement.run_id == binding.run_id
    assert recovered_envelope.identity_binding_hash == binding.identity_binding_hash
    writes_after_replacement = transport.persist_calls
    replayed_replacement, replayed_envelope = binder.replace_instance(
        checkpoint.binding_id,
        replacement_request,
        platform_instance_id="work:1",
        generation=1,
        expected_version=5,
        replacement_idempotency_key="idem:replace:1",
    )
    assert replayed_replacement == replacement
    assert replayed_envelope == recovered_envelope
    assert transport.persist_calls == writes_after_replacement

    restarted = InstanceBindingStore(tmp_path / "instances.sqlite3")
    assert restarted.get(binding.binding_id).status is InstanceStatus.REPLACED
    assert restarted.get(replacement.binding_id).generation == 2
    with pytest.raises(
        InstanceBindingError, match="active_instance_required_for_checkpoint"
    ):
        binder.checkpoint(
            binding.binding_id,
            authority=replace(
                prepare_request(), lease_id="lease:sofia:checkpoint:1"
            ),
            platform_instance_id="work:1",
            generation=1,
            expected_version=6,
            state={"forged": True},
            idempotency_key="idem:checkpoint:old",
        )


@pytest.mark.parametrize("ocs_id", tuple(PROFILES))
def test_ten_ocs_complete_bootstrap_ack_checkpoint_recovery(
    tmp_path: Path,
    ocs_id: str,
) -> None:
    profile = PROFILES[ocs_id]
    capability = profile.allowed_action_classes[0]
    mission_id = f"mission:{ocs_id}"
    organization_id = "org:all"
    root = tmp_path / ocs_id
    root.mkdir()
    store = InstanceBindingStore(root / "instances.sqlite3")
    identity = IdentityKernelGuard(
        audit_log=IdentityAuditLog(root / "identity.jsonl")
    )
    leases = AuthorityLeaseManager()
    now = time()
    lease_id = f"lease:{ocs_id}:1"
    trace_ref = f"trace:{ocs_id}:1"
    leases.issue(
        AuthorityLease(
            lease_id=lease_id,
            ocs=ocs_id,
            capability=capability,
            expires_at=now + 3600,
            actor="NÓESIS",
            issued_at=now,
            not_before=now,
            scope=("repo:reis-os-backend",),
            tenant=organization_id,
            context_ref=mission_id,
            authority_ref=profile.authority_envelope_ref,
            policy_snapshot="policy:all",
            action_binding="ocs_instance_binding",
            object_ref_or_selector=mission_id,
            trace_ref=trace_ref,
            max_uses=1,
            single_use=True,
        )
    )
    checkpoint_lease_id = f"lease:{ocs_id}:checkpoint"
    leases.issue(
        AuthorityLease(
            lease_id=checkpoint_lease_id,
            ocs=ocs_id,
            capability=capability,
            expires_at=now + 3600,
            actor="NÓESIS",
            issued_at=now,
            not_before=now,
            scope=("repo:reis-os-backend",),
            tenant=organization_id,
            context_ref=mission_id,
            authority_ref=profile.authority_envelope_ref,
            policy_snapshot="policy:all",
            action_binding="ocs_instance_checkpoint",
            object_ref_or_selector=mission_id,
            trace_ref=trace_ref,
            max_uses=1,
            single_use=True,
        )
    )
    transport = FakeHazelTransport()
    continuity = HazelBoundContinuity(
        guard=identity,
        transport=transport,
    )
    binder = OCSInstanceBinder(
        store=store,
        identity_guard=identity,
        leases=leases,
        continuity=continuity,
        binding_secret=b"ten-profile-binding-secret",
    )
    request = PrepareInstanceRequest(
        mission_id=mission_id,
        organization_id=organization_id,
        ocs_id=ocs_id,
        capability=capability,
        lease_id=lease_id,
        host="ChatGPT Work",
        scope=("repo:reis-os-backend",),
        idempotency_key=f"idem:{ocs_id}:prepare",
        correlation_id=f"corr:{ocs_id}",
        actor="NÓESIS",
        context_ref=mission_id,
        policy_snapshot="policy:all",
        trace_ref=trace_ref,
    )
    binding, envelope = binder.prepare(request)
    task_prefix = "".join(
        character
        for character in normalize("NFKD", ocs_id.casefold())
        if character.isascii()
    )
    bridge = WorkInstanceBridge(store)
    bridge.attach(
        binding.binding_id,
        WorkSpawnReceipt(f"work:{ocs_id}", f"{task_prefix}__mission"),
        expected_version=2,
        idempotency_key=f"idem:{ocs_id}:attach",
    )
    active = bridge.acknowledge(
        BootstrapAck(
            binding.binding_id,
            f"work:{ocs_id}",
            1,
            envelope.digest(),
            binding.identity_binding_hash,
            envelope.challenge_nonce,
            f"idem:{ocs_id}:ack",
        ),
        expected_version=3,
    )
    checkpoint = binder.checkpoint(
        active.binding_id,
        authority=replace(request, lease_id=checkpoint_lease_id),
        platform_instance_id=f"work:{ocs_id}",
        generation=1,
        expected_version=4,
        state={"ocs_id": ocs_id, "phase": "checkpoint"},
        idempotency_key=f"idem:{ocs_id}:checkpoint",
    )
    recovered = continuity.recover_state(
        run_id=checkpoint.run_id,
        expected_ocs=ocs_id,
        host="ChatGPT Work",
        authority_ref=profile.authority_envelope_ref,
    )
    assert checkpoint.maturity is BindingMaturity.OPERATIONALLY_BOUND_L1
    assert recovered["state_version"] == 2
    assert recovered["payload"]["generation"] == 1


def test_shared_store_rejects_all_directional_cross_ocs_lineages(
    tmp_path: Path,
) -> None:
    from app.ocs_instances.contracts import stable_run_id

    store = InstanceBindingStore(tmp_path / "shared-instances.sqlite3")
    bindings: dict[str, InstanceBinding] = {}
    for index, ocs_id in enumerate(PROFILES, start=1):
        mission_id = f"mission:shared:{ocs_id}"
        binding = replace(
            make_binding(
                binding_id=f"binding:shared:{ocs_id}",
                idempotency_key=f"idem:shared:{ocs_id}",
            ),
            mission_id=mission_id,
            run_id=stable_run_id("REIS OS", "org:shared", mission_id, ocs_id),
            organization_id="org:shared",
            ocs_id=ocs_id,
            generation=1,
        )
        bindings[ocs_id] = store.create(binding)
    denied = 0
    for predecessor_ocs, predecessor in bindings.items():
        for successor_ocs in PROFILES:
            if successor_ocs == predecessor_ocs:
                continue
            with pytest.raises(
                InstanceBindingError, match="replacement_lineage_mismatch"
            ):
                store.create(
                    replace(
                        predecessor,
                        binding_id=(
                            f"binding:cross:{predecessor_ocs}:{successor_ocs}"
                        ),
                        ocs_id=successor_ocs,
                        generation=2,
                        predecessor_binding_id=predecessor.binding_id,
                        idempotency_key=(
                            f"idem:cross:{predecessor_ocs}:{successor_ocs}"
                        ),
                    )
                )
            denied += 1
    assert denied == 90
    for ocs_id, predecessor in bindings.items():
        with pytest.raises(
            InstanceBindingError, match="replacement_lineage_mismatch"
        ):
            store.create(
                replace(
                    predecessor,
                    binding_id=f"binding:cross-org:{ocs_id}",
                    organization_id="org:other",
                    generation=2,
                    predecessor_binding_id=predecessor.binding_id,
                    idempotency_key=f"idem:cross-org:{ocs_id}",
                )
            )


def test_action_saga_survives_restart_at_every_boundary(tmp_path: Path) -> None:
    path = tmp_path / "saga.sqlite3"
    store = InstanceBindingStore(path)
    binding = store.create(make_binding())
    saga = store.begin_action_saga(
        idempotency_key="idem:saga:1",
        binding_id=binding.binding_id,
        operation="ocs_instance_checkpoint",
        request_fingerprint="fingerprint:1",
        payload={"lease_id": binding.lease_id},
    )
    assert saga["state"] == "LEASE_RESERVED"
    states = (
        "EFFECT_APPLIED",
        "READBACK_VERIFIED",
        "LOCAL_COMMITTED",
        "LEASE_FINALIZED",
    )
    previous = "LEASE_RESERVED"
    for target in states:
        restarted = InstanceBindingStore(path)
        saga = restarted.advance_action_saga(
            "idem:saga:1", expected_state=previous, target_state=target
        )
        assert saga["state"] == target
        previous = target
    final = InstanceBindingStore(path).action_saga("idem:saga:1")
    assert final["state"] == "LEASE_FINALIZED"


@pytest.mark.parametrize(
    "boundary",
    (
        "EFFECT_APPLIED",
        "READBACK_VERIFIED",
        "LOCAL_COMMITTED",
        "LEASE_FINALIZED",
    ),
)
def test_checkpoint_fault_boundaries_retry_without_duplicate_hazel(
    tmp_path: Path, boundary: str
) -> None:
    store = FaultInjectingStore(tmp_path / "instances.sqlite3")
    binder, _, transport = build_binder(tmp_path, store=store)
    binding, envelope = binder.prepare(prepare_request())
    bridge = WorkInstanceBridge(store)
    bridge.attach(
        binding.binding_id,
        WorkSpawnReceipt("work:1", "sofia__fault"),
        expected_version=2,
        idempotency_key="idem:fault:attach",
    )
    active = bridge.acknowledge(
        BootstrapAck(
            binding.binding_id,
            "work:1",
            1,
            envelope.digest(),
            binding.identity_binding_hash,
            envelope.challenge_nonce,
            "idem:fault:ack",
        ),
        expected_version=3,
    )
    authority = replace(
        prepare_request(), lease_id="lease:sofia:checkpoint:1"
    )
    store.fail_after_state = boundary
    with pytest.raises(RuntimeError, match="injected_crash_after"):
        binder.checkpoint(
            active.binding_id,
            authority=authority,
            platform_instance_id="work:1",
            generation=1,
            expected_version=4,
            state={"fault_boundary": boundary},
            idempotency_key=f"idem:fault:{boundary}",
        )
    writes = transport.persist_calls
    snapshots = AuthenticatedLeaseSnapshotStore(
        tmp_path / "fault-leases.json", b"fault-snapshot-key"
    )
    snapshots.save(binder._leases)
    restarted_store = FaultInjectingStore(tmp_path / "instances.sqlite3")
    restarted_store.failure_emitted = True
    restarted = OCSInstanceBinder(
        store=restarted_store,
        identity_guard=binder._identity_guard,
        leases=snapshots.load(),
        continuity=binder._continuity,
        binding_secret=b"test-binding-secret",
    )
    recovered = restarted.checkpoint(
        active.binding_id,
        authority=authority,
        platform_instance_id="work:1",
        generation=1,
        expected_version=4,
        state={"fault_boundary": boundary},
        idempotency_key=f"idem:fault:{boundary}",
    )
    assert recovered.status is InstanceStatus.CHECKPOINTED
    assert transport.persist_calls == writes
    assert restarted_store.action_saga(f"idem:fault:{boundary}")["state"] == (
        "LEASE_FINALIZED"
    )


@pytest.mark.parametrize(
    "boundary",
    (
        "EFFECT_APPLIED",
        "READBACK_VERIFIED",
        "LOCAL_COMMITTED",
        "LEASE_FINALIZED",
    ),
)
def test_replacement_fault_boundaries_retry_without_duplicate_hazel(
    tmp_path: Path, boundary: str
) -> None:
    store = FaultInjectingStore(tmp_path / "instances.sqlite3")
    binder, _, transport = build_binder(tmp_path, store=store)
    binding, envelope = binder.prepare(prepare_request())
    bridge = WorkInstanceBridge(store)
    bridge.attach(
        binding.binding_id,
        WorkSpawnReceipt("work:1", "sofia__replacement-fault"),
        expected_version=2,
        idempotency_key="idem:replacement-fault:attach",
    )
    active = bridge.acknowledge(
        BootstrapAck(
            binding.binding_id,
            "work:1",
            1,
            envelope.digest(),
            binding.identity_binding_hash,
            envelope.challenge_nonce,
            "idem:replacement-fault:ack",
        ),
        expected_version=3,
    )
    checkpoint = binder.checkpoint(
        active.binding_id,
        authority=replace(
            prepare_request(), lease_id="lease:sofia:checkpoint:1"
        ),
        platform_instance_id="work:1",
        generation=1,
        expected_version=4,
        state={"ready": True},
        idempotency_key="idem:replacement-fault:checkpoint",
    )
    request = replace(
        prepare_request(),
        lease_id="lease:sofia:2",
        idempotency_key="idem:replacement-fault:prepare",
        correlation_id="corr:replacement-fault",
        causation_id=checkpoint.hazel_event_hash,
    )
    store.fail_after_state = boundary
    replacement_idempotency = f"idem:replacement-fault:{boundary}"
    with pytest.raises(RuntimeError, match="injected_crash_after"):
        binder.replace_instance(
            checkpoint.binding_id,
            request,
            platform_instance_id="work:1",
            generation=1,
            expected_version=5,
            replacement_idempotency_key=replacement_idempotency,
        )
    writes = transport.persist_calls
    snapshots = AuthenticatedLeaseSnapshotStore(
        tmp_path / "replacement-leases.json", b"replacement-snapshot-key"
    )
    snapshots.save(binder._leases)
    restarted_store = FaultInjectingStore(tmp_path / "instances.sqlite3")
    restarted_store.failure_emitted = True
    restarted = OCSInstanceBinder(
        store=restarted_store,
        identity_guard=binder._identity_guard,
        leases=snapshots.load(),
        continuity=binder._continuity,
        binding_secret=b"test-binding-secret",
    )
    recovered, _ = restarted.replace_instance(
        checkpoint.binding_id,
        request,
        platform_instance_id="work:1",
        generation=1,
        expected_version=5,
        replacement_idempotency_key=replacement_idempotency,
    )
    assert recovered.generation == 2
    assert transport.persist_calls == writes
    assert restarted_store.action_saga(replacement_idempotency)["state"] == (
        "LEASE_FINALIZED"
    )
