from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Callable, Iterable


class GateDisposition(str, Enum):
    CONTINUE = "CONTINUE"
    REPAIR = "REPAIR"
    RECURSE = "RECURSE"
    CONVERGE = "CONVERGE"
    HOLD = "HOLD"
    ESCALATE = "ESCALATE"
    STOP = "STOP"
    FAIL_CLOSED = "FAIL_CLOSED"


class TrustClass(str, Enum):
    SELF_REPORTED = "SELF_REPORTED"
    TOOL_OBSERVED = "TOOL_OBSERVED"
    EXTERNAL_PROVIDER_RECEIPT = "EXTERNAL_PROVIDER_RECEIPT"
    INDEPENDENT_REPRODUCTION = "INDEPENDENT_REPRODUCTION"
    CANONICAL_RECORD = "CANONICAL_RECORD"


class ReconciliationStatus(str, Enum):
    MATCHED = "MATCHED"
    STALE = "STALE"
    DIVERGED = "DIVERGED"
    UNKNOWN = "UNKNOWN"


class Reversibility(str, Enum):
    REVERSIBLE = "REVERSIBLE"
    COMPENSATABLE = "COMPENSATABLE"
    IRREVERSIBLE = "IRREVERSIBLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    producer: str
    provider: str
    source_ref: str
    artifact_hash: str
    execution_environment: str
    observed_by: str
    timestamp: float
    causal_parent: str | None
    trust_class: TrustClass

    def fingerprint(self) -> str:
        payload = json.dumps({
            "evidence_id": self.evidence_id,
            "producer": self.producer,
            "provider": self.provider,
            "source_ref": self.source_ref,
            "artifact_hash": self.artifact_hash,
            "execution_environment": self.execution_environment,
            "observed_by": self.observed_by,
            "timestamp": self.timestamp,
            "causal_parent": self.causal_parent,
            "trust_class": self.trust_class.value,
        }, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


class EvidenceLedger:
    """Auri-like provenance ledger. Recording never upgrades trust."""
    def __init__(self):
        self._records: dict[str, EvidenceRecord] = {}
        self._fingerprints: dict[str, str] = {}

    def record(self, evidence: EvidenceRecord) -> EvidenceRecord:
        fp = evidence.fingerprint()
        existing = self._records.get(evidence.evidence_id)
        if existing is not None:
            if self._fingerprints[evidence.evidence_id] != fp:
                raise RuntimeError("EVIDENCE_ID_CONFLICT")
            return existing
        if evidence.causal_parent is not None and evidence.causal_parent not in self._records:
            raise RuntimeError("EVIDENCE_CAUSAL_PARENT_UNKNOWN")
        self._records[evidence.evidence_id] = evidence
        self._fingerprints[evidence.evidence_id] = fp
        return evidence

    def get(self, evidence_id: str) -> EvidenceRecord:
        return self._records[evidence_id]

    def all(self) -> tuple[EvidenceRecord, ...]:
        return tuple(self._records.values())


@dataclass(frozen=True)
class SelfModelSnapshot:
    self_model_version: str
    canonical_state_version: str
    observed_at: float
    max_staleness: float
    reconciliation_status: ReconciliationStatus
    authority_ref: str


class SelfModelGate:
    @staticmethod
    def evaluate(snapshot: SelfModelSnapshot, *, now: float, authority_known: bool = True) -> GateDisposition:
        if not authority_known or snapshot.reconciliation_status is ReconciliationStatus.UNKNOWN:
            return GateDisposition.FAIL_CLOSED
        if now - snapshot.observed_at > snapshot.max_staleness:
            return GateDisposition.HOLD
        if snapshot.reconciliation_status in (ReconciliationStatus.STALE, ReconciliationStatus.DIVERGED):
            return GateDisposition.HOLD
        return GateDisposition.CONTINUE


@dataclass(frozen=True)
class EvolutionWorkspace:
    canonical_version: str
    candidate_version: str

    def __post_init__(self):
        if self.canonical_version == self.candidate_version:
            raise RuntimeError("CANDIDATE_MUST_DIFFER_FROM_CANONICAL")

    def assert_mutation_target(self, target_version: str) -> None:
        if target_version == self.canonical_version:
            raise RuntimeError("CANONICAL_MUTATION_FORBIDDEN")
        if target_version != self.candidate_version:
            raise RuntimeError("UNKNOWN_CANDIDATE_TARGET")


@dataclass(frozen=True)
class BudgetEnvelope:
    max_time: float
    max_tokens: int
    max_cost: float
    max_recursions: int
    max_change_surface: int

    def delegate(self, *, time: float, tokens: int, cost: float, recursions: int, change_surface: int) -> "BudgetEnvelope":
        values = (time, tokens, cost, recursions, change_surface)
        if any(v < 0 for v in values):
            raise RuntimeError("NEGATIVE_BUDGET_FORBIDDEN")
        if time > self.max_time or tokens > self.max_tokens or cost > self.max_cost or recursions > self.max_recursions or change_surface > self.max_change_surface:
            raise RuntimeError("CHILD_BUDGET_EXCEEDS_PARENT")
        return BudgetEnvelope(time, tokens, cost, recursions, change_surface)


@dataclass(frozen=True)
class AssuranceResult:
    layer: str
    status: str
    evidence_refs: tuple[str, ...]
    unresolved_high_critical: bool = False
    target_candidate_id: str = ""
    independent_target_access: bool = True


@dataclass(frozen=True)
class GateContext:
    authority_known: bool = True
    constitutional_boundary: bool = False
    identity_change: bool = False
    new_organism_class: bool = False
    reversibility: Reversibility = Reversibility.REVERSIBLE
    cost_breach: bool = False
    required_evidence_impossible: bool = False
    assurance_deadlock: bool = False
    credential_provisioning_required: bool = False
    normal_implementation_defect: bool = False
    evidence_complete: bool = True
    converged: bool = False


class AssuranceGateEngine:
    """Deterministic policy engine. It never grants canonical promotion."""
    REQUIRED_LAYERS = ("AGORA", "DEDALA", "SYNESIS")

    def evaluate(self, results: Iterable[AssuranceResult], context: GateContext) -> GateDisposition:
        results = tuple(results)
        if not context.authority_known:
            return GateDisposition.FAIL_CLOSED
        if context.constitutional_boundary:
            return GateDisposition.ESCALATE
        if context.identity_change:
            return GateDisposition.ESCALATE
        if context.new_organism_class:
            return GateDisposition.ESCALATE
        if context.reversibility in (Reversibility.IRREVERSIBLE, Reversibility.UNKNOWN):
            return GateDisposition.HOLD
        if context.cost_breach:
            return GateDisposition.HOLD
        if any(r.unresolved_high_critical for r in results):
            return GateDisposition.HOLD
        if context.required_evidence_impossible:
            return GateDisposition.ESCALATE
        if context.assurance_deadlock:
            return GateDisposition.ESCALATE
        if context.credential_provisioning_required:
            return GateDisposition.ESCALATE
        if context.normal_implementation_defect:
            return GateDisposition.REPAIR
        if not context.evidence_complete:
            return GateDisposition.HOLD

        by_layer = {r.layer: r for r in results}
        if any(layer not in by_layer for layer in self.REQUIRED_LAYERS):
            return GateDisposition.HOLD
        syn = by_layer["SYNESIS"]
        if not syn.independent_target_access or not syn.evidence_refs:
            return GateDisposition.HOLD
        if any(by_layer[layer].status not in ("PASS", "PASS_WITH_RESERVATIONS") for layer in self.REQUIRED_LAYERS):
            return GateDisposition.REPAIR
        return GateDisposition.CONVERGE if context.converged else GateDisposition.CONTINUE


@dataclass(frozen=True)
class ConvergenceInput:
    benefit_score: float
    regression_penalty: float
    change_surface_penalty: float
    uncertainty_penalty: float
    recursion_depth: int
    max_recursion_depth: int
    failed_iterations: int
    max_failed_iterations: int
    authority_boundary_preserved: bool
    blocking_assurance: bool
    exception_interrupt: bool


class ConvergenceEngine:
    def __init__(self, *, min_expected_gain: float, convergence_threshold: float):
        self.min_expected_gain = min_expected_gain
        self.convergence_threshold = convergence_threshold

    @staticmethod
    def score(inp: ConvergenceInput) -> float:
        return inp.benefit_score - inp.regression_penalty - inp.change_surface_penalty - inp.uncertainty_penalty

    def decide(self, inp: ConvergenceInput) -> GateDisposition:
        if not inp.authority_boundary_preserved:
            return GateDisposition.ESCALATE
        if inp.blocking_assurance or inp.exception_interrupt:
            return GateDisposition.HOLD
        if inp.recursion_depth >= inp.max_recursion_depth or inp.failed_iterations >= inp.max_failed_iterations:
            return GateDisposition.HOLD
        gain = self.score(inp)
        if gain >= self.convergence_threshold:
            return GateDisposition.CONVERGE
        if gain >= self.min_expected_gain:
            return GateDisposition.RECURSE
        return GateDisposition.HOLD


@dataclass(frozen=True)
class ExecutorLease:
    executor_instance_id: str
    executor_lease_id: str
    mission_namespace: str
    executor_epoch: int
    expires_at: float


@dataclass(frozen=True)
class ExecutorEvent:
    event_id: str
    mission_namespace: str
    payload_ref: str


class DurableExecutorJournal:
    """Single-node fsync JSONL journal for V1 qualification."""
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(self, row: dict) -> None:
        line = json.dumps(row, sort_keys=True) + "\n"
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            import os
            os.fsync(f.fileno())

    def rows(self) -> tuple[dict, ...]:
        return tuple(json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip())


class ContinuousExecutor:
    """Event-driven executor: no pending work means no model inference."""
    def __init__(self, *, lease: ExecutorLease, now: Callable[[], float], journal: DurableExecutorJournal):
        self.lease = lease
        self.now = now
        self.journal = journal
        self._queue: deque[ExecutorEvent] = deque()
        self._active_writer: dict[str, tuple[str, int]] = {lease.mission_namespace: (lease.executor_instance_id, lease.executor_epoch)}
        self.model_inference_count = 0

    @property
    def state(self) -> str:
        return "IDLE" if not self._queue else "READY"

    def enqueue(self, event: ExecutorEvent) -> None:
        if event.mission_namespace != self.lease.mission_namespace:
            raise RuntimeError("MISSION_NAMESPACE_MISMATCH")
        self._queue.append(event)
        self.journal.append({"kind": "EXECUTOR_EVENT_ENQUEUED", "event_id": event.event_id, "mission_namespace": event.mission_namespace, "payload_ref": event.payload_ref})

    def replace_active_writer(self, *, instance_id: str, epoch: int) -> None:
        if epoch <= self.lease.executor_epoch:
            raise RuntimeError("EXECUTOR_EPOCH_MUST_ADVANCE")
        self._active_writer[self.lease.mission_namespace] = (instance_id, epoch)

    def _validate_lease(self) -> GateDisposition:
        if self.now() >= self.lease.expires_at:
            return GateDisposition.HOLD
        active = self._active_writer[self.lease.mission_namespace]
        if active != (self.lease.executor_instance_id, self.lease.executor_epoch):
            return GateDisposition.FAIL_CLOSED
        return GateDisposition.CONTINUE

    def run_once(self, handler: Callable[[ExecutorEvent], GateDisposition]) -> GateDisposition | str:
        if not self._queue:
            return "IDLE"
        valid = self._validate_lease()
        if valid is not GateDisposition.CONTINUE:
            return valid
        event = self._queue.popleft()
        self.journal.append({"kind": "EXECUTOR_EVENT_INTENT", "event_id": event.event_id, "epoch": self.lease.executor_epoch})
        self.model_inference_count += 1
        result = handler(event)
        self.journal.append({"kind": "EXECUTOR_EVENT_RESULT", "event_id": event.event_id, "result": result.value})
        return result

    def replay_unfinished(self) -> tuple[str, ...]:
        rows = self.journal.rows()
        enqueued = {r["event_id"]: r for r in rows if r.get("kind") == "EXECUTOR_EVENT_ENQUEUED"}
        completed = {r["event_id"] for r in rows if r.get("kind") == "EXECUTOR_EVENT_RESULT"}
        return tuple(sorted(set(enqueued) - completed))


@dataclass(frozen=True)
class EvolutionTrialResult:
    mission_id: str
    state: str
    cycles: int
    canonical_version: str
    candidate_version: str
    gate: GateDisposition
    recommendation: str


class AutopoiesisEvolutionRuntime:
    """Bounded V1 qualification runtime. It can qualify a candidate, never promote it."""
    def __init__(self, *, gate_engine: AssuranceGateEngine, convergence: ConvergenceEngine):
        self.gate_engine = gate_engine
        self.convergence = convergence

    def run_trial(
        self,
        *,
        mission_id: str,
        workspace: EvolutionWorkspace,
        model: SelfModelSnapshot,
        now: float,
        budget: BudgetEnvelope,
        cycle_inputs: Iterable[ConvergenceInput],
        assurance_factory: Callable[[int], tuple[AssuranceResult, ...]],
    ) -> EvolutionTrialResult:
        workspace.assert_mutation_target(workspace.candidate_version)
        model_gate = SelfModelGate.evaluate(model, now=now, authority_known=True)
        if model_gate is not GateDisposition.CONTINUE:
            return EvolutionTrialResult(mission_id, "HOLD", 0, workspace.canonical_version, workspace.candidate_version, model_gate, "RETURN_FOR_REWORK")
        cycles = 0
        for inp in cycle_inputs:
            if cycles >= budget.max_recursions:
                return EvolutionTrialResult(mission_id, "HOLD", cycles, workspace.canonical_version, workspace.candidate_version, GateDisposition.HOLD, "RETURN_FOR_REWORK")
            cycles += 1
            conv = self.convergence.decide(inp)
            if conv is GateDisposition.RECURSE:
                continue
            if conv is not GateDisposition.CONVERGE:
                return EvolutionTrialResult(mission_id, "HOLD", cycles, workspace.canonical_version, workspace.candidate_version, conv, "RETURN_FOR_REWORK")
            assurance = assurance_factory(cycles)
            gate = self.gate_engine.evaluate(assurance, GateContext(converged=True))
            if gate is GateDisposition.CONVERGE:
                return EvolutionTrialResult(mission_id, "QUALIFIED", cycles, workspace.canonical_version, workspace.candidate_version, gate, "PROMOTION_ELIGIBLE")
            if gate is GateDisposition.REPAIR:
                continue
            return EvolutionTrialResult(mission_id, "HOLD", cycles, workspace.canonical_version, workspace.candidate_version, gate, "RETURN_FOR_REWORK")
        return EvolutionTrialResult(mission_id, "HOLD", cycles, workspace.canonical_version, workspace.candidate_version, GateDisposition.HOLD, "RETURN_FOR_REWORK")
