from __future__ import annotations

from dataclasses import replace

import pytest

from app.noesis_r7 import (
    CommunicationEnvelope,
    GovernorContract,
    GovernorFunction,
    GovernorLease,
    GovernanceCommand,
    GovernanceTask,
    R1R6IntegrationContract,
    R7ArchitecturalReadiness,
    R7GovernanceRuntime,
    R7InvariantError,
)
from app.noesis_r7.contracts import FailurePoint

MISSION = "mission:noesis:r7"
AUTH = "authority:noesis:r7:internal-governance"
SOURCE = "founder-handoff:NOESIS-TO-AGORA-R7-REFACTOR-IMPLEMENTATION-001"
TEST_DERIVATION = "synthetic-test-only:r7-governor-derivation"


def derived_readiness():
    return R7ArchitecturalReadiness(
        r7_i_taxonomy_frozen=True,
        r7_o_taxonomy_frozen=True,
        cross_taxonomy_complete=True,
        normalized_requirements_available=True,
        governor_derivation_valid=True,
        derivation_ref=TEST_DERIVATION,
    )


def governor(governor_id="governor:state", *, owned=("current_phase", "blockers"), function=GovernorFunction.STATE):
    return GovernorContract(
        governor_id=governor_id,
        function=function,
        owned_state_keys=tuple(owned),
        readable_state_keys=tuple(owned) + ("mission_id",),
        allowed_commands=("SET_STATE", "RECONCILE"),
        authority_ceiling_ref=AUTH,
    )


def lease(governor_id="governor:state", *, lease_id="lease:r7:1", generation=1):
    return GovernorLease(
        lease_id=lease_id,
        governor_id=governor_id,
        mission_id=MISSION,
        authority_ref=AUTH,
        authority_source_ref=SOURCE,
        scope=("state:noesis:r7",),
        generation=generation,
        issued_at=100.0,
        not_before=100.0,
        expires_at=500.0,
        max_uses=20,
    )


def command(*, command_id="cmd:1", governor_id="governor:state", lease_id="lease:r7:1", generation=1,
            write_set=None, idempotency_key="idem:1", expected_state_version=0,
            command_type="SET_STATE", material_effect_requested=False):
    return GovernanceCommand(
        command_id=command_id,
        mission_id=MISSION,
        governor_id=governor_id,
        generation=generation,
        lease_id=lease_id,
        authority_ref=AUTH,
        command_type=command_type,
        write_set=write_set or {"current_phase": "IMPLEMENTATION"},
        idempotency_key=idempotency_key,
        expected_state_version=expected_state_version,
        scope=("state:noesis:r7",),
        material_effect_requested=material_effect_requested,
    )


def inert_runtime():
    return R7GovernanceRuntime(
        mission_id=MISSION,
        integration=R1R6IntegrationContract.canonical(),
        initial_state={"mission_id": MISSION, "current_phase": "INTAKE"},
    )


def runtime():
    rt = R7GovernanceRuntime(
        mission_id=MISSION,
        integration=R1R6IntegrationContract.canonical(),
        initial_state={"mission_id": MISSION, "current_phase": "INTAKE"},
        architectural_readiness=derived_readiness(),
    )
    rt.register_governor(governor())
    rt.bind_lease(lease())
    return rt


def admit(rt, cmd, *, priority=1):
    rt.schedule(
        GovernanceTask(
            task_id=f"task:{cmd.command_id}",
            mission_id=MISSION,
            governor_id=cmd.governor_id,
            command_type=cmd.command_type,
            priority=priority,
            created_seq=rt._task_seq + 1,
            command_id=cmd.command_id,
        )
    )


def execute(rt, cmd, *, now=110.0):
    admit(rt, cmd)
    return rt.execute(cmd, now=now)


def test_governor_activation_is_blocked_until_taxonomic_derivation():
    rt = inert_runtime()
    assert rt.governor_activation_allowed is False
    with pytest.raises(R7InvariantError, match="PENDING_DERIVATION"):
        rt.register_governor(governor())


def test_exact_r1_r6_binding_and_complete_causal_containment_fail_closed():
    compatible = R1R6IntegrationContract.canonical()
    compatible.assert_compatible()
    assert compatible.scheduler_is_authority is False
    assert compatible.governance_may_mutate_l0 is False
    with pytest.raises(R7InvariantError, match="R7_L0_BINDING_DRIFT"):
        replace(compatible, l0_binding_hash="forged").assert_compatible()
    with pytest.raises(R7InvariantError, match="COMPLETE_R1_R6_CAUSAL_CONTAINMENT"):
        replace(compatible, r1_persists_r7_state=False).assert_compatible()
    with pytest.raises(R7InvariantError, match="COMPLETE_R1_R6_CAUSAL_CONTAINMENT"):
        replace(compatible, r2_measures_r7_progress_and_effects=False).assert_compatible()
    with pytest.raises(R7InvariantError, match="COMPLETE_R1_R6_CAUSAL_CONTAINMENT"):
        replace(compatible, r3_types_r7_transitions=False).assert_compatible()


def test_direct_execute_without_scheduler_admission_is_zero_mutation():
    rt = runtime()
    before = rt.state
    receipt = rt.execute(command(), now=110.0)
    assert receipt.reason == "COMMAND_NOT_SCHEDULED"
    assert receipt.mutation_count == 0
    assert rt.state == before


def test_scheduler_priority_is_an_admission_gate_not_authority():
    rt = runtime()
    low = command(command_id="cmd:low", idempotency_key="idem:low")
    high = command(command_id="cmd:high", idempotency_key="idem:high")
    admit(rt, low, priority=1)
    admit(rt, high, priority=10)
    denied = rt.execute(low, now=110.0)
    assert denied.reason == "COMMAND_NOT_NEXT_SCHEDULED"
    assert denied.mutation_count == 0
    accepted = rt.execute(high, now=110.0)
    assert accepted.mutation_count == 1


