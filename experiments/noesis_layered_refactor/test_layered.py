from __future__ import annotations

from experiments.noesis_layered_refactor.layered import (
    FORBIDDEN_ACTIONS,
    CycleDisposition,
    LayeredNoesis,
    RefactorStage,
    RelationType,
)


def _new(stage=RefactorStage.R6_FORMAL_CHECKS, threshold=2):
    return LayeredNoesis(
        mission_id="NOESIS-LAYERED-REFRACTOR-QUALIFICATION",
        current_object="EC-NOESIS-007",
        max_stage=stage,
        stagnation_threshold=threshold,
    )


def test_r1_blackboard_is_explicit_and_l0_preserved():
    n = _new(RefactorStage.R1_BLACKBOARD)
    before = n.l0_identity_hash
    state = n.read_state()
    assert state["mission_id"] == "NOESIS-LAYERED-REFRACTOR-QUALIFICATION"
    assert state["current_object"] == "EC-NOESIS-007"
    assert n.l0.initial_binding_hash == before


def test_r2_stagnation_detects_no_material_delta():
    n = _new(RefactorStage.R2_PROGRESS_MONITOR, threshold=2)
    n.bind(current_phase="IMPLEMENTATION")
    r1 = n.cycle("tx-r2-1", {"phase": "IMPLEMENTATION"})
    r2 = n.cycle("tx-r2-2", {"phase": "IMPLEMENTATION"})
    assert r1["blackboard"]["stagnation_cycles"] == 1
    assert r2["blackboard"]["stagnation_cycles"] >= 2


def test_r3_typed_transition_never_transfers_authority():
    n = _new(RefactorStage.R3_TYPED_TRANSITIONS)
    t = n._record_transition(RelationType.HANDOFF_FOR_CONFORMANCE, "DEDALA", "TEST")
    assert t.authority_transferred is False


def test_r4_scheduler_never_allows_forbidden_authority_actions():
    n = _new(RefactorStage.R4_SCHEDULER)
    n.bind(current_phase="IMPLEMENTATION_COMPLETE")
    decision = n.schedule()
    assert not (set(decision.allowed_actions) & FORBIDDEN_ACTIONS)
    assert set(FORBIDDEN_ACTIONS).issubset(set(decision.prohibited_actions))


def test_forbidden_transition_is_blocked_before_native_cognition():
    n = _new()
    result = n.cycle(
        "tx-forbidden",
        {"phase": "IMPLEMENTATION", "requested_actions": ["MERGE", "PRODUCTION"]},
    )
    assert result["disposition"] == CycleDisposition.BLOCKED.value
    assert result["cognitive_result"]["status"] == "BLOCKED"
    assert result["l0_binding_hash"] == n.l0_identity_hash


def test_r5_telemetry_chain_is_verifiable():
    n = _new(RefactorStage.R5_TELEMETRY)
    n.bind(current_phase="IMPLEMENTATION")
    n.cycle("tx-tel-1", {"phase": "IMPLEMENTATION"})
    n.cycle("tx-tel-2", {"phase": "IMPLEMENTATION"})
    assert n.telemetry.events
    assert n.telemetry.verify() is True


def test_r6_formal_checks_keep_l0_identity_and_ec():
    n = _new(RefactorStage.R6_FORMAL_CHECKS)
    n.bind(current_phase="IMPLEMENTATION")
    result = n.cycle("tx-r6", {"phase": "IMPLEMENTATION"})
    assert result["l0_binding_hash"] == n.l0_identity_hash
    assert result["l0_current_ec"] == "EC-NOESIS-007"


def test_native_cognitive_engine_remains_under_layered_candidate():
    n = _new()
    result = n.cycle("tx-cognition", {"phase": "IMPLEMENTATION", "claim": "x"})
    assert "cognitive_result" in result
    assert result["l0_binding_hash"] == n.l0.initial_binding_hash


def test_stage_activation_is_cumulative():
    n = _new(RefactorStage.R4_SCHEDULER)
    assert n.active_layers == (
        RefactorStage.R1_BLACKBOARD.value,
        RefactorStage.R2_PROGRESS_MONITOR.value,
        RefactorStage.R3_TYPED_TRANSITIONS.value,
        RefactorStage.R4_SCHEDULER.value,
    )


def test_explicit_stop_prevents_reentry():
    n = _new()
    n.stop("BOUND_COMPLETE")
    result = n.cycle("tx-after-stop", {"phase": "IMPLEMENTATION"})
    assert result["status"] == "STOPPED"
    assert result["stop_reason"] == "BOUND_COMPLETE"


def test_no_self_assurance_or_self_promotion_authority():
    n = _new()
    decision = n.schedule()
    assert "SELF_ASSURANCE" not in decision.allowed_actions
    assert "SELF_PROMOTION" not in decision.allowed_actions
    assert "CREATE_AUTHORITY" not in decision.allowed_actions


def test_stagnation_with_scheduler_changes_method_instead_of_looping():
    n = _new(RefactorStage.R4_SCHEDULER, threshold=2)
    n.bind(current_phase="IMPLEMENTATION")
    n.cycle("tx-stag-1", {"phase": "IMPLEMENTATION"})
    r2 = n.cycle("tx-stag-2", {"phase": "IMPLEMENTATION"})
    assert r2["disposition"] == CycleDisposition.METHOD_CHANGE.value
    assert r2["transition"]["relation"] == RelationType.METHOD_CHANGE.value
