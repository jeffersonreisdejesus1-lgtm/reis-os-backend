from dataclasses import dataclass
from typing import Dict, Tuple
from uuid import uuid4
import threading

from recursive_runtime.contracts.model import JournalRecord


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
    causal_parent_signal_id: str | None = None


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


class CausalDAG:
    def __init__(self):
        self._nodes: Dict[str, tuple[str, str | None]] = {}
        self._lock = threading.RLock()

    def add(self, signal: SynapticSignal):
        with self._lock:
            existing = self._nodes.get(signal.signal_id)
            candidate = (signal.trace_id, signal.causal_parent_signal_id)
            if existing is not None:
                if existing != candidate:
                    raise RuntimeError("CAUSAL_DAG_NODE_CONFLICT")
                return
            parent = signal.causal_parent_signal_id
            if parent is not None:
                if parent not in self._nodes:
                    raise RuntimeError("CAUSAL_PARENT_UNKNOWN")
                parent_trace, _ = self._nodes[parent]
                if parent_trace != signal.trace_id:
                    raise RuntimeError("CAUSAL_CROSS_TRACE_FORBIDDEN")
                cursor = parent
                while cursor is not None:
                    if cursor == signal.signal_id:
                        raise RuntimeError("CAUSAL_CYCLE")
                    cursor = self._nodes[cursor][1]
            self._nodes[signal.signal_id] = candidate

    def contains(self, signal_id: str):
        with self._lock:
            return signal_id in self._nodes

    def parent_of(self, signal_id: str):
        with self._lock:
            return self._nodes[signal_id][1]


class SynapticMesh:
    ALLOWED_KINDS = frozenset({"STATE", "EVIDENCE", "REQUEST", "ESCALATION", "REPAIR_PROPOSAL"})

    def __init__(self, states, trace, ocs_enforcer, journal=None, causal_dag=None):
        self.states = states
        self.trace = trace
        self.ocs_enforcer = ocs_enforcer
        self.journal = journal
        self.causal_dag = causal_dag or CausalDAG()
        self._signals: Dict[str, SynapticSignal] = {}
        self._fingerprints: Dict[str, tuple] = {}
        self._lock = threading.RLock()
        self.replay()

    @staticmethod
    def _fingerprint(signal: SynapticSignal):
        return (
            signal.sender_actor_id, signal.sender_ocs_id, signal.recipient_actor_id,
            signal.recipient_ocs_id, signal.kind, signal.payload_ref, signal.trace_id,
            signal.authority_ref, signal.mission_binding, signal.fencing_epoch,
            signal.causal_parent_signal_id,
        )

    @staticmethod
    def _payload(signal: SynapticSignal):
        return tuple((k, str(v) if v is not None else "") for k, v in (
            ("sender_actor_id", signal.sender_actor_id), ("sender_ocs_id", signal.sender_ocs_id),
            ("recipient_actor_id", signal.recipient_actor_id), ("recipient_ocs_id", signal.recipient_ocs_id),
            ("kind", signal.kind), ("payload_ref", signal.payload_ref), ("authority_ref", signal.authority_ref),
            ("mission_binding", signal.mission_binding), ("causal_parent_signal_id", signal.causal_parent_signal_id),
        ))

    def _journal_signal(self, signal: SynapticSignal):
        if self.journal is None:
            return
        self.journal.put(JournalRecord(
            journal_id=f"mesh:{signal.signal_id}", kind="MESH_SIGNAL", actor_id=signal.sender_actor_id,
            trace_id=signal.trace_id, generation=0, fencing_epoch=signal.fencing_epoch,
            status="COMMITTED", payload=self._payload(signal),
        ))

    def replay(self):
        if self.journal is None:
            return ()
        restored=[]
        with self._lock:
            for row in self.journal.all():
                if row["kind"] != "MESH_SIGNAL":
                    continue
                p=dict(row["payload"])
                signal=SynapticSignal(
                    signal_id=row["journal_id"].removeprefix("mesh:"), sender_actor_id=p["sender_actor_id"],
                    sender_ocs_id=p["sender_ocs_id"], recipient_actor_id=p["recipient_actor_id"],
                    recipient_ocs_id=p["recipient_ocs_id"], kind=p["kind"], payload_ref=p["payload_ref"],
                    trace_id=row["trace_id"], authority_ref=p["authority_ref"], mission_binding=p["mission_binding"],
                    fencing_epoch=row["fencing_epoch"], causal_parent_signal_id=p.get("causal_parent_signal_id") or None,
                )
                fp=self._fingerprint(signal)
                existing=self._signals.get(signal.signal_id)
                if existing is not None and self._fingerprints[signal.signal_id] != fp:
                    raise RuntimeError("SIGNAL_ID_CONFLICT")
                self.causal_dag.add(signal)
                self._signals[signal.signal_id]=signal; self._fingerprints[signal.signal_id]=fp; restored.append(signal.signal_id)
        return tuple(dict.fromkeys(restored))

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
            self.ocs_enforcer.binding_for_actor(sender); self.ocs_enforcer.binding_for_actor(recipient)
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
            self.causal_dag.add(signal)
            self._journal_signal(signal)
            self._signals[signal.signal_id] = signal; self._fingerprints[signal.signal_id] = fp
            self.trace.emit(
                "SYNAPTIC_SIGNAL", sender,
                f"signal={signal.signal_id};kind={signal.kind};payload={signal.payload_ref};to={recipient.actor_id};trace={signal.trace_id};parent={signal.causal_parent_signal_id or 'ROOT'}",
                parent_span_id=recipient.span_id, receipt_id=f"synaptic:{signal.signal_id}",
            )
            return signal

    def all(self) -> Tuple[SynapticSignal, ...]:
        with self._lock:
            return tuple(self._signals.values())


