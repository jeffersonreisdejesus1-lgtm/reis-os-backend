from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from app.gica.contracts import (
    CANONICAL_OCS_ROSTER,
    AuthorityEvidence,
    FounderAuthorizationEvidence,
    GateEvidence,
    GicaGate,
    GicaProgramContract,
    GicaProgramState,
    GicaVerificationContext,
    ProgramTransitionError,
    _expected_signature,
)

NOW = datetime(2026, 9, 12, 23, 0, tzinfo=timezone.utc)
HEAD = "2bcb624b4487fa84f0c80828941985043697e5da"
PROGRAM = "GICA"
POLICY = "GICA-AUTHORITY-v1"
VERIFIER = "SYNESIS-VERIFIER"
AUTH_ISSUER = "NOESIS-AUTHORITY"
EVIDENCE_ISSUER = "SYNESIS-EVIDENCE"
FOUNDER_ISSUER = "FOUNDER-RESERVED"
AUTH_KEY = b"test-authority-key"
EVIDENCE_KEY = b"test-evidence-key"
FOUNDER_KEY = b"test-founder-key"


def verification_context() -> GicaVerificationContext:
    return GicaVerificationContext(
        verifier_id=VERIFIER,
        authority_keys={AUTH_ISSUER: AUTH_KEY},
        gate_evidence_keys={EVIDENCE_ISSUER: EVIDENCE_KEY},
        founder_keys={FOUNDER_ISSUER: FOUNDER_KEY},
        criteria_versions={gate: f"{gate.name}-CRITERIA-v1" for gate in GicaGate},
        allowed_assurers={gate: frozenset({"SYNESIS"}) for gate in GicaGate},
        independent_assurers=frozenset({"SYNESIS"}),
        reserved_founder_issuer=FOUNDER_ISSUER,
        accepted_policy_versions=frozenset({POLICY}),
    )


def sign(value, key: bytes):
    return replace(value, signature=_expected_signature(value, key))


def authority(gate: GicaGate, target: GicaGate, **changes) -> AuthorityEvidence:
    value = AuthorityEvidence(
        program_id=PROGRAM,
        operation=f"transition:{gate.name}->{target.name}",
        object_version=HEAD,
        issuer=AUTH_ISSUER,
        verifier=VERIFIER,
        issued_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(hours=1),
        policy_version=POLICY,
        provenance="ledger://authority/001",
        signature="",
    )
    value = replace(value, **changes)
    return sign(value, AUTH_KEY)


def evidence(gate: GicaGate, assurance_pass: bool = False, **changes) -> GateEvidence:
    value = GateEvidence(
        program_id=PROGRAM,
        gate=gate,
        object_version=HEAD,
        criteria_version=f"{gate.name}-CRITERIA-v1",
        lineage=("artifact://criteria", "artifact://review"),
        issuer=EVIDENCE_ISSUER,
        assurer="SYNESIS",
        verifier=VERIFIER,
        issued_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(hours=1),
        policy_version=POLICY,
        provenance="ledger://evidence/001",
        assurance_pass=assurance_pass,
        signature="",
    )
    value = replace(value, **changes)
    return sign(value, EVIDENCE_KEY)


def founder(**changes) -> FounderAuthorizationEvidence:
    value = FounderAuthorizationEvidence(
        program_id=PROGRAM,
        gate=GicaGate.GA12,
        object_version=HEAD,
        operation="COMPLETE",
        issuer=FOUNDER_ISSUER,
        verifier=VERIFIER,
        issued_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(hours=1),
        policy_version=POLICY,
        provenance="ledger://founder/001",
        signature="",
    )
    value = replace(value, **changes)
    return sign(value, FOUNDER_KEY)


def contract_at(gate: GicaGate, state: GicaProgramState = GicaProgramState.ACTIVE, history=()) -> GicaProgramContract:
    return GicaProgramContract(PROGRAM, gate, HEAD, state=state, gate_history=history)


def advance(current: GicaProgramContract, target: GicaGate, gate_evidence: GateEvidence | None = None):
    return current.transition_to(
        target,
        authority=authority(current.gate, target),
        gate_evidence=gate_evidence or evidence(current.gate),
        verification=verification_context(),
        now=NOW,
    )


