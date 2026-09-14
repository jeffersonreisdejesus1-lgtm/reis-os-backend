from app.materialization.authority import AuthorityBoundary, MutationKind
from app.materialization.coi import CognitiveOperationalIntegration, CoiDisposition
from app.materialization.factory import FactoryPhase, SoftwareFactory
from app.materialization.recursive_engine import RecursiveEngine


def test_unknown_actor_fails_closed() -> None:
    decision = AuthorityBoundary().decide(actor="UNKNOWN", kind=MutationKind.EDIT_FILE)
    assert decision.allowed is False


def test_development_edit_does_not_require_founder() -> None:
    decision = AuthorityBoundary().decide(actor="SOFIA", kind=MutationKind.EDIT_FILE)
    assert decision.allowed is True


def test_merge_and_self_promotion_denied_without_founder() -> None:
    boundary = AuthorityBoundary()
    assert boundary.decide(actor="SOFIA", kind=MutationKind.MERGE).allowed is False
    assert boundary.decide(actor="SOFIA", kind=MutationKind.SELF_PROMOTION).allowed is False
    assert boundary.decide(
        actor="FOUNDER", kind=MutationKind.MERGE, founder_authorized=True
    ).allowed is True


def test_factory_packages_candidate_without_promoting() -> None:
    receipt = SoftwareFactory().run(actor="SOFIA", mission_id="M1", spec="ledger formatBrl")
    assert receipt.phase == FactoryPhase.QUALIFY_HANDOFF
    assert receipt.promoted is False
    assert receipt.material is False
    assert receipt.logical_candidate is True
    assert receipt.qualifies_for_handoff is False


def test_factory_empty_spec_fails() -> None:
    receipt = SoftwareFactory().run(actor="SOFIA", mission_id="M1", spec="  ")
    assert receipt.phase == FactoryPhase.FAILED
    assert receipt.failure == "empty_spec"


def test_factory_unavailable_executor_hold() -> None:
    receipt = SoftwareFactory().run(
        actor="SOFIA", mission_id="M1", spec="x", executor="MISSING"
    )
    assert receipt.phase == FactoryPhase.HOLD
    assert receipt.failure == "executor_unavailable"
    assert receipt.qualifies_for_handoff is False


def test_recursive_engine_terminates_and_does_not_gain_authority() -> None:
    receipt = RecursiveEngine(max_depth=3).run(
        actor="SOFIA", mission_id="M1", initial_state="idle", goal="done"
    )
    assert receipt.terminated is True
    assert receipt.authority_gained is False


def test_recursive_cycle_detection() -> None:
    engine = RecursiveEngine(max_depth=5)
    receipt = engine.run(
        actor="SOFIA",
        mission_id="M-CYCLE",
        initial_state="loop",
        goal="never",
        step=lambda current, index: "loop",
    )
    assert receipt.termination_reason == "cycle_detected"
    assert receipt.authority_gained is False


def test_recursive_replay_does_not_duplicate_effect() -> None:
    engine = RecursiveEngine(max_depth=2)
    first = engine.run(actor="SOFIA", mission_id="M-R", initial_state="s", goal="s|nudge:1")
    second = engine.run(actor="SOFIA", mission_id="M-R", initial_state="s", goal="s|nudge:1")
    assert first.replayed is False
    assert second.replayed is True
    assert second.termination_reason == "replay_blocked"


def test_coi_hold_candidate_not_institutional_pass() -> None:
    receipt = CognitiveOperationalIntegration().realize(
        actor="SOFIA",
        identity="ocs://sofia",
        intent="materialize factory slice",
        mission_id="M-COI",
        bound_object="object://cupuwa-p0",
    )
    assert receipt.disposition == CoiDisposition.CANDIDATE
    assert receipt.promoted is False
    assert receipt.bound_object == "object://cupuwa-p0"


def test_coi_without_identity_denied() -> None:
    receipt = CognitiveOperationalIntegration().realize(
        actor="SOFIA", identity="", intent="x", mission_id="M-COI", bound_object="o"
    )
    assert receipt.disposition == CoiDisposition.DENIED
    assert receipt.failure == "identity_binding_required"


def test_coi_missing_bound_object_hold() -> None:
    receipt = CognitiveOperationalIntegration().realize(
        actor="SOFIA", identity="ocs://sofia", intent="x", mission_id="M-COI"
    )
    assert receipt.disposition == CoiDisposition.HOLD
    assert receipt.failure == "missing_bound_object"


def test_coi_missing_executor_hold() -> None:
    receipt = CognitiveOperationalIntegration().realize(
        actor="SOFIA",
        identity="ocs://sofia",
        intent="x",
        mission_id="M-COI",
        bound_object="o",
        executor="REPLIT-MISSING",
    )
    assert receipt.disposition == CoiDisposition.HOLD
    assert receipt.failure == "executor_unavailable"


def test_coi_material_failure_is_not_execution_claim() -> None:
    receipt = CognitiveOperationalIntegration().realize(
        actor="SOFIA",
        identity="ocs://sofia",
        intent="x",
        mission_id="M-COI",
        bound_object="o",
        force_material_failure=True,
    )
    assert receipt.disposition == CoiDisposition.FAILED
    assert receipt.readback == "NO_CLAIM_OF_EXECUTION"


def test_coi_readback_mismatch_hold() -> None:
    receipt = CognitiveOperationalIntegration().realize(
        actor="SOFIA",
        identity="ocs://sofia",
        intent="x",
        mission_id="M-COI-RB",
        bound_object="o",
        force_readback_mismatch=True,
    )
    assert receipt.disposition == CoiDisposition.HOLD
    assert receipt.failure == "readback_mismatch"
