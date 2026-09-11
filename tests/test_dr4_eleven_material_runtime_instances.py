import time

from app.distributed_runtime.fleet import DR4_OCS_ORDER, ElevenOCSFleet
from app.ocs_instances.contracts import BindingMaturity, InstanceBinding, InstanceStatus
from app.profile_bindings.profiles import PROFILES


def _binding(ocs_id: str, generation: int = 1) -> InstanceBinding:
    profile = PROFILES[ocs_id]
    now = time.time()
    slug = ocs_id.casefold()
    return InstanceBinding(
        binding_id=f"binding:{slug}:dr4",
        mission_id="mission:dr4-eleven-material-runtimes",
        run_id=f"run:{slug}:dr4",
        organization_id="reis-os",
        ocs_id=ocs_id,
        profile_version=profile.version,
        profile_hash=f"profile-hash:{slug}",
        identity_binding_hash=f"identity-binding:{slug}",
        request_hash=f"request:{slug}",
        maturity=BindingMaturity.OPERATIONALLY_BOUND_L1,
        host="dr4-provider-independent",
        capability="cognitive-runtime",
        lease_id=f"lease:{slug}:dr4",
        authority_ref=profile.authority_envelope_ref,
        scope=("cognition", "health", "checkpoint"),
        state_namespace=profile.state_namespace,
        memory_namespace=profile.memory_namespace,
        generation=generation,
        platform_instance_id=None,
        challenge_hash=f"challenge:{slug}",
        bootstrap_hash=f"bootstrap:{slug}",
        status=InstanceStatus.ACTIVE,
        version=1,
        predecessor_binding_id=None,
        checkpoint_version=0,
        checkpoint_hash=None,
        hazel_event_hash=None,
        idempotency_key=f"idem:{slug}:dr4",
        correlation_id="corr:dr4",
        causation_id=None,
        created_at=now,
        updated_at=now,
    )


def _fleet() -> ElevenOCSFleet:
    bindings = {ocs_id: _binding(ocs_id) for ocs_id in DR4_OCS_ORDER}
    return ElevenOCSFleet(bindings)


def test_dr4_materializes_exactly_eleven_canonical_ocs_workers():
    fleet = _fleet()
    try:
        snapshots = fleet.start_all()
        assert tuple(snapshots.keys()) == DR4_OCS_ORDER
        assert len(snapshots) == 11
        assert all(snapshot.ocs_id == ocs_id for ocs_id, snapshot in snapshots.items())
    finally:
        fleet.stop_all()


def test_dr4_has_eleven_distinct_execution_and_failure_contexts():
    fleet = _fleet()
    try:
        snapshots = fleet.start_all()
        assert len({s.pid for s in snapshots.values()}) == 11
        assert len({s.execution_context_id for s in snapshots.values()}) == 11
        assert len({s.failure_domain_id for s in snapshots.values()}) == 11
        assert len({s.instance_id for s in snapshots.values()}) == 11
        assert len({s.logical_runtime_id for s in snapshots.values()}) == 11
    finally:
        fleet.stop_all()


def test_dr4_preserves_state_memory_and_authority_binding_per_ocs():
    fleet = _fleet()
    try:
        snapshots = fleet.start_all()
        assert len({s.state_namespace for s in snapshots.values()}) == 11
        assert len({s.memory_namespace for s in snapshots.values()}) == 11
        for ocs_id, snapshot in snapshots.items():
            profile = PROFILES[ocs_id]
            assert snapshot.state_namespace == profile.state_namespace
            assert snapshot.memory_namespace == profile.memory_namespace
            assert snapshot.authority_ref == profile.authority_envelope_ref
            assert snapshot.generation == 1
    finally:
        fleet.stop_all()


def test_dr4_all_lifecycles_are_independently_active_and_healthy():
    fleet = _fleet()
    try:
        fleet.start_all()
        health = fleet.health_all()
        assert len(health) == 11
        assert all(snapshot.lifecycle_state.value == "active" for snapshot in health.values())
        assert all(snapshot.monotonic_sequence >= 2 for snapshot in health.values())
    finally:
        fleet.stop_all()


def test_dr4_checkpoints_are_local_to_each_worker():
    fleet = _fleet()
    try:
        fleet.start_all()
        checkpoints = fleet.checkpoint_all()
        assert len(checkpoints) == 11
        for ocs_id, checkpoint in checkpoints.items():
            assert checkpoint["ocs_id"] == ocs_id
            assert checkpoint["state_namespace"] == PROFILES[ocs_id].state_namespace
            assert checkpoint["memory_namespace"] == PROFILES[ocs_id].memory_namespace
            assert checkpoint["authority_ref"] == PROFILES[ocs_id].authority_envelope_ref
            assert checkpoint["generation"] == 1
    finally:
        fleet.stop_all()


def test_dr4_kill_one_preserves_other_ten_workers():
    fleet = _fleet()
    try:
        fleet.start_all()
        fleet.kill_one("DÉDALA")
        health = fleet.peer_health_after_kill("DÉDALA")
        assert len(health) == 10
        assert "DÉDALA" not in health
        assert all(snapshot.lifecycle_state.value == "active" for snapshot in health.values())
    finally:
        fleet.stop_all()


def test_dr4_rejects_incomplete_binding_set():
    bindings = {ocs_id: _binding(ocs_id) for ocs_id in DR4_OCS_ORDER[:-1]}
    try:
        ElevenOCSFleet(bindings)
        assert False, "incomplete fleet must be rejected"
    except PermissionError as exc:
        assert "dr4_requires" in str(exc)
