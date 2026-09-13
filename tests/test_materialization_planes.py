from app.materialization.authority import AuthorityBoundary, MutationKind
from app.materialization.coi import CognitiveOperationalIntegration, CoiDisposition
from app.materialization.factory import FactoryPhase, SoftwareFactory
from app.materialization.recursive_engine import RecursiveEngine


def test_unknown_actor_fails_closed() -> None:
    decision = AuthorityBoundary().decide(actor="UNKNOWN", kind=MutationKind.EDIT_FILE)
    assert decision.allowed is False
    assert decision.reason == "unknown_authority_fail_closed"


def test_development_edit_does_not_require_founder() -> None:
    decision = AuthorityBoundary().decide(actor="SOFIA", kind=MutationKind.EDIT_FILE)
    assert decision.allowed is True
    assert decision.plane.value == "development"


def test_merge_and_self_promotion_denied_without_founder() -> None:
    boundary = AuthorityBoundary()
    merge = boundary.decide(actor="SOFIA", kind=MutationKind.MERGE)
    promo = boundary.decide(actor="SOFIA", kind=MutationKind.SELF_PROMOTION)
    assert merge.allowed is False
    assert promo.allowed is False
    founder_merge = boundary.decide(
        actor="FOUNDER", kind=MutationKind.MERGE, founder_authorized=True
    )
    assert founder_merge.allowed is True


def test_factory_packages_candidate_without_promoting() -> None:
    receipt = SoftwareFactory().run(
        actor="SOFIA", mission_id="M1", spec="ledger formatBrl"
    )
    assert receipt.phase == FactoryPhase.QUALIFY_HANDOFF
    assert receipt.candidate_packaged is True
    assert receipt.promoted is False
    assert receipt.evidence
    assert receipt.qualifies_for_handoff is True


def test_factory_empty_spec_fails() -> None:
    receipt = SoftwareFactory().run(actor="SOFIA", mission_id="M1", spec="  ")
    assert receipt.phase == FactoryPhase.FAILED
    assert receipt.failure == "empty_spec"


def test_recursive_engine_terminates_and_does_not_gain_authority() -> None:
    receipt = RecursiveEngine(max_depth=3).run(
        actor="SOFIA", mission_id="M1", initial_state="idle", goal="done"
    )
    assert receipt.terminated is True
    assert receipt.authority_gained is False
    assert 1 <= len(receipt.iterations) <= 3


def test_coi_hold_candidate_not_institutional_pass() -> None:
    receipt = CognitiveOperationalIntegration().realize(
        actor="SOFIA",
        identity="ocs://sofia",
        intent="materialize factory slice",
        mission_id="M-COI",
    )
    assert receipt.disposition == CoiDisposition.CANDIDATE
    assert receipt.promoted is False
    assert receipt.evidence_hash
    assert receipt.readback


def test_coi_without_identity_denied() -> None:
    receipt = CognitiveOperationalIntegration().realize(
        actor="SOFIA",
        identity="",
        intent="x",
        mission_id="M-COI",
    )
    assert receipt.disposition == CoiDisposition.DENIED
    assert receipt.failure == "identity_binding_required"
