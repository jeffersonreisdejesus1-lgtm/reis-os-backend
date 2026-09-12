import pytest

from app.gica.contracts import (
    CANONICAL_OCS_ROSTER,
    GicaGate,
    GicaProgramContract,
    GicaProgramState,
    ProgramTransitionError,
)


def contract_at(gate: GicaGate, **overrides) -> GicaProgramContract:
    values = {
        "program_id": "GICA-TEST",
        "gate": gate,
        "state": GicaProgramState.ACTIVE,
        "authority_bound": True,
        "evidence_complete": True,
        "independent_assurance_pass": False,
        "founder_authorized": False,
    }
    values.update(overrides)
    return GicaProgramContract(**values)


def test_canonical_roster_contains_eleven_unique_ocs_including_themis() -> None:
    assert len(CANONICAL_OCS_ROSTER) == 11
    assert len(set(CANONICAL_OCS_ROSTER)) == 11
    assert "TÊMIS" in CANONICAL_OCS_ROSTER


def test_ga3_can_transition_only_to_ga4_with_authority_and_evidence() -> None:
    current = contract_at(GicaGate.GA3)
    next_contract = current.transition_to(GicaGate.GA4)
    assert next_contract.gate is GicaGate.GA4
    assert next_contract.state is GicaProgramState.ACTIVE
    assert next_contract.evidence_complete is False


def test_gate_skipping_is_denied() -> None:
    current = contract_at(GicaGate.GA3)
    with pytest.raises(ProgramTransitionError, match="non_sequential_gate_transition_denied"):
        current.transition_to(GicaGate.GA5)


def test_transition_without_authority_is_denied() -> None:
    current = contract_at(GicaGate.GA3, authority_bound=False)
    with pytest.raises(ProgramTransitionError, match="valid_authority_required"):
        current.transition_to(GicaGate.GA4)


def test_transition_without_evidence_is_denied() -> None:
    current = contract_at(GicaGate.GA3, evidence_complete=False)
    with pytest.raises(ProgramTransitionError, match="gate_evidence_required"):
        current.transition_to(GicaGate.GA4)


def test_ga12_requires_independent_assurance_pass() -> None:
    current = contract_at(GicaGate.GA11, independent_assurance_pass=False)
    with pytest.raises(ProgramTransitionError, match="independent_assurance_pass_required"):
        current.transition_to(GicaGate.GA12)


def test_ga12_enters_ready_for_founder_not_complete() -> None:
    current = contract_at(GicaGate.GA11, independent_assurance_pass=True)
    target = current.transition_to(GicaGate.GA12)
    assert target.state is GicaProgramState.READY_FOR_FOUNDER
    assert target.founder_authorized is False


def test_founder_promotion_requires_explicit_authorization() -> None:
    target = GicaProgramContract(
        program_id="GICA-TEST",
        gate=GicaGate.GA12,
        state=GicaProgramState.READY_FOR_FOUNDER,
        authority_bound=True,
        evidence_complete=True,
        independent_assurance_pass=True,
        founder_authorized=False,
    )
    with pytest.raises(ProgramTransitionError, match="explicit_founder_authorization_required"):
        target.founder_promote()


def test_explicit_founder_authorization_can_complete_after_assurance() -> None:
    target = GicaProgramContract(
        program_id="GICA-TEST",
        gate=GicaGate.GA12,
        state=GicaProgramState.READY_FOR_FOUNDER,
        authority_bound=True,
        evidence_complete=True,
        independent_assurance_pass=True,
        founder_authorized=True,
    )
    promoted = target.founder_promote()
    assert promoted.state is GicaProgramState.COMPLETE


def test_hold_state_cannot_advance() -> None:
    current = contract_at(GicaGate.GA3, state=GicaProgramState.HOLD)
    with pytest.raises(ProgramTransitionError, match="program_not_in_active_state"):
        current.transition_to(GicaGate.GA4)
