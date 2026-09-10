from dataclasses import dataclass
from typing import Dict, Tuple
from uuid import uuid4
import threading


@dataclass(frozen=True)
class SynapticSignal:
    signal_id: str
    sender_actor_id: str
    sender_ocs_id: str
    recipient_actor_id: str
    recipient_ocs_id: str
    kind: str
    payload_ref: str
    trace_id: str
    authority_ref: str
    mission_binding: str
    fencing_epoch: int


@dataclass(frozen=True)
class RepairMission:
    repair_id: str
    actor_id: str
    ocs_id: str
    anomaly_code: str
    action: str
    authority_ref: str
    mission_binding: str
    trace_id: str
    generation: int
    fencing_epoch: int
    status: str = "PROPOSED"


class SynapticMesh:
    ALLOWED_KINDS = frozenset({"STATE", "EVIDENCE", "REQUEST", "ESCALATION", "REPAIR_PROPOSAL"})

    def __init__(self, states, trace, ocs_enforcer):
        self.states = states
        self.trace = trace
        self.ocs_enforcer = ocs_enforcer
        self._signals: Dict[str, SynapticSignal] = {}
        self._fingerprints: Dict[str, tuple] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _fingerprint(signal: SynapticSignal):
        return (
            signal.sender_actor_id,
            signal.sender_ocs_id,
            signal.recipient_actor_id,
            signal.recipient_ocs_id,
            signal.kind,
            signal.payload_ref,
            signal.trace_id,
            signal.authority_ref,
            signal.mission_binding,
            signal.fencing_epoch,
        )

    def route(self, signal: SynapticSignal):
        fp = self._fingerprint(signal)
        with self._lock:
            if signal.signal_id in self._signals:
                if self._fingerprints[signal.signal_id] != fp:
                    raise RuntimeError("SIGNAL_ID_CONFLICT")
                return self._signals[signal.signal_id]
            if signal.kind not in self.ALLOWED_KINDS:
                raise RuntimeError("MESH_KIND_FORBIDDEN")
            sender = self.states.get(signal.sender_actor_id)
            recipient = self.states.get(signal.recipient_actor_id)
            self.states.validate_current(sender.actor_id, sender.generation, sender.fencing_epoch)
            self.states.validate_current(recipient.actor_id, recipient.generation, recipient.fencing_epoch)
            self.ocs_enforcer.binding_for_actor(sender)
            self.ocs_enforcer.binding_for_actor(recipient)
            if sender.identity_id != signal.sender_ocs_id or recipient.identity_id != signal.recipient_ocs_id:
                raise RuntimeError("MESH_IDENTITY_MISMATCH")
            if sender.authority.authority_ref != signal.authority_ref:
                raise RuntimeError("MESH_AUTHORITY_MISMATCH")
            if sender.mission_binding != signal.mission_binding or recipient.mission_binding != signal.mission_binding:
                raise RuntimeError("MESH_MISSION_MISMATCH")
            if sender.fencing_epoch != signal.fencing_epoch:
                raise RuntimeError("MESH_FENCING_MISMATCH")
            if signal.trace_id != sender.trace_id:
                raise RuntimeError("MESH_TRACE_MISMATCH")
            if recipient.trace_id != sender.trace_id:
                raise RuntimeError("MESH_CROSS_TRACE_FORBIDDEN_V1")
            self._signals[signal.signal_id] = signal
            self._fingerprints[signal.signal_id] = fp
            self.trace.emit(
                "SYNAPTIC_SIGNAL",
                sender,
                f"signal={signal.signal_id};kind={signal.kind};payload={signal.payload_ref};to={recipient.actor_id};trace={signal.trace_id}",
                parent_span_id=recipient.span_id,
                receipt_id=f"synaptic:{signal.signal_id}",
            )
            return signal

    def all(self) -> Tuple[SynapticSignal, ...]:
        with self._lock:
            return tuple(self._signals.values())


class AutopoiesisEngine:
    REPAIRABLE = frozenset({"STALE_CONTEXT", "MISSING_EVIDENCE", "BUDGET_PRESSURE", "CHILD_STALL"})

    def __init__(self, states, trace, ocs_enforcer, mesh: SynapticMesh):
        self.states = states
        self.trace = trace
        self.ocs_enforcer = ocs_enforcer
        self.mesh = mesh
        self._repairs: Dict[str, RepairMission] = {}
        self._lock = threading.RLock()

    def inspect_and_propose(self, actor_id: str, anomaly_code: str):
        actor = self.states.get(actor_id)
        self.states.validate_current(actor.actor_id, actor.generation, actor.fencing_epoch)
        self.ocs_enforcer.binding_for_actor(actor)
        if anomaly_code not in self.REPAIRABLE:
            self.trace.emit("AUTOPOIESIS_HOLD", actor, f"UNREPAIRABLE:{anomaly_code}")
            return None
        repair = RepairMission(
            repair_id=f"repair:{uuid4()}",
            actor_id=actor.actor_id,
            ocs_id=actor.identity_id,
            anomaly_code=anomaly_code,
            action="OPEN_BOUNDED_INTERNAL_REPAIR_MISSION",
            authority_ref=actor.authority.authority_ref,
            mission_binding=actor.mission_binding,
            trace_id=actor.trace_id,
            generation=actor.generation,
            fencing_epoch=actor.fencing_epoch,
        )
        with self._lock:
            self._repairs[repair.repair_id] = repair
        self.trace.emit("AUTOPOIESIS_PROPOSE", actor, f"{anomaly_code}:{repair.repair_id}")
        return repair

    def _resolve_repair(self, repair_or_id):
        repair_id = repair_or_id if isinstance(repair_or_id, str) else repair_or_id.repair_id
        with self._lock:
            if repair_id not in self._repairs:
                raise RuntimeError("REPAIR_PROVENANCE_UNKNOWN")
            stored = self._repairs[repair_id]
        if not isinstance(repair_or_id, str) and repair_or_id != stored:
            raise RuntimeError("REPAIR_PROVENANCE_CONFLICT")
        return stored

    def emit_repair_signal(self, repair_or_id, recipient_actor_id: str):
        repair = self._resolve_repair(repair_or_id)
        sender = self.states.get(repair.actor_id)
        recipient = self.states.get(recipient_actor_id)
        self.states.validate_current(sender.actor_id, repair.generation, repair.fencing_epoch)
        if sender.identity_id != repair.ocs_id:
            raise RuntimeError("REPAIR_IDENTITY_MISMATCH")
        if sender.authority.authority_ref != repair.authority_ref:
            raise RuntimeError("REPAIR_AUTHORITY_MISMATCH")
        if sender.mission_binding != repair.mission_binding:
            raise RuntimeError("REPAIR_MISSION_MISMATCH")
        if sender.trace_id != repair.trace_id:
            raise RuntimeError("REPAIR_TRACE_MISMATCH")
        signal = SynapticSignal(
            signal_id=f"signal:{uuid4()}",
            sender_actor_id=sender.actor_id,
            sender_ocs_id=sender.identity_id,
            recipient_actor_id=recipient.actor_id,
            recipient_ocs_id=recipient.identity_id,
            kind="REPAIR_PROPOSAL",
            payload_ref=repair.repair_id,
            trace_id=sender.trace_id,
            authority_ref=sender.authority.authority_ref,
            mission_binding=sender.mission_binding,
            fencing_epoch=sender.fencing_epoch,
        )
        return self.mesh.route(signal)

    def repairs(self):
        with self._lock:
            return tuple(self._repairs.values())
