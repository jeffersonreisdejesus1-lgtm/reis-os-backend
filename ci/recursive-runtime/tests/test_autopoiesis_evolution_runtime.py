import pytest

from autopoiesis_evolution_runtime import (
    AssuranceGateEngine, AssuranceResult, AutopoiesisEvolutionRuntime, BudgetEnvelope,
    ContinuousExecutor, ConvergenceEngine, ConvergenceInput, DurableExecutorJournal,
    EvidenceLedger, EvidenceRecord, EvolutionWorkspace, ExecutorEvent, ExecutorLease,
    GateContext, GateDisposition, ReconciliationStatus, Reversibility, SelfModelGate,
    SelfModelSnapshot, TrustClass,
)


def assurances(candidate="cand-2"):
    return (
        AssuranceResult("AGORA", "PASS", ("ev:a",), target_candidate_id=candidate),
        AssuranceResult("DEDALA", "PASS", ("ev:d",), target_candidate_id=candidate),
        AssuranceResult("SYNESIS", "PASS_WITH_RESERVATIONS", ("ev:s",), target_candidate_id=candidate, independent_target_access=True),
    )


def test_assurance_gate_deterministic_precedence_and_no_promotion():
    gate = AssuranceGateEngine()
    assert gate.evaluate(assurances(), GateContext(authority_known=False, normal_implementation_defect=True)) is GateDisposition.FAIL_CLOSED
    assert gate.evaluate(assurances(), GateContext(constitutional_boundary=True)) is GateDisposition.ESCALATE
    assert gate.evaluate(assurances(), GateContext(reversibility=Reversibility.IRREVERSIBLE)) is GateDisposition.HOLD
    assert gate.evaluate(assurances(), GateContext(normal_implementation_defect=True)) is GateDisposition.REPAIR
    assert gate.evaluate(assurances(), GateContext(converged=True)) is GateDisposition.CONVERGE
    assert not hasattr(GateDisposition, "PROMOTE")


def test_assurance_requires_synesis_independent_target_access():
    rows = list(assurances())
    rows[-1] = AssuranceResult("SYNESIS", "PASS", ("ev:s",), independent_target_access=False)
    assert AssuranceGateEngine().evaluate(rows, GateContext(converged=True)) is GateDisposition.HOLD


def test_high_critical_blocks_and_missing_layer_holds():
    rows = list(assurances())
    rows[1] = AssuranceResult("DEDALA", "PASS", ("ev:d",), unresolved_high_critical=True)
    assert AssuranceGateEngine().evaluate(rows, GateContext()) is GateDisposition.HOLD
    assert AssuranceGateEngine().evaluate(rows[:2], GateContext()) is GateDisposition.HOLD


def test_candidate_cannot_mutate_canonical():
    ws = EvolutionWorkspace("main:abc", "candidate:def")
    ws.assert_mutation_target("candidate:def")
    with pytest.raises(RuntimeError, match="CANONICAL_MUTATION_FORBIDDEN"):
        ws.assert_mutation_target("main:abc")


def test_evidence_ledger_preserves_trust_and_detects_conflict():
    ledger = EvidenceLedger()
    ev = EvidenceRecord("e1", "AGORA", "LOCAL", "pytest:1", "abc", "local", "AGORA", 1.0, None, TrustClass.TOOL_OBSERVED)
    ledger.record(ev)
    assert ledger.get("e1").trust_class is TrustClass.TOOL_OBSERVED
    conflict = EvidenceRecord("e1", "AGORA", "LOCAL", "pytest:2", "def", "local", "AGORA", 2.0, None, TrustClass.CANONICAL_RECORD)
    with pytest.raises(RuntimeError, match="EVIDENCE_ID_CONFLICT"):
        ledger.record(conflict)


def test_self_model_freshness_rules():
    matched = SelfModelSnapshot("sm1", "main1", 100.0, 10.0, ReconciliationStatus.MATCHED, "AUTH:1")
    assert SelfModelGate.evaluate(matched, now=105.0) is GateDisposition.CONTINUE
    assert SelfModelGate.evaluate(matched, now=111.0) is GateDisposition.HOLD
    unknown = SelfModelSnapshot("sm1", "main1", 100.0, 10.0, ReconciliationStatus.UNKNOWN, "AUTH:1")
    assert SelfModelGate.evaluate(unknown, now=105.0) is GateDisposition.FAIL_CLOSED


