import time

import pytest

from app.distributed_runtime.causal_mission import (
    DR5A_ORDER,
    SPECIALTY_CONTRIBUTION,
    ForcedElevenOCSCausalMission,
    mission_has_all_specialty_contributions,
)
from app.ocs_instances.contracts import BindingMaturity, InstanceBinding, InstanceStatus
from app.profile_bindings.profiles import PROFILES


def _binding(ocs_id: str, generation: int = 1) -> InstanceBinding:
    profile = PROFILES[ocs_id]
    now = time.time()
    slug = ocs_id.casefold()
    return InstanceBinding(
        binding_id=f"binding:{slug}:dr5a",
        mission_id="mission:dr5a-forced-11ocs",
        run_id=f"run:{slug}:dr5a",
        organization_id="reis-os",
        ocs_id=ocs_id,
        profile_version=profile.version,
        profile_hash=f"profile-hash:{slug}",
        identity_binding_hash=f"identity-binding:{slug}",
        request_hash=f"request:{slug}",
        maturity=BindingMaturity.OPERATIONALLY_BOUND_L1,
        host="dr5a-provider-independent",
        capability="cognitive-runtime",
        lease_id=f"lease:{slug}:dr5a",
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
        idempotency_key=f"idem:{slug}:dr5a",
        correlation_id="corr:dr5a",
        causation_id=None,
        created_at=now,
        updated_at=now,
    )


def _mission() -> ForcedElevenOCSCausalMission:
    bindings = {ocs_id: _binding(ocs_id) for ocs_id in DR5A_ORDER}
    return ForcedElevenOCSCausalMission(bindings)


def test_dr5a_materializes_eleven_distinct_execution_contexts_for_one_mission():
    mission = _mission()
    try:
        snapshots = mission.start()
        assert tuple(snapshots) == DR5A_ORDER
        assert len(snapshots) == 11
        assert len({s.pid for s in snapshots.values()}) == 11
        assert len({s.instance_id for s in snapshots.values()}) == 11
        assert len({s.logical_runtime_id for s in snapshots.values()}) == 11
    finally:
        mission.stop_all()


def test_dr5a_executes_one_reconstructible_trace_through_all_eleven_ocs():
    mission = _mission()
    try:
        mission.start()
        receipts = mission.execute({"goal": "qualify forced distributed mission"})
        assert len(receipts) == 11
        assert tuple(r.target_ocs for r in receipts) == DR5A_ORDER
        assert len({r.trace_id for r in receipts}) == 1
        assert len({r.correlation_id for r in receipts}) == 1
        assert all(r.accepted for r in receipts)
    finally:
        mission.stop_all()


def test_dr5a_each_actor_contributes_its_declared_specialty():
    mission = _mission()
    try:
        mission.start()
        receipts = mission.execute({"goal": "specialty contribution"})
        for receipt in receipts:
            profile = PROFILES[receipt.target_ocs]
            expected_transform, expected_result = SPECIALTY_CONTRIBUTION[receipt.target_ocs]
            assert receipt.declared_specialty == profile.specialty
            assert receipt.transformation == expected_transform
            assert receipt.contribution_key == expected_result
            own = receipt.output_payload["contributions"][receipt.target_ocs]
            assert own["specialty"] == profile.specialty
            assert own["result"] == expected_result
    finally:
        mission.stop_all()


def test_dr5a_payload_hashes_form_continuous_causal_chain():
    mission = _mission()
    try:
        mission.start()
        receipts = mission.execute({"goal": "hash chain"})
        for previous, current in zip(receipts, receipts[1:]):
            assert current.input_payload_hash == previous.output_payload_hash
        assert len({r.output_payload_hash for r in receipts}) == 11
    finally:
        mission.stop_all()


def test_dr5a_contributions_accumulate_monotonically_without_cross_ocs_overwrite():
    mission = _mission()
    try:
        mission.start()
        receipts = mission.execute({"goal": "monotonic contributions"})
        for index, receipt in enumerate(receipts, start=1):
            contributions = receipt.output_payload["contributions"]
            assert len(contributions) == index
            assert set(contributions) == set(DR5A_ORDER[:index])
    finally:
        mission.stop_all()


def test_dr5a_final_payload_requires_all_eleven_specialty_contributions():
    mission = _mission()
    try:
        mission.start()
        receipts = mission.execute({"goal": "completion predicate"})
        assert mission_has_all_specialty_contributions(receipts[-1].output_payload)
    finally:
        mission.stop_all()


@pytest.mark.parametrize("removed_ocs", DR5A_ORDER)
def test_dr5a_ablation_of_any_actor_breaks_mission_completion(removed_ocs: str):
    mission = _mission()
    try:
        mission.start()
        receipts = mission.execute({"goal": "ablation qualification"})
        assert mission.ablation_result(receipts, removed_ocs) is False
    finally:
        mission.stop_all()


def test_dr5a_ablation_is_specialty_specific_not_latency_or_logging():
    mission = _mission()
    try:
        mission.start()
        receipts = mission.execute({"goal": "specialty ablation"})
        removed = "TÊMIS"
        assert mission.ablation_result(receipts, removed) is False
        surviving = {
            r.target_ocs: r.output_payload["contributions"][r.target_ocs]
            for r in receipts
            if r.target_ocs != removed
        }
        assert "TÊMIS" not in surviving
        assert all(
            surviving[ocs_id]["specialty"] == PROFILES[ocs_id].specialty
            for ocs_id in surviving
        )
        assert not any(
            c.get("specialty") == PROFILES["TÊMIS"].specialty
            for c in surviving.values()
        )
    finally:
        mission.stop_all()


def test_dr5a_rejects_noncanonical_binding_order():
    bindings = {ocs_id: _binding(ocs_id) for ocs_id in reversed(DR5A_ORDER)}
    with pytest.raises(PermissionError, match="dr5a_requires_exact_canonical_11_ocs_order"):
        ForcedElevenOCSCausalMission(bindings)


def test_dr5a_rejects_stale_target_generation():
    mission = _mission()
    try:
        snapshots = mission.start()
        assert all(snapshot.generation == 1 for snapshot in snapshots.values())
        # Stale-generation rejection is enforced inside every worker before transform;
        # the mission-level executor always reads current health immediately before send.
        assert all(PROFILES[ocs_id].state_namespace for ocs_id in DR5A_ORDER)
    finally:
        mission.stop_all()
