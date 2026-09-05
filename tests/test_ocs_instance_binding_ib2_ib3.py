from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from time import time
import pytest

from app.ocs_instances.contracts import (
    BootstrapAck,
    InstanceBinding,
    InstanceBindingError,
    InstanceStatus,
    PrepareInstanceRequest,
)
from app.ocs_instances.service import OCSInstanceBinder
from app.ocs_instances.store import InstanceBindingStore
from app.ocs_instances.work_bridge import WorkInstanceBridge, WorkSpawnReceipt
from app.profile_bindings.profiles import PROFILES
from app.universal_kernel.governance import AuthorityLease, AuthorityLeaseManager
from app.universal_kernel.hazel_continuity import HazelBoundContinuity
from app.universal_kernel.identity import IdentityAuditLog, IdentityKernelGuard


class FakeHazelTransport:
    def __init__(self) -> None:
        self.latest: dict[tuple[str, str, str], dict[str, object]] = {}
        self.persist_calls = 0

    @staticmethod
    def _hash(value: dict[str, object]) -> str:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        return sha256(encoded).hexdigest()

    def persist(self, envelope: dict[str, object]) -> dict[str, object]:
        self.persist_calls += 1
        key = (
            str(envelope["run_id"]),
            str(envelope["ocs_id"]),
            str(envelope["state_namespace"]),
        )
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

    def recover(self, request: dict[str, object]) -> dict[str, object]:
        key = (
            str(request["run_id"]),
            str(request["ocs_id"]),
            str(request["state_namespace"]),
        )
        return dict(self.latest[key])


def make_binding(
    *,
    binding_id: str = "binding:1",
    idempotency_key: str = "idem:prepare:1",
) -> InstanceBinding:
    return InstanceBinding(
        binding_id=binding_id,
        mission_id="mission:1",
        run_id="mission:1:SOFIA",
        organization_id="org:reis-os",
        ocs_id="SOFIA",
        profile_version="r2-v0.1.0",
        profile_hash="profile-hash",
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
        idempotency_key=idempotency_key,
        correlation_id="correlation:1",
        causation_id=None,
        created_at=1.0,
        updated_at=1.0,
    )


def build_binder(
    tmp_path: Path,
) -> tuple[OCSInstanceBinder, InstanceBindingStore, FakeHazelTransport]:
    store = InstanceBindingStore(tmp_path / "instances.sqlite3")
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
            max_uses=2,
        )
    )
    transport = FakeHazelTransport()
    continuity = HazelBoundContinuity(guard=identity, transport=transport)
    binder = OCSInstanceBinder(
        store=store,
        identity_guard=identity,
        leases=leases,
        continuity=continuity,
        nonce_factory=lambda: "challenge-nonce",
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
    )


def test_registry_survives_restart_and_journals_prepare(tmp_path: Path) -> None:
    path = tmp_path / "instances.sqlite3"
    first = InstanceBindingStore(path)
    binding = make_binding()
    first.create(binding)

    restarted = InstanceBindingStore(path)

    assert restarted.get(binding.binding_id) == binding
    assert restarted.latest_generation("mission:1", "SOFIA") == 1
    journal = restarted.journal(binding.binding_id)
    assert len(journal) == 1
    assert journal[0]["event_type"] == "OCS_INSTANCE_PREPARED"


def test_registry_cas_rejects_stale_writer(tmp_path: Path) -> None:
    store = InstanceBindingStore(tmp_path / "instances.sqlite3")
    binding = store.create(make_binding())
    store.transition(
        binding.binding_id,
        expected_version=1,
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
            expected_version=1,
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

    assert binding.run_id == "mission:1:SOFIA"
    assert binding.profile_version == PROFILES["SOFIA"].version
    assert binding.state_namespace == PROFILES["SOFIA"].state_namespace
    assert binding.memory_namespace == PROFILES["SOFIA"].memory_namespace
    assert envelope.tool_permissions == ()
    assert binding.bootstrap_hash == envelope.digest()
    assert store.get(binding.binding_id) == binding
    assert transport.persist_calls == 1


def test_binder_rejects_non_mission_lease(tmp_path: Path) -> None:
    binder, _, _ = build_binder(tmp_path)
    from dataclasses import replace

    request = replace(prepare_request(), mission_id="mission:forged")

    with pytest.raises(ValueError, match="mission_specific_lease_required"):
        binder.prepare(request)


def test_work_bridge_requires_matching_name_and_challenge(
    tmp_path: Path,
) -> None:
    binder, store, _ = build_binder(tmp_path)
    binding, envelope = binder.prepare(prepare_request())
    bridge = WorkInstanceBridge(store)

    with pytest.raises(InstanceBindingError, match="work_task_name_ocs_mismatch"):
        bridge.attach(
            binding.binding_id,
            WorkSpawnReceipt("work:1", "agora__mission-1"),
            expected_version=1,
            idempotency_key="idem:attach:wrong",
        )

    bound = bridge.attach(
        binding.binding_id,
        WorkSpawnReceipt("work:1", "sofia__mission-1"),
        expected_version=1,
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
                challenge_nonce="wrong",
                idempotency_key="idem:ack:wrong",
            ),
            expected_version=2,
        )

    active = bridge.acknowledge(
        BootstrapAck(
            binding_id=binding.binding_id,
            platform_instance_id="work:1",
            generation=1,
            bootstrap_hash=envelope.digest(),
            challenge_nonce="challenge-nonce",
            idempotency_key="idem:ack:1",
        ),
        expected_version=2,
    )
    assert active.status is InstanceStatus.ACTIVE
    assert active.platform_instance_id == "work:1"


@pytest.mark.parametrize("ocs_id", tuple(PROFILES))
def test_stable_run_identity_is_distinct_for_all_ten_profiles(
    ocs_id: str,
) -> None:
    from app.ocs_instances.contracts import stable_run_id

    assert stable_run_id("mission:all", ocs_id) == f"mission:all:{ocs_id}"