def test_child_budget_never_exceeds_parent():
    parent = BudgetEnvelope(100, 1000, 0.0, 5, 20)
    child = parent.delegate(time=50, tokens=500, cost=0.0, recursions=2, change_surface=10)
    assert child.max_recursions == 2
    with pytest.raises(RuntimeError, match="CHILD_BUDGET_EXCEEDS_PARENT"):
        parent.delegate(time=101, tokens=1, cost=0, recursions=1, change_surface=1)


def test_convergence_is_bounded_and_auditable():
    engine = ConvergenceEngine(min_expected_gain=1.0, convergence_threshold=5.0)
    recurse = ConvergenceInput(4, 1, 1, 0, 1, 5, 0, 3, True, False, False)
    converge = ConvergenceInput(8, 1, 1, 0, 2, 5, 0, 3, True, False, False)
    exhausted = ConvergenceInput(8, 1, 1, 0, 5, 5, 0, 3, True, False, False)
    assert engine.decide(recurse) is GateDisposition.RECURSE
    assert engine.decide(converge) is GateDisposition.CONVERGE
    assert engine.decide(exhausted) is GateDisposition.HOLD


def test_executor_idle_means_zero_inference_and_expired_lease_holds(tmp_path):
    clock = [100.0]
    lease = ExecutorLease("exec-1", "lease-1", "mission:a", 1, 110.0)
    ex = ContinuousExecutor(lease=lease, now=lambda: clock[0], journal=DurableExecutorJournal(tmp_path / "journal.jsonl"))
    assert ex.run_once(lambda _: GateDisposition.CONTINUE) == "IDLE"
    assert ex.model_inference_count == 0
    ex.enqueue(ExecutorEvent("ev1", "mission:a", "payload:1"))
    clock[0] = 111.0
    assert ex.run_once(lambda _: GateDisposition.CONTINUE) is GateDisposition.HOLD
    assert ex.model_inference_count == 0


def test_stale_executor_fails_closed(tmp_path):
    lease = ExecutorLease("exec-1", "lease-1", "mission:a", 1, 999.0)
    ex = ContinuousExecutor(lease=lease, now=lambda: 100.0, journal=DurableExecutorJournal(tmp_path / "journal.jsonl"))
    ex.enqueue(ExecutorEvent("ev1", "mission:a", "payload:1"))
    ex.replace_active_writer(instance_id="exec-2", epoch=2)
    assert ex.run_once(lambda _: GateDisposition.CONTINUE) is GateDisposition.FAIL_CLOSED


def test_executor_journal_replays_unfinished(tmp_path):
    journal = DurableExecutorJournal(tmp_path / "journal.jsonl")
    lease = ExecutorLease("exec-1", "lease-1", "mission:a", 1, 999.0)
    ex = ContinuousExecutor(lease=lease, now=lambda: 100.0, journal=journal)
    ex.enqueue(ExecutorEvent("ev1", "mission:a", "payload:1"))
    assert ex.replay_unfinished() == ("ev1",)
    assert ex.run_once(lambda _: GateDisposition.CONTINUE) is GateDisposition.CONTINUE
    assert ex.replay_unfinished() == ()


def test_end_to_end_trial_recurse_then_qualify_without_canonical_mutation():
    runtime = AutopoiesisEvolutionRuntime(
        gate_engine=AssuranceGateEngine(),
        convergence=ConvergenceEngine(min_expected_gain=1.0, convergence_threshold=5.0),
    )
    ws = EvolutionWorkspace("main:canonical", "candidate:v1")
    model = SelfModelSnapshot("sm:v1", "main:canonical", 100.0, 60.0, ReconciliationStatus.MATCHED, "AUTH:FOUNDER")
    budget = BudgetEnvelope(1000, 10000, 0.0, 3, 10)
    cycles = (
        ConvergenceInput(4, 1, 1, 0, 0, 3, 0, 2, True, False, False),
        ConvergenceInput(8, 1, 1, 0, 1, 3, 0, 2, True, False, False),
    )
    out = runtime.run_trial(
        mission_id="trial:1", workspace=ws, model=model, now=110.0, budget=budget,
        cycle_inputs=cycles, assurance_factory=lambda _: assurances("candidate:v1"),
    )
    assert out.state == "QUALIFIED"
    assert out.recommendation == "PROMOTION_ELIGIBLE"
    assert out.cycles == 2
    assert out.canonical_version == "main:canonical"
    assert out.candidate_version == "candidate:v1"