class AutopoiesisEngine:
    REPAIRABLE = frozenset({"STALE_CONTEXT", "MISSING_EVIDENCE", "BUDGET_PRESSURE", "CHILD_STALL"})

    def __init__(self, states, trace, ocs_enforcer, mesh: SynapticMesh, journal=None):
        self.states = states; self.trace = trace; self.ocs_enforcer = ocs_enforcer; self.mesh = mesh
        self.journal = journal
        self._repairs: Dict[str, RepairMission] = {}; self._lock = threading.RLock()
        self.replay()

    @staticmethod
    def _repair_payload(repair: RepairMission):
        return tuple((k,str(v)) for k,v in (
            ("ocs_id",repair.ocs_id),("anomaly_code",repair.anomaly_code),("action",repair.action),
            ("authority_ref",repair.authority_ref),("mission_binding",repair.mission_binding),("status",repair.status),
        ))

    def _journal_repair(self, repair: RepairMission):
        if self.journal is None: return
        self.journal.put(JournalRecord(
            journal_id=f"repair:{repair.repair_id}", kind="AUTOPOIESIS_REPAIR", actor_id=repair.actor_id,
            trace_id=repair.trace_id, generation=repair.generation, fencing_epoch=repair.fencing_epoch,
            status=repair.status, payload=self._repair_payload(repair),
        ))

    def replay(self):
        if self.journal is None: return ()
        restored=[]
        with self._lock:
            for row in self.journal.all():
                if row["kind"] != "AUTOPOIESIS_REPAIR": continue
                p=dict(row["payload"])
                repair=RepairMission(
                    repair_id=row["journal_id"].removeprefix("repair:"), actor_id=row["actor_id"], ocs_id=p["ocs_id"],
                    anomaly_code=p["anomaly_code"], action=p["action"], authority_ref=p["authority_ref"],
                    mission_binding=p["mission_binding"], trace_id=row["trace_id"], generation=row["generation"],
                    fencing_epoch=row["fencing_epoch"], status=p.get("status",row["status"]),
                )
                existing=self._repairs.get(repair.repair_id)
                if existing is not None and existing != repair: raise RuntimeError("REPAIR_PROVENANCE_CONFLICT")
                self._repairs[repair.repair_id]=repair; restored.append(repair.repair_id)
        return tuple(dict.fromkeys(restored))

    def inspect_and_propose(self, actor_id: str, anomaly_code: str):
        actor = self.states.get(actor_id)
        self.states.validate_current(actor.actor_id, actor.generation, actor.fencing_epoch)
        self.ocs_enforcer.binding_for_actor(actor)
        if anomaly_code not in self.REPAIRABLE:
            self.trace.emit("AUTOPOIESIS_HOLD", actor, f"UNREPAIRABLE:{anomaly_code}")
            return None
        repair = RepairMission(
            repair_id=f"repair:{uuid4()}", actor_id=actor.actor_id, ocs_id=actor.identity_id,
            anomaly_code=anomaly_code, action="OPEN_BOUNDED_INTERNAL_REPAIR_MISSION",
            authority_ref=actor.authority.authority_ref, mission_binding=actor.mission_binding,
            trace_id=actor.trace_id, generation=actor.generation, fencing_epoch=actor.fencing_epoch,
        )
        with self._lock:
            self._journal_repair(repair); self._repairs[repair.repair_id] = repair
        self.trace.emit("AUTOPOIESIS_PROPOSE", actor, f"{anomaly_code}:{repair.repair_id}")
        return repair

    def _resolve_repair(self, repair_or_id):
        repair_id = repair_or_id if isinstance(repair_or_id, str) else repair_or_id.repair_id
        with self._lock:
            if repair_id not in self._repairs: raise RuntimeError("REPAIR_PROVENANCE_UNKNOWN")
            stored = self._repairs[repair_id]
        if not isinstance(repair_or_id, str) and repair_or_id != stored: raise RuntimeError("REPAIR_PROVENANCE_CONFLICT")
        return stored

    def emit_repair_signal(self, repair_or_id, recipient_actor_id: str, causal_parent_signal_id=None):
        repair = self._resolve_repair(repair_or_id)
        sender = self.states.get(repair.actor_id); recipient = self.states.get(recipient_actor_id)
        self.states.validate_current(sender.actor_id, repair.generation, repair.fencing_epoch)
        if sender.identity_id != repair.ocs_id: raise RuntimeError("REPAIR_IDENTITY_MISMATCH")
        if sender.authority.authority_ref != repair.authority_ref: raise RuntimeError("REPAIR_AUTHORITY_MISMATCH")
        if sender.mission_binding != repair.mission_binding: raise RuntimeError("REPAIR_MISSION_MISMATCH")
        if sender.trace_id != repair.trace_id: raise RuntimeError("REPAIR_TRACE_MISMATCH")
        signal = SynapticSignal(
            signal_id=f"signal:{uuid4()}", sender_actor_id=sender.actor_id, sender_ocs_id=sender.identity_id,
            recipient_actor_id=recipient.actor_id, recipient_ocs_id=recipient.identity_id, kind="REPAIR_PROPOSAL",
            payload_ref=repair.repair_id, trace_id=sender.trace_id, authority_ref=sender.authority.authority_ref,
            mission_binding=sender.mission_binding, fencing_epoch=sender.fencing_epoch,
            causal_parent_signal_id=causal_parent_signal_id,
        )
        return self.mesh.route(signal)

    def repairs(self):
        with self._lock:
            return tuple(self._repairs.values())
