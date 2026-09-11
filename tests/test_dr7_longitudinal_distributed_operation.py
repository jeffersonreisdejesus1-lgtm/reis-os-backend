import time

import pytest

from app.distributed_runtime.causal_mission import DR5A_ORDER
from app.distributed_runtime.longitudinal import LongitudinalDistributedOperation
from app.ocs_instances.contracts import BindingMaturity, InstanceBinding, InstanceStatus
from app.profile_bindings.profiles import PROFILES


def _binding(ocs_id: str) -> InstanceBinding:
    profile = PROFILES[ocs_id]
    now = time.time()
    slug = ocs_id.casefold()
    return InstanceBinding(
        binding_id=f"binding:{slug}:dr7",
        mission_id="mission:dr7-longitudinal",
        run_id=f"run:{slug}:dr7",
        organization_id="reis-os",
        ocs_id=ocs_id,
        profile_version=profile.version,
        profile_hash=f"profile-hash:{slug}",
        identity_binding_hash=f"identity-binding:{slug}",
        request_hash=f"request:{slug}",
        maturity=BindingMaturity.OPERATIONALLY_BOUND_L1,
        host="dr7-provider-independent",
        capability="cognitive-runtime",
        lease_id=f"lease:{slug}:dr7",
        authority_ref=profile.authority_envelope_ref,
        scope=("cognition", "handoff", "evidence"),
        state_namespace=profile.state_namespace,
        memory_namespace=profile.memory_namespace,
        generation=1,
        platform_instance_id=None,
        challenge_hash=f"challenge:{slug}",
        bootstrap_hash=f"bootstrap:{slug}",
        status=InstanceStatus.ACTIVE,
        version=1,
        predecessor_binding_id=None,
        checkpoint_version=0,
        checkpoint_hash=None,
        hazel_event_hash=None,
        idempotency_key=f"idem:{slug}:dr7",
        correlation_id="corr:dr7",
        causation_id=None,
        created_at=now,
        updated_at=now,
    )


def _runtime() -> LongitudinalDistributedOperation:
    return LongitudinalDistributedOperation({ocs_id: _binding(ocs_id) for ocs_id in DR5A_ORDER})


def test_dr7_runs_twenty_two_cycles_with_two_recoveries_per_ocs():
    runtime = _runtime()
    try:
        runtime.start()
        result = runtime.execute_cycles(DR5A_ORDER + DR5A_ORDER)
        assert result.completed is True
        assert len(result.cycles) == 22
        assert len(set(result.mission_ids)) == 22
        assert len(set(result.trace_ids)) == 22
        assert len(set(result.correlation_ids)) == 22
        assert result.final_generations == {ocs_id: 3 for ocs_id in DR5A_ORDER}
    finally:
        runtime.stop()


def test_dr7_every_cycle_preserves_bindings_and_causal_reconstruction():
    runtime = _runtime()
    try:
        runtime.start()
        result = runtime.execute_cycles(DR5A_ORDER)
        for cycle in result.cycles:
            assert cycle.identity_binding_stable is True
            assert cycle.authority_binding_stable is True
            assert cycle.profile_binding_stable is True
            assert cycle.state_namespace_stable is True
            assert cycle.memory_namespace_stable is True
            assert cycle.causal_reconstruction_valid is True
            assert cycle.mission_isolation_valid is True
            assert cycle.receipt_count == 11
            assert cycle.contribution_count == 11
    finally:
        runtime.stop()


def test_dr7_generations_advance_only_for_scheduled_recoveries():
    runtime = _runtime()
    try:
        runtime.start()
        schedule = tuple(DR5A_ORDER) + ("NÓESIS", "NÓESIS", "DÉDALA")
        result = runtime.execute_cycles(schedule)
        expected = {ocs_id: 2 for ocs_id in DR5A_ORDER}
        expected["NÓESIS"] = 4
        expected["DÉDALA"] = 3
        assert result.final_generations == expected
    finally:
        runtime.stop()


def test_dr7_rejects_too_short_longitudinal_window():
    runtime = _runtime()
    try:
        runtime.start()
        with pytest.raises(ValueError, match="dr7_requires_at_least_eleven_longitudinal_cycles"):
            runtime.execute_cycles(DR5A_ORDER[:10])
    finally:
        runtime.stop()


def test_dr7_rejects_unknown_failure_target():
    runtime = _runtime()
    try:
        runtime.start()
        with pytest.raises(ValueError, match="dr7_unknown_failure_target"):
            runtime.execute_cycles(tuple(DR5A_ORDER[:-1]) + ("UNKNOWN",))
    finally:
        runtime.stop()
