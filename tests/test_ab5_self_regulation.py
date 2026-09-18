from app.cognitive_validation import (
    CognitiveControlState,
    RegulatoryAction,
    SelfRegulationEngine,
)


def test_ab5_normal_state_proceeds():
    decision = SelfRegulationEngine().decide(CognitiveControlState())
    assert decision.action == RegulatoryAction.PROCEED
    assert decision.review_depth == 1


def test_ab5_critical_contradiction_forces_fail_closed_hold():
    decision = SelfRegulationEngine().decide(
        CognitiveControlState(contradiction_count=2, confidence=0.95)
    )
    assert decision.action == RegulatoryAction.ENTER_HOLD
    assert decision.risk_level == "critical"


def test_ab5_resource_pressure_reduces_action_scope():
    decision = SelfRegulationEngine().decide(
        CognitiveControlState(resource_pressure=0.95)
    )
    assert decision.action == RegulatoryAction.REDUCE_ACTION_SCOPE


def test_ab5_repeated_failures_request_specialist_ocs():
    decision = SelfRegulationEngine().decide(
        CognitiveControlState(repeated_failures=3)
    )
    assert decision.action == RegulatoryAction.REQUEST_SPECIALIST_OCS
    assert decision.review_depth == 3


def test_ab5_insufficient_evidence_changes_control_policy():
    engine = SelfRegulationEngine()
    treatment = engine.decide(CognitiveControlState(evidence_sufficiency=0.20))
    ablated = engine.decide(CognitiveControlState(evidence_sufficiency=1.0))
    assert treatment.action == RegulatoryAction.SEEK_EVIDENCE
    assert ablated.action == RegulatoryAction.PROCEED


def test_ab5_high_uncertainty_defers_decision():
    decision = SelfRegulationEngine().decide(
        CognitiveControlState(uncertainty=0.90, confidence=0.90)
    )
    assert decision.action == RegulatoryAction.DEFER


def test_ab5_moderate_uncertainty_increases_review_depth():
    decision = SelfRegulationEngine().decide(
        CognitiveControlState(uncertainty=0.60)
    )
    assert decision.action == RegulatoryAction.INCREASE_REVIEW_DEPTH
    assert decision.review_depth == 2


def test_ab5_internal_state_is_causal_not_task_instruction():
    engine = SelfRegulationEngine()
    safe = engine.decide(CognitiveControlState(confidence=0.90, uncertainty=0.10))
    risky = engine.decide(CognitiveControlState(confidence=0.15, uncertainty=0.10))
    assert safe.action == RegulatoryAction.PROCEED
    assert risky.action == RegulatoryAction.DEFER


def test_ab5_critical_contradiction_dominates_other_signals():
    decision = SelfRegulationEngine().decide(
        CognitiveControlState(
            contradiction_count=3,
            repeated_failures=5,
            resource_pressure=1.0,
            evidence_sufficiency=0.0,
        )
    )
    assert decision.action == RegulatoryAction.ENTER_HOLD


def test_ab5_invalid_control_state_fails_closed():
    engine = SelfRegulationEngine()
    try:
        engine.decide(CognitiveControlState(confidence=1.1))
    except ValueError as exc:
        assert "confidence" in str(exc)
    else:
        raise AssertionError("invalid cognitive control state must be rejected")
