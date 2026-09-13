from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess

import pytest

import app.gica.contracts as contracts
from app.gica.contracts import (
    CANONICAL_OCS_ROSTER,
    AuthorityEvidence,
    FounderAuthorizationEvidence,
    GateEvidence,
    GicaGate,
    GicaProgramContract,
    GicaProgramState,
    ProgramTransitionError,
    _InstitutionalTrustRoot,
    _expected_signature,
)

NOW = datetime(2026, 9, 12, 23, 0, tzinfo=timezone.utc)
PROGRAM = "GICA"
POLICY = "GICA-AUTHORITY-v1"
VERIFIER = "SYNESIS-VERIFIER"
AUTH_ISSUER = "NOESIS-AUTHORITY"
EVIDENCE_ISSUER = "SYNESIS-EVIDENCE"
FOUNDER_ISSUER = "FOUNDER-RESERVED"
AUTH_KEY = b"test-fixture-authority-key"
EVIDENCE_KEY = b"test-fixture-evidence-key"
FOUNDER_KEY = b"test-fixture-founder-key"
ATTACKER_KEY = b"attacker-key"
ATTACKER = "ATTACKER"


def _git_head() -> str:
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


HEAD = _git_head()


def trusted_root() -> _InstitutionalTrustRoot:
    return _InstitutionalTrustRoot(
        authority_key=AUTH_KEY,
        gate_evidence_key=EVIDENCE_KEY,
        founder_key=FOUNDER_KEY,
        bootstrap_provenance="test-fixture:simulated-runtime-composition-root",
    )


@pytest.fixture(autouse=True)
def institutional_runtime_root(monkeypatch):
    root = trusted_root()
    monkeypatch.setattr(contracts, "_resolve_institutional_trust", lambda: root)
    return root


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
    return sign(replace(value, **changes), AUTH_KEY)


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
    return sign(replace(value, **changes), EVIDENCE_KEY)


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
    return sign(replace(value, **changes), FOUNDER_KEY)


def contract_at(gate: GicaGate, state: GicaProgramState = GicaProgramState.ACTIVE, history=()) -> GicaProgramContract:
    return GicaProgramContract(PROGRAM, gate, HEAD, state=state, gate_history=history)


def advance(current: GicaProgramContract, target: GicaGate, gate_evidence: GateEvidence | None = None, authority_evidence: AuthorityEvidence | None = None):
    return current.transition_to(
        target,
        authority=authority_evidence or authority(current.gate, target),
        gate_evidence=gate_evidence or evidence(current.gate),
        now=NOW,
    )


def attacker_authority(gate: GicaGate, target: GicaGate):
    value = AuthorityEvidence(PROGRAM, f"transition:{gate.name}->{target.name}", HEAD, ATTACKER, ATTACKER, NOW - timedelta(minutes=1), NOW + timedelta(hours=1), "ATTACKER-POLICY", "attacker://authority", "")
    return sign(value, ATTACKER_KEY)


def attacker_evidence(gate: GicaGate):
    value = GateEvidence(PROGRAM, gate, HEAD, "ATTACKER-CRITERIA", ("attacker://criteria",), ATTACKER, ATTACKER, ATTACKER, NOW - timedelta(minutes=1), NOW + timedelta(hours=1), "ATTACKER-POLICY", "attacker://evidence", True, "")
    return sign(value, ATTACKER_KEY)


def attacker_founder():
    value = FounderAuthorizationEvidence(PROGRAM, GicaGate.GA12, HEAD, "COMPLETE", ATTACKER, ATTACKER, NOW - timedelta(minutes=1), NOW + timedelta(hours=1), "ATTACKER-POLICY", "attacker://founder", "")
    return sign(value, ATTACKER_KEY)


def test_exact_object_binding_uses_checked_out_git_head() -> None:
    assert len(HEAD) == 40
    assert HEAD == _git_head()


