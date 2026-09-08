from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from noesis.runtime import Noesis, NOESIS_CURRENT_EC, NOESIS_ID, RUNTIME_ID, binding_hash


class RefactorInvariantError(RuntimeError):
    pass


class RefactorStage(str, Enum):
    R1_BLACKBOARD = "R1_EXPLICIT_STATE_BLACKBOARD"
    R2_PROGRESS_MONITOR = "R2_PROGRESS_MONITOR"
    R3_TYPED_TRANSITIONS = "R3_TYPED_TRANSITIONS"
    R4_SCHEDULER = "R4_SCHEDULER"
    R5_TELEMETRY = "R5_TELEMETRY"
    R6_FORMAL_CHECKS = "R6_FORMAL_CHECKS"


class RelationType(str, Enum):
    CONTINUE = "CONTINUE"
    METHOD_CHANGE = "METHOD_CHANGE"
    HANDOFF_FOR_CONFORMANCE = "HANDOFF_FOR_CONFORMANCE"
    RETURNS_FINDING_TO = "RETURNS_FINDING_TO"
    ESCALATE_TO_FOUNDER = "ESCALATE_TO_FOUNDER"
    FOUNDER_AUTHORIZES = "FOUNDER_AUTHORIZES"
    STOP = "STOP"


class CycleDisposition(str, Enum):
    CONTINUE = "CONTINUE"
    METHOD_CHANGE = "METHOD_CHANGE"
    HANDOFF = "HANDOFF"
    ESCALATE = "ESCALATE"
    STOP = "STOP"
    BLOCKED = "BLOCKED"


FORBIDDEN_ACTIONS = frozenset({
    "SELF_ASSURANCE",
    "SELF_PROMOTION",
    "CREATE_AUTHORITY",
    "MERGE",
    "PRODUCTION",
    "CANONICAL_WRITE",
    "FOUNDER_PROMOTION",
    "BYPASS_FOUNDER_GATE",
})