def test_cross_owner_write_and_material_effect_fail_closed():
    rt = runtime()
    rt.register_governor(governor("governor:evidence", owned=("evidence_refs",), function=GovernorFunction.EVIDENCE))
    rt.bind_lease(lease("governor:evidence", lease_id="lease:evidence"))
    cross = command(
        command_id="cmd:cross",
        governor_id="governor:evidence",
        lease_id="lease:evidence",
        idempotency_key="idem:cross",
        write_set={"current_phase": "FORGED"},
    )
    receipt = execute(rt, cross)
    assert receipt.reason == "STATE_OWNERSHIP_VIOLATION"
    assert receipt.mutation_count == 0
    effect = command(command_id="cmd:effect", idempotency_key="idem:effect", material_effect_requested=True)
    receipt2 = execute(rt, effect)
    assert receipt2.reason == "R7_INTERNAL_GOVERNANCE_CANNOT_EXECUTE_MATERIAL_EFFECT"
    assert receipt2.material_effect_performed is False


def test_communication_never_transfers_authority():
    rt = runtime()
    rt.register_governor(
        governor("governor:communication", owned=("last_message_ref",), function=GovernorFunction.COMMUNICATION)
    )
    rt.communicate(
        CommunicationEnvelope(
            "msg:1", MISSION, "governor:state", "governor:communication",
            "HANDOFF_FOR_REVIEW", "evidence:r7:1"
        )
    )
    assert rt.communications[0].authority_transferred is False
    with pytest.raises(R7InvariantError, match="MUST_NOT_TRANSFER_AUTHORITY"):
        CommunicationEnvelope(
            "msg:bad", MISSION, "governor:state", "governor:communication",
            "FORGED", "none", authority_transferred=True
        )


def test_generation_fencing_and_expiry_fail_closed():
    rt = runtime()
    expired = command(command_id="cmd:expired", idempotency_key="idem:expired")
    assert execute(rt, expired, now=501.0).mutation_count == 0
    assert rt.fence_generation("governor:state") == 2
    stale = command(command_id="cmd:stale", idempotency_key="idem:stale")
    assert execute(rt, stale).reason == "STALE_GENERATION"
    rt.bind_lease(lease(lease_id="lease:gen2", generation=2))
    current = command(
        command_id="cmd:gen2",
        idempotency_key="idem:gen2",
        lease_id="lease:gen2",
        generation=2,
    )
    assert execute(rt, current).mutation_count == 1


def test_idempotent_replay_does_not_require_second_schedule_and_never_duplicates():
    rt = runtime()
    cmd = command()
    first = execute(rt, cmd)
    replay = rt.execute(cmd, now=111.0)
    assert first.state_version_after == 1
    assert replay.status.value == "REPLAYED"
    assert replay.mutation_count == 0
    assert rt.state_version == 1
    assert rt.verify_receipt_chain() is True
    with pytest.raises(R7InvariantError, match="DIVERGENT_COMMAND"):
        rt.execute(replace(cmd, write_set={"current_phase": "DIVERGENT"}), now=112.0)


def test_failure_injection_requires_rescheduling_before_retry():
    rt = runtime()
    cmd = command()
    admit(rt, cmd)
    rt.inject_failure(FailurePoint.BEFORE_COMMIT)
    with pytest.raises(RuntimeError, match="before_commit"):
        rt.execute(cmd, now=110.0)
    assert rt.state_version == 0
    admit(rt, cmd)
    assert rt.execute(cmd, now=111.0).mutation_count == 1


def test_owner_scoped_recovery_preserves_other_governor_state_and_monotonic_version():
    rt = runtime()
    rt.register_governor(governor("governor:evidence", owned=("evidence_refs",), function=GovernorFunction.EVIDENCE))
    rt.bind_lease(lease("governor:evidence", lease_id="lease:evidence"))
    execute(rt, command())
    rt.checkpoint("cp:1", now=111.0)
    execute(
        rt,
        command(
            command_id="cmd:block",
            idempotency_key="idem:block",
            expected_state_version=1,
            write_set={"blockers": ["b1"]},
        ),
        now=112.0,
    )
    execute(
        rt,
        command(
            command_id="cmd:evidence",
            governor_id="governor:evidence",
            lease_id="lease:evidence",
            idempotency_key="idem:evidence",
            expected_state_version=2,
            write_set={"evidence_refs": ["e1"]},
        ),
        now=113.0,
    )
    before = rt.state_version
    generation = rt.recover_governor("governor:state", checkpoint_id="cp:1")
    assert generation == 2
    assert rt.state_version == before + 1
    assert rt.state["evidence_refs"] == ["e1"]
    assert "blockers" not in rt.state


def test_rollback_counts_only_real_deltas_and_invalidates_later_idempotency():
    rt = runtime()
    execute(rt, command())
    rt.checkpoint("cp:rollback", now=111.0)
    later = command(
        command_id="cmd:later",
        idempotency_key="idem:later",
        expected_state_version=1,
        write_set={"blockers": ["b1"]},
    )
    execute(rt, later, now=112.0)
    before = rt.state_version
    rt.rollback_to_checkpoint("cp:rollback")
    assert rt.state_version == before + 1
    assert rt.receipts[-1].mutation_count == 1
    with pytest.raises(R7InvariantError, match="INVALIDATED_BY_ROLLBACK"):
        rt.execute(later, now=113.0)
