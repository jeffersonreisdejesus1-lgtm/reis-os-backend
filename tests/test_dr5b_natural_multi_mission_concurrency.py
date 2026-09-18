import time

import pytest

from app.distributed_runtime.causal_mission import DR5A_ORDER
from app.distributed_runtime.concurrent_missions import SharedElevenOCSMissionFleet
from app.ocs_instances.contracts import BindingMaturity, InstanceBinding, InstanceStatus
from app.profile_bindings.profiles import PROFILES


def _binding(ocs_id: str, generation: int = 1) -> InstanceBinding:
    profile = PROFILES[ocs_id]
    now = time.time()
    slug = ocs_id.casefold()
    return InstanceBinding(
        binding_id=f"binding:{slug}:dr5b",
        mission_id="mission:dr5b-shared-fleet",
        run_id=f"run:{slug}:dr5b",
        organization_id="reis-os",
        ocs_id=ocs_id,
        profile_version=profile.version,
        profile_hash=f"profile-hash:{slug}",
        identity_binding_hash=f"identity-binding:{slug}",
        request_hash=f"request:{slug}",
        maturity=BindingMaturity.OPERATIONALLY_BOUND_L1,
        host="dr5b-provider-independent",
        capability="cognitive-runtime",
        lease_id=f"lease:{slug}:dr5b",
        authority_ref=profile.authority_envelope_ref,
        scope=("cognition", "handoff", "evidence"),
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
        idempotency_key=f"idem:{slug}:dr5b",
        correlation_id="corr:dr5b",
        causation_id=None,
        created_at=now,
        updated_at=now,
    )


def _fleet(max_inflight: int = 4) -> SharedElevenOCSMissionFleet:
    bindings = {ocs_id: _binding(ocs_id) for ocs_id in DR5A_ORDER}
    return SharedElevenOCSMissionFleet(bindings, max_inflight_missions=max_inflight)


def test_dr5b_shared_fleet_completes_multiple_concurrent_missions():
    fleet = _fleet(4)
    try:
        fleet.start()
        results = fleet.execute_many([
            ("mission:a", {"goal": "alpha"}),
            ("mission:b", {"goal": "beta"}),
            ("mission:c", {"goal": "gamma"}),
            ("mission:d", {"goal": "delta"}),
        ])
        assert len(results) == 4
        assert {r.mission_id for r in results} == {"mission:a", "mission:b", "mission:c", "mission:d"}
        assert all(len(r.receipts) == 11 for r in results)
        assert fleet.max_observed_active_missions >= 2
    finally:
        fleet.stop_all()


def test_dr5b_keeps_trace_and_correlation_isolated_per_mission():
    fleet = _fleet(3)
    try:
        fleet.start()
        results = fleet.execute_many([
            ("mission:a", {"goal": "a"}),
            ("mission:b", {"goal": "b"}),
            ("mission:c", {"goal": "c"}),
        ])
        assert len({r.trace_id for r in results}) == 3
        assert len({r.correlation_id for r in results}) == 3
        for result in results:
            assert {receipt.trace_id for receipt in result.receipts} == {result.trace_id}
            assert {receipt.correlation_id for receipt in result.receipts} == {result.correlation_id}
            assert {receipt.mission_id for receipt in result.receipts} == {result.mission_id}
    finally:
        fleet.stop_all()


def test_dr5b_payloads_do_not_cross_contaminate_between_missions():
    fleet = _fleet(2)
    try:
        fleet.start()
        results = fleet.execute_many([
            ("mission:red", {"goal": "red", "marker": "RED_ONLY"}),
            ("mission:blue", {"goal": "blue", "marker": "BLUE_ONLY"}),
        ])
        by_id = {r.mission_id: r for r in results}
        assert by_id["mission:red"].final_payload["marker"] == "RED_ONLY"
        assert by_id["mission:blue"].final_payload["marker"] == "BLUE_ONLY"
        assert "BLUE_ONLY" not in str(by_id["mission:red"].final_payload)
        assert "RED_ONLY" not in str(by_id["mission:blue"].final_payload)
    finally:
        fleet.stop_all()


def test_dr5b_each_mission_preserves_all_eleven_specialty_contributions():
    fleet = _fleet(3)
    try:
        fleet.start()
        results = fleet.execute_many([
            (f"mission:{i}", {"goal": f"goal-{i}"}) for i in range(3)
        ])
        for result in results:
            contributions = result.final_payload["contributions"]
            assert set(contributions) == set(DR5A_ORDER)
            assert len(contributions) == 11
    finally:
        fleet.stop_all()


def test_dr5b_reuses_same_material_workers_across_missions():
    fleet = _fleet(2)
    try:
        fleet.start()
        results = fleet.execute_many([
            ("mission:a", {"goal": "a"}),
            ("mission:b", {"goal": "b"}),
        ])
        for hop in range(11):
            assert results[0].receipts[hop].target_instance_id == results[1].receipts[hop].target_instance_id
    finally:
        fleet.stop_all()


def test_dr5b_backpressure_rejects_above_inflight_limit():
    fleet = _fleet(2)
    try:
        fleet.start()
        assert fleet._admission.acquire(blocking=False)
        assert fleet._admission.acquire(blocking=False)
        with pytest.raises(RuntimeError, match="dr5b_backpressure_inflight_limit"):
            fleet.execute_mission({"goal": "rejected"}, mission_id="mission:overflow")
        fleet._admission.release()
        fleet._admission.release()
    finally:
        fleet.stop_all()


def test_dr5b_rejects_duplicate_mission_ids_before_execution():
    fleet = _fleet(2)
    try:
        fleet.start()
        with pytest.raises(ValueError, match="dr5b_mission_ids_must_be_unique"):
            fleet.execute_many([
                ("mission:dup", {"goal": "a"}),
                ("mission:dup", {"goal": "b"}),
            ])
    finally:
        fleet.stop_all()