def test_canonical_roster_contains_eleven_unique_ocs_including_themis() -> None:
    assert len(CANONICAL_OCS_ROSTER) == 11
    assert len(set(CANONICAL_OCS_ROSTER)) == 11
    assert "TÊMIS" in CANONICAL_OCS_ROSTER


def test_ga2_to_ga3_denied_without_ga2_specific_assurance_pass() -> None:
    with pytest.raises(ProgramTransitionError, match="independent_assurance_pass_required"):
        advance(contract_at(GicaGate.GA2), GicaGate.GA3, evidence(GicaGate.GA2, assurance_pass=False))


def test_absent_authority_denied() -> None:
    with pytest.raises(ProgramTransitionError, match="valid_authority_required"):
        contract_at(GicaGate.GA3).transition_to(GicaGate.GA4, authority=None, gate_evidence=evidence(GicaGate.GA3), verification=verification_context(), now=NOW)


def test_forged_authority_denied() -> None:
    forged = replace(authority(GicaGate.GA3, GicaGate.GA4), signature="00" * 32)
    with pytest.raises(ProgramTransitionError, match="authority_forged_denied"):
        contract_at(GicaGate.GA3).transition_to(GicaGate.GA4, authority=forged, gate_evidence=evidence(GicaGate.GA3), verification=verification_context(), now=NOW)


def test_stale_authority_denied() -> None:
    stale = authority(GicaGate.GA3, GicaGate.GA4, expires_at=NOW - timedelta(seconds=1))
    with pytest.raises(ProgramTransitionError, match="stale_or_invalid_evidence_denied"):
        contract_at(GicaGate.GA3).transition_to(GicaGate.GA4, authority=stale, gate_evidence=evidence(GicaGate.GA3), verification=verification_context(), now=NOW)


def test_wrong_scope_authority_denied() -> None:
    wrong = authority(GicaGate.GA3, GicaGate.GA4, operation="transition:GA2->GA3")
    with pytest.raises(ProgramTransitionError, match="authority_wrong_scope_denied"):
        contract_at(GicaGate.GA3).transition_to(GicaGate.GA4, authority=wrong, gate_evidence=evidence(GicaGate.GA3), verification=verification_context(), now=NOW)


def test_evidence_absent_denied() -> None:
    with pytest.raises(ProgramTransitionError, match="gate_evidence_required"):
        contract_at(GicaGate.GA3).transition_to(GicaGate.GA4, authority=authority(GicaGate.GA3, GicaGate.GA4), gate_evidence=None, verification=verification_context(), now=NOW)


def test_unbound_evidence_denied() -> None:
    unbound = evidence(GicaGate.GA3, provenance="")
    with pytest.raises(ProgramTransitionError, match="evidence_provenance_required"):
        contract_at(GicaGate.GA3).transition_to(GicaGate.GA4, authority=authority(GicaGate.GA3, GicaGate.GA4), gate_evidence=unbound, verification=verification_context(), now=NOW)


def test_wrong_head_evidence_denied() -> None:
    wrong = evidence(GicaGate.GA3, object_version="wrong-head")
    with pytest.raises(ProgramTransitionError, match="evidence_wrong_object_version_denied"):
        contract_at(GicaGate.GA3).transition_to(GicaGate.GA4, authority=authority(GicaGate.GA3, GicaGate.GA4), gate_evidence=wrong, verification=verification_context(), now=NOW)


def test_wrong_gate_evidence_denied() -> None:
    wrong = evidence(GicaGate.GA2)
    with pytest.raises(ProgramTransitionError, match="evidence_wrong_gate_denied"):
        contract_at(GicaGate.GA3).transition_to(GicaGate.GA4, authority=authority(GicaGate.GA3, GicaGate.GA4), gate_evidence=wrong, verification=verification_context(), now=NOW)


