import time

import pytest

from app.distributed_runtime.causal_mission import DR5A_ORDER
from app.distributed_runtime.recovery import RecoverableElevenOCSFleet
from app.ocs_instances.contracts import BindingMaturity, InstanceBinding, InstanceStatus
from app.profile_bindings.profiles import PROFILES


def _binding(ocs_id: str, generation: int = 1) -> InstanceBinding:
    profile = PROFILES[ocs_id]
    now = time.time()
    slug = ocs_id.casefold()
    return InstanceBinding(
        binding_id=f"binding:{slug}:dr6",
        mission_id="mission:dr6-recovery",
        run_id=f"run:{slug}:dr6",
        organization_id="reis-os",
        ocs_id=ocs_id,
        profile_version=profile.version,
        profile_hash=f"profile-hash:{slug}",
        identity_binding_hash=f"identity-binding:{slug}",
        request_hash=f"request:{slug}",
        maturity=BindingMaturity.OPERATIONALLY_BOUND_L1,
        host="dr6-provider-independent",
        capability="cognitive-runtime",
        lease_id=f"lease:{slug}:dr6",
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
        idempotency_key=f"idem:{slug}:dr6",
        correlation_id="corr:dr6",
        causation_id=None,
        created_at=now,
        updated_at=now,
    )


def _fleet() -> RecoverableElevenOCSFleet:
    return RecoverableElevenOCSFleet({ocs_id: _binding(ocs_id) for ocs_id in DR5A_ORDER})


def test_dr6_midflight_failure_restarts_only_failed_actor_and_completes_mission():
    fleet = _fleet()
    try:
        fleet.start()
        before = fleet.health_instance_ids()
        result = fleet.execute_with_midflight_recovery(
            {"goal": "recover distributed mission"},
            failed_ocs="DÉDALA",
            mission_id="mission:dr6:midflight",
        )
        after = fleet.health_instance_ids()
        assert len(result.receipts) == 11
        assert set(result.final_payload["contributions"]) == set(DR5A_ORDER)
        assert before["DÉDALA"] != after["DÉDALA"]
        for ocs_id in DR5A_ORDER:
            if ocs_id != "DÉDALA":
                assert before[ocs_id] == after[ocs_id]
    finally:
        fleet.stop_all()


def test_dr6_generation_advances_exactly_once_and_old_generation_is_fenced():
    fleet = _fleet()
    try:
        fleet.start()
        result = fleet.execute_with_midflight_recovery(
            {"goal": "generation fencing"},
            failed_ocs="DÉDALA",
        )
        event = result.recovery
        assert event.old_generation == 1
        assert event.new_generation == 2
        fleet.assert_commit_allowed("DÉDALA", 2)
        with pytest.raises(PermissionError, match="dr6_stale_generation_fenced"):
            fleet.assert_commit_allowed("DÉDALA", 1)
    finally:
        fleet.stop_all()


def test_dr6_rebind_preserves_identity_authority_profile_and_namespaces():
    fleet = _fleet()
    try:
        fleet.start()
        result = fleet.execute_with_midflight_recovery(
            {"goal": "binding preservation"},
            failed_ocs="ÁGORA",
        )
        event = result.recovery
        assert event.identity_preserved
        assert event.authority_preserved
        assert event.profile_preserved
        assert event.state_namespace_preserved
        assert event.memory_namespace_preserved
        assert event.old_instance_id != event.new_instance_id
    finally:
        fleet.stop_all()


def test_dr6_safe_replay_keeps_same_message_identity_without_double_contribution():
    fleet = _fleet()
    try:
        fleet.start()
        result = fleet.execute_with_midflight_recovery(
            {"goal": "safe replay"},
            failed_ocs="SOFIA",
        )
        sofia_receipts = [r for r in result.receipts if r.target_ocs == "SOFIA"]
        assert len(sofia_receipts) == 1
        assert sofia_receipts[0].message_id == result.recovery.replayed_message_id
        assert list(result.final_payload["contributions"]).count("SOFIA") == 1
    finally:
        fleet.stop_all()


def test_dr6_causal_chain_survives_restart_without_trace_or_correlation_break():
    fleet = _fleet()
    try:
        fleet.start()
        result = fleet.execute_with_midflight_recovery(
            {"goal": "causal continuity"},
            failed_ocs="MÊTIS",
        )
        assert {r.trace_id for r in result.receipts} == {result.trace_id}
        assert {r.correlation_id for r in result.receipts} == {result.correlation_id}
        for previous, current in zip(result.receipts, result.receipts[1:]):
            assert current.input_payload_hash == previous.output_payload_hash
    finally:
        fleet.stop_all()


def test_dr6_can_recover_each_canonical_actor_independently():
    for failed_ocs in DR5A_ORDER:
        fleet = _fleet()
        try:
            fleet.start()
            result = fleet.execute_with_midflight_recovery(
                {"goal": f"recover {failed_ocs}"},
                failed_ocs=failed_ocs,
                mission_id=f"mission:dr6:{failed_ocs}",
            )
            assert result.recovery.ocs_id == failed_ocs
            assert result.recovery.new_generation == 2
            assert len(result.receipts) == 11
        finally:
            fleet.stop_all()
