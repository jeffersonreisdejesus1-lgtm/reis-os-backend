from types import SimpleNamespace

import pytest

from app.cognitive_validation.real_mission_qualification import (
    MissionQualificationEvidence,
    RealMissionQualificationError,
    RealMissionQualifier,
)


def evidence(**overrides):
    values = dict(
        mission_id="mission-real-001",
        mission_class="SOFTWARE_ENGINEERING",
        mission_input="Implement a governed institutional change",
        cognitive_entry_receipt="cognitive-entry",
        capability_discovery_receipt="discovery",
        ocs_composition_receipt="composition",
        authority_receipt="authority",
        governed_execution_receipt="execution",
        evidence_receipt="evidence",
        state_hash="state-v2",
        learning_receipt="learning",
        final_status="SUCCESS",
        real_effect_observed=True,
    )
    values.update(overrides)
    return MissionQualificationEvidence(**values)


def learning(*, mission_id="mission-real-001", outcome="FAILURE", changed=True, receipt="learning"):
    previous = SimpleNamespace(selected_capability_id="route-a")
    next_plan = SimpleNamespace(selected_capability_id="route-b" if changed else "route-a")
    feedback = SimpleNamespace(mission_id=mission_id, outcome=outcome)
    return SimpleNamespace(
        feedback=feedback,
        previous_plan=previous,
        next_plan=next_plan,
        route_changed=changed,
        learning_receipt=receipt,
    )


def test_real_success_requires_complete_chain_and_observed_effect():
    result = RealMissionQualifier().qualify(evidence=evidence())
    assert result.evidence.final_status == "SUCCESS"
    assert result.qualification_receipt


def test_success_without_observed_effect_is_rejected():
    with pytest.raises(RealMissionQualificationError, match="success_requires_observed_effect"):
        RealMissionQualifier().qualify(evidence=evidence(real_effect_observed=False))


def test_missing_chain_receipt_is_rejected():
    with pytest.raises(RealMissionQualificationError, match="evidence_chain_incomplete"):
        RealMissionQualifier().qualify(evidence=evidence(authority_receipt=""))


def test_failure_recovery_requires_observed_route_change():
    ev = evidence(mission_class="FAILURE_RECOVERY_REPLAN")
    result = RealMissionQualifier().qualify(evidence=ev, learning=learning())
    assert result.route_changed_after_failure is True


def test_failure_recovery_without_route_change_is_rejected():
    ev = evidence(mission_class="FAILURE_RECOVERY_REPLAN")
    with pytest.raises(RealMissionQualificationError, match="different_route_required"):
        RealMissionQualifier().qualify(evidence=ev, learning=learning(changed=False))


def test_failure_recovery_requires_failure_or_partial_feedback():
    ev = evidence(mission_class="FAILURE_RECOVERY_REPLAN")
    with pytest.raises(RealMissionQualificationError, match="failure_feedback_required"):
        RealMissionQualifier().qualify(evidence=ev, learning=learning(outcome="SUCCESS"))


def test_authority_denied_mission_must_be_denied_as_designed():
    with pytest.raises(RealMissionQualificationError, match="authority_denial_status_required"):
        RealMissionQualifier().qualify(evidence=evidence(mission_class="AUTHORITY_DENIED"))


def test_qualification_suite_requires_failure_recovery_case():
    qualifier = RealMissionQualifier()
    ordinary = qualifier.qualify(evidence=evidence())
    with pytest.raises(RealMissionQualificationError, match="failure_recovery_mission_required"):
        qualifier.qualify_suite([ordinary])


def test_qualification_suite_accepts_real_and_recovery_missions():
    qualifier = RealMissionQualifier()
    ordinary = qualifier.qualify(evidence=evidence())
    recovery_ev = evidence(
        mission_id="mission-recovery-001",
        mission_class="FAILURE_RECOVERY_REPLAN",
    )
    recovery = qualifier.qualify(
        evidence=recovery_ev,
        learning=learning(mission_id="mission-recovery-001"),
    )
    assert qualifier.qualify_suite([ordinary, recovery])
