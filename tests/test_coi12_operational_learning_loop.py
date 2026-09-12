from types import SimpleNamespace

import pytest

from app.cognitive_validation.operational_learning_loop import (
    ClosedOperationalLearningLoop,
    OperationalLearningLoopError,
)


def coi11_result(*, mission="mission-1", evidence="evidence-1", state_hash="state-1", version=1):
    return SimpleNamespace(
        evidence=SimpleNamespace(mission_id=mission, evidence_receipt=evidence),
        state_snapshot=SimpleNamespace(
            mission_id=mission,
            evidence_receipt=evidence,
            state_hash=state_hash,
            state_version=version,
        ),
    )


def test_failure_feedback_changes_next_route():
    loop=ClosedOperationalLearningLoop()
    plan=loop.initial_plan(mission_id="mission-1",capability_id="github")
    result=loop.close_loop(previous_plan=plan,coi11_result=coi11_result(),candidate_capabilities=["github","software_factory"],outcome="FAILURE")
    assert result.route_changed is True
    assert result.next_plan.selected_capability_id == "software_factory"
    assert result.next_plan.plan_revision == 2
    assert result.next_plan.prior_plan_receipt == plan.plan_receipt
    assert result.next_plan.feedback_receipt
    assert result.learning_receipt


def test_success_feedback_preserves_viable_route_but_advances_plan():
    loop=ClosedOperationalLearningLoop(); plan=loop.initial_plan(mission_id="mission-1",capability_id="github")
    result=loop.close_loop(previous_plan=plan,coi11_result=coi11_result(),candidate_capabilities=["github","software_factory"],outcome="SUCCESS")
    assert result.route_changed is False
    assert result.next_plan.selected_capability_id == "github"
    assert result.next_plan.plan_revision == 2
    assert result.next_plan.state_hash == "state-1"


def test_feedback_is_bound_to_coi11_evidence_and_state():
    loop=ClosedOperationalLearningLoop(); plan=loop.initial_plan(mission_id="mission-1",capability_id="github")
    broken=coi11_result(evidence="evidence-1")
    broken.state_snapshot.evidence_receipt="other"
    with pytest.raises(OperationalLearningLoopError,match="evidence_state_mismatch"):
        loop.close_loop(previous_plan=plan,coi11_result=broken,candidate_capabilities=["github","software_factory"],outcome="FAILURE")


def test_mission_mismatch_denied():
    loop=ClosedOperationalLearningLoop(); plan=loop.initial_plan(mission_id="mission-1",capability_id="github")
    with pytest.raises(OperationalLearningLoopError,match="mission_mismatch"):
        loop.close_loop(previous_plan=plan,coi11_result=coi11_result(mission="mission-2"),candidate_capabilities=["github","software_factory"],outcome="FAILURE")


def test_replanning_requires_state_change():
    loop=ClosedOperationalLearningLoop(); plan=loop.initial_plan(mission_id="mission-1",capability_id="github",state_hash="state-1")
    with pytest.raises(OperationalLearningLoopError,match="requires_new_state"):
        loop.close_loop(previous_plan=plan,coi11_result=coi11_result(state_hash="state-1"),candidate_capabilities=["github","software_factory"],outcome="FAILURE")


def test_failure_without_alternative_route_fails_closed():
    loop=ClosedOperationalLearningLoop(); plan=loop.initial_plan(mission_id="mission-1",capability_id="github")
    with pytest.raises(OperationalLearningLoopError,match="no_alternative_route"):
        loop.close_loop(previous_plan=plan,coi11_result=coi11_result(),candidate_capabilities=["github"],outcome="FAILURE")


def test_previous_route_must_be_in_governed_candidates():
    loop=ClosedOperationalLearningLoop(); plan=loop.initial_plan(mission_id="mission-1",capability_id="github")
    with pytest.raises(OperationalLearningLoopError,match="previous_route_not_candidate"):
        loop.close_loop(previous_plan=plan,coi11_result=coi11_result(),candidate_capabilities=["software_factory"],outcome="FAILURE")


def test_duplicate_candidates_denied():
    loop=ClosedOperationalLearningLoop(); plan=loop.initial_plan(mission_id="mission-1",capability_id="github")
    with pytest.raises(OperationalLearningLoopError,match="duplicate_candidate"):
        loop.close_loop(previous_plan=plan,coi11_result=coi11_result(),candidate_capabilities=["github","github"],outcome="FAILURE")


def test_invalid_outcome_denied():
    loop=ClosedOperationalLearningLoop(); plan=loop.initial_plan(mission_id="mission-1",capability_id="github")
    with pytest.raises(OperationalLearningLoopError,match="outcome_invalid"):
        loop.close_loop(previous_plan=plan,coi11_result=coi11_result(),candidate_capabilities=["github","software_factory"],outcome="UNKNOWN")