def test_wrong_criteria_version_evidence_denied() -> None:
    wrong = evidence(GicaGate.GA3, criteria_version="GA3-CRITERIA-wrong")
    with pytest.raises(ProgramTransitionError, match="evidence_wrong_criteria_version_denied"):
        contract_at(GicaGate.GA3).transition_to(GicaGate.GA4, authority=authority(GicaGate.GA3, GicaGate.GA4), gate_evidence=wrong, verification=verification_context(), now=NOW)


def test_empty_or_invalid_evidence_lineage_denied() -> None:
    wrong = evidence(GicaGate.GA3, lineage=())
    with pytest.raises(ProgramTransitionError, match="evidence_lineage_required"):
        contract_at(GicaGate.GA3).transition_to(GicaGate.GA4, authority=authority(GicaGate.GA3, GicaGate.GA4), gate_evidence=wrong, verification=verification_context(), now=NOW)


def test_self_asserted_founder_authorization_denied() -> None:
    fake = founder(issuer="SOFIA")
    target = contract_at(GicaGate.GA12, GicaProgramState.READY_FOR_FOUNDER, history=(GicaGate.GA11,))
    with pytest.raises(ProgramTransitionError, match="founder_reserved_authority_required"):
        target.founder_promote(authorization=fake, verification=verification_context(), now=NOW)


def test_wrong_program_founder_authorization_denied() -> None:
    wrong = founder(program_id="OTHER")
    target = contract_at(GicaGate.GA12, GicaProgramState.READY_FOR_FOUNDER, history=(GicaGate.GA11,))
    with pytest.raises(ProgramTransitionError, match="founder_wrong_program_denied"):
        target.founder_promote(authorization=wrong, verification=verification_context(), now=NOW)


def test_wrong_head_founder_authorization_denied() -> None:
    wrong = founder(object_version="wrong-head")
    target = contract_at(GicaGate.GA12, GicaProgramState.READY_FOR_FOUNDER, history=(GicaGate.GA11,))
    with pytest.raises(ProgramTransitionError, match="founder_wrong_object_version_denied"):
        target.founder_promote(authorization=wrong, verification=verification_context(), now=NOW)


def test_founder_authorization_outside_ga12_denied() -> None:
    with pytest.raises(ProgramTransitionError, match="founder_promotion_outside_ga12_denied"):
        contract_at(GicaGate.GA11).founder_promote(authorization=founder(), verification=verification_context(), now=NOW)


def test_valid_ga2_assurance_permits_ga2_to_ga3_when_other_requirements_pass() -> None:
    result = advance(contract_at(GicaGate.GA2), GicaGate.GA3, evidence(GicaGate.GA2, assurance_pass=True))
    assert result.gate is GicaGate.GA3


def test_valid_provenance_bound_authority_satisfies_transition() -> None:
    result = advance(contract_at(GicaGate.GA3), GicaGate.GA4)
    assert result.gate is GicaGate.GA4


def test_correctly_bound_gate_evidence_satisfies_gate() -> None:
    result = advance(contract_at(GicaGate.GA4), GicaGate.GA5)
    assert result.gate is GicaGate.GA5


def test_valid_independently_verifiable_founder_authorization_permits_complete_only_after_legitimate_ga12() -> None:
    ga11 = contract_at(GicaGate.GA11)
    ga12 = ga11.transition_to(GicaGate.GA12, authority=authority(GicaGate.GA11, GicaGate.GA12), gate_evidence=evidence(GicaGate.GA11, assurance_pass=True), verification=verification_context(), now=NOW)
    complete = ga12.founder_promote(authorization=founder(), verification=verification_context(), now=NOW)
    assert complete.state is GicaProgramState.COMPLETE


def test_directly_constructed_ga12_ready_state_cannot_complete_without_legitimate_transition_history() -> None:
    fabricated = contract_at(GicaGate.GA12, GicaProgramState.READY_FOR_FOUNDER)
    with pytest.raises(ProgramTransitionError, match="legitimate_ga12_transition_required"):
        fabricated.founder_promote(authorization=founder(), verification=verification_context(), now=NOW)


def test_hold_state_cannot_advance() -> None:
    with pytest.raises(ProgramTransitionError, match="program_not_in_active_state"):
        advance(contract_at(GicaGate.GA3, GicaProgramState.HOLD), GicaGate.GA4)