def test_transaction_api_has_no_verification_or_trust_root_argument() -> None:
    with pytest.raises(TypeError):
        contract_at(GicaGate.GA2).transition_to(
            GicaGate.GA3,
            authority=authority(GicaGate.GA2, GicaGate.GA3),
            gate_evidence=evidence(GicaGate.GA2, assurance_pass=True),
            verification=trusted_root(),  # type: ignore[call-arg]
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
        contract_at(GicaGate.GA3).transition_to(GicaGate.GA4, authority=None, gate_evidence=evidence(GicaGate.GA3), now=NOW)


def test_forged_authority_denied() -> None:
    forged = replace(authority(GicaGate.GA3, GicaGate.GA4), signature="00" * 32)
    with pytest.raises(ProgramTransitionError, match="authority_forged_denied"):
        advance(contract_at(GicaGate.GA3), GicaGate.GA4, authority_evidence=forged)


def test_stale_authority_denied() -> None:
    stale = authority(GicaGate.GA3, GicaGate.GA4, expires_at=NOW - timedelta(seconds=1))
    with pytest.raises(ProgramTransitionError, match="stale_or_invalid_evidence_denied"):
        advance(contract_at(GicaGate.GA3), GicaGate.GA4, authority_evidence=stale)


def test_wrong_scope_authority_denied() -> None:
    wrong = authority(GicaGate.GA3, GicaGate.GA4, operation="transition:GA2->GA3")
    with pytest.raises(ProgramTransitionError, match="authority_wrong_scope_denied"):
        advance(contract_at(GicaGate.GA3), GicaGate.GA4, authority_evidence=wrong)


def test_wrong_object_authority_denied() -> None:
    wrong = authority(GicaGate.GA3, GicaGate.GA4, object_version="wrong-head")
    with pytest.raises(ProgramTransitionError, match="authority_wrong_object_version_denied"):
        advance(contract_at(GicaGate.GA3), GicaGate.GA4, authority_evidence=wrong)


def test_evidence_absent_denied() -> None:
    with pytest.raises(ProgramTransitionError, match="gate_evidence_required"):
        contract_at(GicaGate.GA3).transition_to(GicaGate.GA4, authority=authority(GicaGate.GA3, GicaGate.GA4), gate_evidence=None, now=NOW)


def test_unbound_evidence_denied() -> None:
    with pytest.raises(ProgramTransitionError, match="evidence_provenance_required"):
        advance(contract_at(GicaGate.GA3), GicaGate.GA4, gate_evidence=evidence(GicaGate.GA3, provenance=""))


def test_wrong_head_evidence_denied() -> None:
    with pytest.raises(ProgramTransitionError, match="evidence_wrong_object_version_denied"):
        advance(contract_at(GicaGate.GA3), GicaGate.GA4, gate_evidence=evidence(GicaGate.GA3, object_version="wrong-head"))


def test_wrong_gate_evidence_denied() -> None:
    with pytest.raises(ProgramTransitionError, match="evidence_wrong_gate_denied"):
        advance(contract_at(GicaGate.GA3), GicaGate.GA4, gate_evidence=evidence(GicaGate.GA2))


def test_wrong_criteria_version_evidence_denied() -> None:
    with pytest.raises(ProgramTransitionError, match="evidence_wrong_criteria_version_denied"):
        advance(contract_at(GicaGate.GA3), GicaGate.GA4, gate_evidence=evidence(GicaGate.GA3, criteria_version="wrong"))


def test_empty_or_invalid_evidence_lineage_denied() -> None:
    with pytest.raises(ProgramTransitionError, match="evidence_lineage_required"):
        advance(contract_at(GicaGate.GA3), GicaGate.GA4, gate_evidence=evidence(GicaGate.GA3, lineage=()))


def test_wrong_program_founder_authorization_denied() -> None:
    target = contract_at(GicaGate.GA12, GicaProgramState.READY_FOR_FOUNDER, history=(GicaGate.GA11,))
    with pytest.raises(ProgramTransitionError, match="founder_wrong_program_denied"):
        target.founder_promote(authorization=founder(program_id="OTHER"), now=NOW)


def test_wrong_operation_founder_authorization_denied() -> None:
    target = contract_at(GicaGate.GA12, GicaProgramState.READY_FOR_FOUNDER, history=(GicaGate.GA11,))
    with pytest.raises(ProgramTransitionError, match="founder_wrong_operation_denied"):
        target.founder_promote(authorization=founder(operation="OTHER"), now=NOW)


def test_founder_authorization_outside_ga12_denied() -> None:
    with pytest.raises(ProgramTransitionError, match="founder_promotion_outside_ga12_denied"):
        contract_at(GicaGate.GA11).founder_promote(authorization=founder(), now=NOW)


def test_directly_constructed_ga12_ready_state_cannot_complete_without_legitimate_transition_history() -> None:
    with pytest.raises(ProgramTransitionError, match="legitimate_ga12_transition_required"):
        contract_at(GicaGate.GA12, GicaProgramState.READY_FOR_FOUNDER).founder_promote(authorization=founder(), now=NOW)


def test_hold_state_cannot_advance() -> None:
    with pytest.raises(ProgramTransitionError, match="program_not_in_active_state"):
        advance(contract_at(GicaGate.GA3, GicaProgramState.HOLD), GicaGate.GA4)


def test_attacker_created_authority_root_cannot_be_passed_to_transaction() -> None:
    attacker_root = _InstitutionalTrustRoot(ATTACKER_KEY, ATTACKER_KEY, ATTACKER_KEY, "attacker://root")
    with pytest.raises(TypeError):
        contract_at(GicaGate.GA2).transition_to(
            GicaGate.GA3,
            authority=attacker_authority(GicaGate.GA2, GicaGate.GA3),
            gate_evidence=attacker_evidence(GicaGate.GA2),
            verification=attacker_root,  # type: ignore[call-arg]
            now=NOW,
        )


def test_attacker_created_authority_key_denied() -> None:
    malicious = sign(replace(authority(GicaGate.GA3, GicaGate.GA4), signature=""), ATTACKER_KEY)
    with pytest.raises(ProgramTransitionError, match="authority_forged_denied"):
        advance(contract_at(GicaGate.GA3), GicaGate.GA4, authority_evidence=malicious)


def test_attacker_created_gate_evidence_root_denied() -> None:
    with pytest.raises(ProgramTransitionError):
        advance(contract_at(GicaGate.GA2), GicaGate.GA3, gate_evidence=attacker_evidence(GicaGate.GA2))


@pytest.mark.parametrize("changes", [
    {"assurer": ATTACKER},
    {"criteria_version": "ATTACKER-CRITERIA"},
    {"policy_version": "ATTACKER-POLICY"},
    {"verifier": ATTACKER},
])
def test_attacker_selected_gate_trust_policy_denied(changes) -> None:
    malicious = evidence(GicaGate.GA2, assurance_pass=True, **changes)
    malicious = sign(replace(malicious, signature=""), EVIDENCE_KEY)
    with pytest.raises(ProgramTransitionError):
        advance(contract_at(GicaGate.GA2), GicaGate.GA3, gate_evidence=malicious)


def test_entirely_self_rooted_ga2_universe_denied() -> None:
    with pytest.raises(ProgramTransitionError):
        contract_at(GicaGate.GA2).transition_to(
            GicaGate.GA3,
            authority=attacker_authority(GicaGate.GA2, GicaGate.GA3),
            gate_evidence=attacker_evidence(GicaGate.GA2),
            now=NOW,
        )


def test_attacker_selected_founder_issuer_denied() -> None:
    target = contract_at(GicaGate.GA12, GicaProgramState.READY_FOR_FOUNDER, history=(GicaGate.GA11,))
    with pytest.raises(ProgramTransitionError, match="founder_reserved_authority_required"):
        target.founder_promote(authorization=attacker_founder(), now=NOW)


def test_attacker_selected_founder_key_denied() -> None:
    target = contract_at(GicaGate.GA12, GicaProgramState.READY_FOR_FOUNDER, history=(GicaGate.GA11,))
    malicious = sign(replace(founder(), signature=""), ATTACKER_KEY)
    with pytest.raises(ProgramTransitionError, match="founder_authorization_forged_denied"):
        target.founder_promote(authorization=malicious, now=NOW)


def test_entirely_self_rooted_founder_universe_denied() -> None:
    target = contract_at(GicaGate.GA12, GicaProgramState.READY_FOR_FOUNDER, history=(GicaGate.GA11,))
    with pytest.raises(ProgramTransitionError):
        target.founder_promote(authorization=attacker_founder(), now=NOW)


def test_externally_anchored_authority_evidence_permits_authorized_transition() -> None:
    assert advance(contract_at(GicaGate.GA3), GicaGate.GA4).gate is GicaGate.GA4


def test_externally_anchored_gate_evidence_is_accepted() -> None:
    assert advance(contract_at(GicaGate.GA4), GicaGate.GA5).gate is GicaGate.GA5


def test_externally_anchored_independent_ga2_assurance_permits_ga2_to_ga3() -> None:
    assert advance(contract_at(GicaGate.GA2), GicaGate.GA3, evidence(GicaGate.GA2, assurance_pass=True)).gate is GicaGate.GA3


def test_legitimate_ga11_to_ga12_sequence_succeeds() -> None:
    ga12 = advance(contract_at(GicaGate.GA11), GicaGate.GA12, evidence(GicaGate.GA11, assurance_pass=True))
    assert ga12.gate is GicaGate.GA12
    assert ga12.state is GicaProgramState.READY_FOR_FOUNDER
    assert ga12.gate_history[-1] is GicaGate.GA11


def test_directly_constructed_ga12_ready_with_synthetic_ga11_history_is_denied() -> None:
    target = contract_at(GicaGate.GA12, GicaProgramState.READY_FOR_FOUNDER, history=(GicaGate.GA11,))
    with pytest.raises(ProgramTransitionError, match="legitimate_ga11_to_ga12_transition_proof_required"):
        target.founder_promote(authorization=founder(), now=NOW)


def test_externally_anchored_reserved_founder_authorization_permits_complete_only_at_final_gate() -> None:
    ga12 = advance(contract_at(GicaGate.GA11), GicaGate.GA12, evidence(GicaGate.GA11, assurance_pass=True))
    assert ga12.founder_promote(authorization=founder(), now=NOW).state is GicaProgramState.COMPLETE
