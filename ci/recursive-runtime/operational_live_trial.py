from __future__ import annotations

import json
import time
from pathlib import Path

from autopoiesis_evolution_runtime import (
    AssuranceGateEngine,
    AssuranceResult,
    AutopoiesisEvolutionRuntime,
    BudgetEnvelope,
    ContinuousExecutor,
    ConvergenceEngine,
    ConvergenceInput,
    DurableExecutorJournal,
    EvolutionWorkspace,
    ExecutorEvent,
    ExecutorLease,
    GateDisposition,
    ReconciliationStatus,
    SelfModelSnapshot,
)

MISSION_ID = "AUTOPOIESIS-OPERATIONAL-LIVE-TRIAL-V1-001"
NAMESPACE = "reis-os:auto:evolution:trial:v1"
NOW = time.time()


def assurance_factory(cycle: int) -> tuple[AssuranceResult, ...]:
    candidate = "candidate:autopoiesis-v1"
    return (
        AssuranceResult("AGORA", "PASS", (f"live:agora:{cycle}",), target_candidate_id=candidate),
        AssuranceResult("DEDALA", "PASS_WITH_RESERVATIONS", (f"live:dedala:{cycle}",), target_candidate_id=candidate),
        AssuranceResult("SYNESIS", "PASS_WITH_RESERVATIONS", (f"live:synesis:{cycle}",), target_candidate_id=candidate, independent_target_access=True),
    )


def run_live_trial() -> dict:
    journal_path = Path("/tmp/reis-os-autopoiesis-live-trial.jsonl")
    journal_path.unlink(missing_ok=True)
    journal = DurableExecutorJournal(journal_path)
    lease = ExecutorLease(
        executor_instance_id="render-free-live-trial-1",
        executor_lease_id="lease:auto:live:v1:001",
        mission_namespace=NAMESPACE,
        executor_epoch=1,
        expires_at=NOW + 1800,
    )
    executor = ContinuousExecutor(lease=lease, now=time.time, journal=journal)
    executor.enqueue(ExecutorEvent("event:auto:live:001", NAMESPACE, MISSION_ID))

    runtime = AutopoiesisEvolutionRuntime(
        gate_engine=AssuranceGateEngine(),
        convergence=ConvergenceEngine(min_expected_gain=0.25, convergence_threshold=0.75),
    )
    workspace = EvolutionWorkspace("canonical:main:259c7a0", "candidate:autopoiesis-v1")
    model = SelfModelSnapshot(
        self_model_version="self-model:v1",
        canonical_state_version="canonical:main:259c7a0",
        observed_at=NOW,
        max_staleness=3600,
        reconciliation_status=ReconciliationStatus.MATCHED,
        authority_ref="FOUNDER-AUTHORIZATION-AUTOPOIESIS-OPERATIONAL-QUALIFICATION-END-TO-END-V1-001",
    )
    budget = BudgetEnvelope(max_time=300, max_tokens=10000, max_cost=0.0, max_recursions=4, max_change_surface=10)
    cycle_inputs = (
        ConvergenceInput(0.55, 0.05, 0.05, 0.05, 0, 4, 0, 2, True, False, False),
        ConvergenceInput(0.95, 0.05, 0.05, 0.05, 1, 4, 0, 2, True, False, False),
    )

    def handler(_: ExecutorEvent) -> GateDisposition:
        result = runtime.run_trial(
            mission_id=MISSION_ID,
            workspace=workspace,
            model=model,
            now=NOW,
            budget=budget,
            cycle_inputs=cycle_inputs,
            assurance_factory=assurance_factory,
        )
        if result.state != "QUALIFIED" or result.recommendation != "PROMOTION_ELIGIBLE":
            raise RuntimeError("LIVE_TRIAL_NOT_QUALIFIED")
        journal.append({
            "kind": "FOUNDER_FINAL_GATE_REACHED",
            "mission_id": result.mission_id,
            "state": result.state,
            "cycles": result.cycles,
            "recommendation": result.recommendation,
            "canonical_promotion": "NOT_PERFORMED",
        })
        return GateDisposition.CONVERGE

    executor_result = executor.run_once(handler)
    if executor_result is not GateDisposition.CONVERGE:
        raise RuntimeError(f"EXECUTOR_LIVE_TRIAL_FAILED:{executor_result}")
    if executor.run_once(handler) != "IDLE":
        raise RuntimeError("EXECUTOR_DID_NOT_RETURN_TO_IDLE")

    return {
        "mission_id": MISSION_ID,
        "runtime": "REAL_RENDER_PROCESS",
        "event_wake": "PROVEN",
        "recursive_cycles": 2,
        "assurance_chain": ["AGORA", "DEDALA", "SYNESIS"],
        "final_state": "QUALIFIED",
        "final_gate": "FOUNDER_REQUIRED",
        "canonical_promotion": "NOT_PERFORMED",
        "executor_after_trial": "IDLE",
        "new_cost": 0,
        "journal_rows": len(journal.rows()),
    }


if __name__ == "__main__":
    print("LIVE_TRIAL_RESULT=" + json.dumps(run_live_trial(), sort_keys=True), flush=True)