@dataclass
class Blackboard:
    mission_id: str
    current_object: str
    current_phase: str = "INTAKE"
    current_actor: str = "NOESIS"
    last_action: str = "BIND"
    last_material_delta: Dict[str, Any] = field(default_factory=dict)
    open_findings: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    pending_gates: List[str] = field(default_factory=list)
    authorized_next_actors: List[str] = field(default_factory=list)
    prohibited_transitions: List[str] = field(default_factory=lambda: sorted(FORBIDDEN_ACTIONS))
    stop_conditions: List[str] = field(default_factory=lambda: [
        "BOUND_COMPLETE",
        "NO_PROGRESS_THRESHOLD",
        "FAIL",
        "FOUNDER_HOLD",
    ])
    decisions: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    verified_claims: List[str] = field(default_factory=list)
    stagnation_cycles: int = 0
    stopped: bool = False
    stop_reason: Optional[str] = None
    cycle: int = 0

    def snapshot(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MaterialDelta:
    evidence: int = 0
    state: int = 0
    findings: int = 0
    blockers: int = 0
    decisions: int = 0
    verified_claims: int = 0

    @property
    def total(self) -> int:
        return self.evidence + self.state + self.findings + self.blockers + self.decisions + self.verified_claims

    @property
    def material(self) -> bool:
        return self.total > 0

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class TypedTransition:
    source: str
    relation: RelationType
    target: str
    object_id: str
    reason: str
    authority_transferred: bool = False

    def __post_init__(self) -> None:
        if self.authority_transferred:
            raise RefactorInvariantError("HANDOFF_MUST_NOT_TRANSFER_AUTHORITY")


@dataclass(frozen=True)
class SchedulerDecision:
    allowed_actions: Tuple[str, ...]
    prohibited_actions: Tuple[str, ...]
    requires_founder_gate: Tuple[str, ...]

    def allows(self, action: str) -> bool:
        return action in self.allowed_actions and action not in self.prohibited_actions


@dataclass(frozen=True)
class TelemetryEvent:
    seq: int
    cycle: int
    actor: str
    state_before: str
    action: str
    reason: str
    material_delta: Dict[str, Any]
    gate: Optional[str]
    state_after: str
    previous_hash: str
    event_hash: str


class ProgressMonitor:
    def __init__(self, stagnation_threshold: int = 2) -> None:
        if stagnation_threshold < 1:
            raise ValueError("stagnation_threshold must be >= 1")
        self.stagnation_threshold = stagnation_threshold

    @staticmethod
    def _new_count(before: Sequence[str], after: Sequence[str]) -> int:
        return max(0, len(set(after)) - len(set(before)))

    def measure(self, before: Blackboard, after: Blackboard) -> MaterialDelta:
        return MaterialDelta(
            evidence=self._new_count(before.evidence_refs, after.evidence_refs),
            state=1 if before.current_phase != after.current_phase else 0,
            findings=self._new_count(before.open_findings, after.open_findings),
            blockers=self._new_count(before.blockers, after.blockers),
            decisions=self._new_count(before.decisions, after.decisions),
            verified_claims=self._new_count(before.verified_claims, after.verified_claims),
        )

    def update_stagnation(self, board: Blackboard, delta: MaterialDelta) -> None:
        board.stagnation_cycles = 0 if delta.material else board.stagnation_cycles + 1

    def threshold_reached(self, board: Blackboard) -> bool:
        return board.stagnation_cycles >= self.stagnation_threshold


class PhysiologicalScheduler:
    """Constrains mechanism only. It never grants authority."""

    PHASE_ACTIONS: Dict[str, Tuple[str, ...]] = {
        "INTAKE": ("CLASSIFY", "CONTINUE", "STOP"),
        "IMPLEMENTATION": ("CONTINUE", "METHOD_CHANGE", "HANDOFF_FOR_CONFORMANCE", "STOP"),
        "IMPLEMENTATION_COMPLETE": ("HANDOFF_FOR_CONFORMANCE", "HANDOFF_FOR_VERIFICATION", "STOP"),
        "ASSURANCE_PENDING": ("WAIT_FOR_ASSURANCE", "RETURNS_FINDING_TO", "ESCALATE_TO_FOUNDER", "STOP"),
        "FOUNDER_GATE": ("ESCALATE_TO_FOUNDER", "STOP"),
        "BLOCKED": ("METHOD_CHANGE", "HANDOFF_FOR_CONFORMANCE", "ESCALATE_TO_FOUNDER", "STOP"),
        "COMPLETE": ("STOP",),
    }

    def decide(self, board: Blackboard) -> SchedulerDecision:
        allowed = self.PHASE_ACTIONS.get(
            board.current_phase,
            ("CONTINUE", "METHOD_CHANGE", "HANDOFF_FOR_CONFORMANCE", "STOP"),
        )
        prohibited = tuple(sorted(set(board.prohibited_transitions) | FORBIDDEN_ACTIONS))
        founder = ("PRODUCTION", "CANONICAL_WRITE", "PROMOTION", "MERGE", "ADOPTION")
        return SchedulerDecision(tuple(allowed), prohibited, founder)


class TelemetryLedger:
    def __init__(self) -> None:
        self.events: List[TelemetryEvent] = []

    @staticmethod
    def _hash(payload: Dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def append(
        self,
        *,
        cycle: int,
        actor: str,
        state_before: str,
        action: str,
        reason: str,
        material_delta: Dict[str, Any],
        gate: Optional[str],
        state_after: str,
    ) -> TelemetryEvent:
        prev = self.events[-1].event_hash if self.events else "GENESIS"
        payload = {
            "seq": len(self.events) + 1,
            "cycle": cycle,
            "actor": actor,
            "state_before": state_before,
            "action": action,
            "reason": reason,
            "material_delta": material_delta,
            "gate": gate,
            "state_after": state_after,
            "previous_hash": prev,
        }
        event_hash = self._hash(payload)
        event = TelemetryEvent(event_hash=event_hash, **payload)
        self.events.append(event)
        return event

    def verify(self) -> bool:
        prev = "GENESIS"
        for event in self.events:
            payload = asdict(event)
            event_hash = payload.pop("event_hash")
            if payload["previous_hash"] != prev:
                return False
            if self._hash(payload) != event_hash:
                return False
            prev = event_hash
        return True


class FormalChecks:
    @staticmethod
    def assert_all(*, l0: Noesis, board: Blackboard, scheduler: SchedulerDecision, telemetry: TelemetryLedger) -> bool:
        l0.assert_invariants()
        if binding_hash(l0.binding) != l0.initial_binding_hash:
            raise RefactorInvariantError("L0_IDENTITY_MUTATED")
        if l0.binding["identity"]["idi"] != NOESIS_ID:
            raise RefactorInvariantError("NOESIS_ID_MUTATED")
        if l0.binding["canonical_state"]["current_ec"] != NOESIS_CURRENT_EC:
            raise RefactorInvariantError("CURRENT_EC_MUTATED")
        if any(action in scheduler.allowed_actions for action in FORBIDDEN_ACTIONS):
            raise RefactorInvariantError("SCHEDULER_GRANTED_FORBIDDEN_AUTHORITY")
        if board.stopped and board.stop_reason is None:
            raise RefactorInvariantError("STOP_WITHOUT_REASON")
        if not telemetry.verify():
            raise RefactorInvariantError("TELEMETRY_CHAIN_BROKEN")
        return True


class LayeredNoesis:
    """Additive physiological refactor around canonical Nóesis L0."""

    STAGE_ORDER = (
        RefactorStage.R1_BLACKBOARD,
        RefactorStage.R2_PROGRESS_MONITOR,
        RefactorStage.R3_TYPED_TRANSITIONS,
        RefactorStage.R4_SCHEDULER,
        RefactorStage.R5_TELEMETRY,
        RefactorStage.R6_FORMAL_CHECKS,
    )

    def __init__(
        self,
        *,
        mission_id: str,
        current_object: str,
        max_stage: RefactorStage = RefactorStage.R6_FORMAL_CHECKS,
        stagnation_threshold: int = 2,
        l0: Optional[Noesis] = None,
    ) -> None:
        self.l0 = l0 or Noesis(version="0.2.1-ec007-remediated+layered-candidate")
        self.l0_identity_hash = self.l0.initial_binding_hash
        self.max_stage = max_stage
        self.blackboard = Blackboard(mission_id=mission_id, current_object=current_object)
        self.progress = ProgressMonitor(stagnation_threshold)
        self.scheduler = PhysiologicalScheduler()
        self.telemetry = TelemetryLedger()
        self.transitions: List[TypedTransition] = []
        self._assert_l0_preserved()

    def _stage_enabled(self, stage: RefactorStage) -> bool:
        return self.STAGE_ORDER.index(stage) <= self.STAGE_ORDER.index(self.max_stage)

    @property
    def active_layers(self) -> Tuple[str, ...]:
        return tuple(stage.value for stage in self.STAGE_ORDER if self._stage_enabled(stage))

    def _assert_l0_preserved(self) -> None:
        self.l0.assert_invariants()
        if self.l0.initial_binding_hash != self.l0_identity_hash:
            raise RefactorInvariantError("L0_BINDING_CHANGED")
        if binding_hash(self.l0.binding) != self.l0_identity_hash:
            raise RefactorInvariantError("L0_RUNTIME_BINDING_CHANGED")

    def bind(
        self,
        *,
        current_phase: Optional[str] = None,
        authorized_next_actors: Optional[Iterable[str]] = None,
        pending_gates: Optional[Iterable[str]] = None,
    ) -> None:
        if current_phase:
            self.blackboard.current_phase = current_phase
        if authorized_next_actors is not None:
            self.blackboard.authorized_next_actors = sorted(set(authorized_next_actors))
        if pending_gates is not None:
            self.blackboard.pending_gates = sorted(set(pending_gates))
        self.blackboard.last_action = "BIND"
        self._assert_l0_preserved()

    def read_state(self) -> Dict[str, Any]:
        return self.blackboard.snapshot()

    def classify(self, matter: Dict[str, Any]) -> str:
        if self.blackboard.stopped:
            return "STOPPED"
        if matter.get("blocker"):
            return "BLOCKED"
        if matter.get("implementation_complete"):
            return "IMPLEMENTATION_COMPLETE"
        if matter.get("assurance_pending"):
            return "ASSURANCE_PENDING"
        return str(matter.get("phase") or self.blackboard.current_phase)

    def schedule(self) -> SchedulerDecision:
        if not self._stage_enabled(RefactorStage.R4_SCHEDULER):
            return SchedulerDecision(
                ("CONTINUE", "STOP"),
                tuple(sorted(FORBIDDEN_ACTIONS)),
                ("PRODUCTION", "PROMOTION", "MERGE"),
            )
        return self.scheduler.decide(self.blackboard)

    def _record_transition(self, relation: RelationType, target: str, reason: str) -> TypedTransition:
        transition = TypedTransition(
            source="NOESIS",
            relation=relation,
            target=target,
            object_id=self.blackboard.current_object,
            reason=reason,
            authority_transferred=False,
        )
        if self._stage_enabled(RefactorStage.R3_TYPED_TRANSITIONS):
            self.transitions.append(transition)
        return transition

    def _ingest_result_delta(self, matter: Dict[str, Any], result: Dict[str, Any]) -> None:
        for key, target in (
            ("evidence_refs", self.blackboard.evidence_refs),
            ("verified_claims", self.blackboard.verified_claims),
            ("open_findings", self.blackboard.open_findings),
            ("blockers", self.blackboard.blockers),
            ("decisions", self.blackboard.decisions),
        ):
            values = matter.get(key, [])
            if isinstance(values, str):
                values = [values]
            for value in values or []:
                if value not in target:
                    target.append(str(value))
        for value in result.get("evidence_refs", []) or []:
            if value not in self.blackboard.evidence_refs:
                self.blackboard.evidence_refs.append(str(value))
        if result.get("status") == "READY" and matter.get("claim_id"):
            claim = str(matter["claim_id"])
            if claim not in self.blackboard.verified_claims:
                self.blackboard.verified_claims.append(claim)

    def _choose_stagnation_action(self, decision: SchedulerDecision) -> Tuple[CycleDisposition, RelationType, str, str]:
        if decision.allows("METHOD_CHANGE"):
            return CycleDisposition.METHOD_CHANGE, RelationType.METHOD_CHANGE, "NOESIS", "STAGNATION_THRESHOLD"
        if decision.allows("HANDOFF_FOR_CONFORMANCE"):
            return CycleDisposition.HANDOFF, RelationType.HANDOFF_FOR_CONFORMANCE, "DEDALA", "STAGNATION_THRESHOLD"
        if decision.allows("ESCALATE_TO_FOUNDER"):
            return CycleDisposition.ESCALATE, RelationType.ESCALATE_TO_FOUNDER, "FOUNDER", "STAGNATION_THRESHOLD"
        return CycleDisposition.STOP, RelationType.STOP, "NOESIS", "STAGNATION_THRESHOLD"

    def cycle(self, tx_id: str, matter: Dict[str, Any], **process_kwargs: Any) -> Dict[str, Any]:
        self._assert_l0_preserved()
        if self.blackboard.stopped:
            return {
                "status": "STOPPED",
                "stop_reason": self.blackboard.stop_reason,
                "blackboard": self.read_state(),
                "active_layers": self.active_layers,
            }

        before = Blackboard(**self.blackboard.snapshot())
        self.blackboard.cycle += 1
        self.blackboard.current_phase = self.classify(matter)
        scheduler_decision = self.schedule()

        if any(action in FORBIDDEN_ACTIONS for action in matter.get("requested_actions", []) or []):
            self.blackboard.last_action = "BLOCKED_FORBIDDEN_TRANSITION"
            disposition = CycleDisposition.BLOCKED
            transition = self._record_transition(RelationType.STOP, "NOESIS", "FORBIDDEN_TRANSITION_REQUESTED")
            cognitive_result: Dict[str, Any] = {"status": "BLOCKED", "reason": "FORBIDDEN_TRANSITION_REQUESTED"}
        else:
            cognitive_result = self.l0.process(tx_id, matter, **process_kwargs)
            self._ingest_result_delta(matter, cognitive_result)
            disposition = CycleDisposition.CONTINUE
            transition = self._record_transition(RelationType.CONTINUE, "NOESIS", "MATERIAL_COGNITIVE_CYCLE")
            self.blackboard.last_action = "COGNITIVE_STEP"

        after_pre_delta = Blackboard(**self.blackboard.snapshot())
        if self._stage_enabled(RefactorStage.R2_PROGRESS_MONITOR):
            delta = self.progress.measure(before, after_pre_delta)
            self.progress.update_stagnation(self.blackboard, delta)
        else:
            delta = MaterialDelta(state=1 if before.current_phase != self.blackboard.current_phase else 0)

        self.blackboard.last_material_delta = delta.to_dict()

        if self._stage_enabled(RefactorStage.R2_PROGRESS_MONITOR) and self.progress.threshold_reached(self.blackboard):
            disposition, relation, target, reason = self._choose_stagnation_action(scheduler_decision)
            transition = self._record_transition(relation, target, reason)
            self.blackboard.last_action = disposition.value
            if disposition is CycleDisposition.STOP:
                self.blackboard.stopped = True
                self.blackboard.stop_reason = reason
        elif cognitive_result.get("status") in {"BLOCKED", "SOURCE_REQUIRED"} and scheduler_decision.allows("HANDOFF_FOR_CONFORMANCE"):
            disposition = CycleDisposition.HANDOFF
            transition = self._record_transition(
                RelationType.HANDOFF_FOR_CONFORMANCE,
                "DEDALA",
                cognitive_result.get("status", "BLOCKED"),
            )
            self.blackboard.last_action = "HANDOFF_FOR_CONFORMANCE"

        gate = self.blackboard.pending_gates[0] if self.blackboard.pending_gates else None
        if self._stage_enabled(RefactorStage.R5_TELEMETRY):
            self.telemetry.append(
                cycle=self.blackboard.cycle,
                actor="NOESIS",
                state_before=before.current_phase,
                action=self.blackboard.last_action,
                reason=transition.reason,
                material_delta=delta.to_dict(),
                gate=gate,
                state_after=self.blackboard.current_phase,
            )

        if self._stage_enabled(RefactorStage.R6_FORMAL_CHECKS):
            FormalChecks.assert_all(
                l0=self.l0,
                board=self.blackboard,
                scheduler=scheduler_decision,
                telemetry=self.telemetry,
            )
        else:
            self._assert_l0_preserved()

        return {
            "status": cognitive_result.get("status", disposition.value),
            "disposition": disposition.value,
            "cognitive_result": cognitive_result,
            "blackboard": self.read_state(),
            "scheduler": {
                "allowed_actions": list(scheduler_decision.allowed_actions),
                "prohibited_actions": list(scheduler_decision.prohibited_actions),
                "requires_founder_gate": list(scheduler_decision.requires_founder_gate),
            },
            "transition": asdict(transition),
            "material_delta": delta.to_dict(),
            "active_layers": self.active_layers,
            "l0_binding_hash": self.l0_identity_hash,
            "l0_current_ec": NOESIS_CURRENT_EC,
            "l0_runtime_id": RUNTIME_ID,
            "telemetry_events": [asdict(e) for e in self.telemetry.events]
            if self._stage_enabled(RefactorStage.R5_TELEMETRY)
            else [],
        }

    def stop(self, reason: str = "BOUND_COMPLETE") -> None:
        if not self.blackboard.stopped:
            self.blackboard.stopped = True
            self.blackboard.stop_reason = reason
            self.blackboard.last_action = "STOP"
        self._assert_l0_preserved()
