from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable

from sqlalchemy import Boolean, Column, Integer, MetaData, String, Table, Text, UniqueConstraint, and_, insert, select, update
from sqlalchemy.engine import Engine

metadata = MetaData()

missions = Table(
    "trial2_missions", metadata,
    Column("mission_id", String(128), primary_key=True),
    Column("canonical_state_ref", String(256), nullable=False),
    Column("current_gate", String(128), nullable=False),
    Column("status", String(64), nullable=False),
    Column("active_ocs_id", String(64)),
    Column("active_instance_id", String(128)),
    Column("current_handoff_ref", String(128)),
    Column("autonomy_budget", Integer, nullable=False),
    Column("autonomous_step_counter", Integer, nullable=False),
    Column("autonomous_handoff_counter", Integer, nullable=False),
    Column("repair_cycle_counter", Integer, nullable=False),
    Column("version", Integer, nullable=False),
)

bindings = Table(
    "trial2_bindings", metadata,
    Column("binding_id", String(128), primary_key=True),
    Column("mission_id", String(128), nullable=False),
    Column("ocs_id", String(64), nullable=False),
    Column("instance_id", String(128), nullable=False),
    Column("generation", Integer, nullable=False),
    Column("fencing_epoch", Integer, nullable=False),
    Column("authority_ref", String(256), nullable=False),
    Column("role", String(128), nullable=False),
    Column("status", String(64), nullable=False),
    Column("checkpoint_ref", String(128)),
    Column("created_at", String(64), nullable=False),
    UniqueConstraint("mission_id", "instance_id", name="uq_trial2_binding_instance"),
)

fencing = Table(
    "trial2_fencing", metadata,
    Column("mission_id", String(128), primary_key=True),
    Column("ocs_id", String(64), primary_key=True),
    Column("epoch", Integer, nullable=False),
)

checkpoints = Table(
    "trial2_checkpoints", metadata,
    Column("checkpoint_id", String(128), primary_key=True),
    Column("mission_id", String(128), nullable=False),
    Column("instance_id", String(128), nullable=False),
    Column("ocs_id", String(64), nullable=False),
    Column("sequence", Integer, nullable=False),
    Column("canonical_state_ref", String(256), nullable=False),
    Column("local_state_json", Text, nullable=False),
    Column("local_state_hash", String(64), nullable=False),
    Column("created_at", String(64), nullable=False),
    UniqueConstraint("mission_id", "sequence", name="uq_trial2_checkpoint_sequence"),
)

handoffs = Table(
    "trial2_handoffs", metadata,
    Column("handoff_id", String(128), primary_key=True),
    Column("mission_id", String(128), nullable=False),
    Column("route_id", String(180), nullable=False),
    Column("source_ocs_id", String(64), nullable=False),
    Column("source_instance_id", String(128), nullable=False),
    Column("target_ocs_id", String(64), nullable=False),
    Column("target_instance_id", String(128), nullable=False),
    Column("checkpoint_ref", String(128), nullable=False),
    Column("envelope_json", Text, nullable=False),
    Column("envelope_hash", String(64), nullable=False),
    Column("accepted", Boolean, nullable=False),
    Column("acceptance_receipt_ref", String(128)),
    Column("created_at", String(64), nullable=False),
)

receipts = Table(
    "trial2_receipts", metadata,
    Column("receipt_id", String(128), primary_key=True),
    Column("mission_id", String(128), nullable=False),
    Column("kind", String(64), nullable=False),
    Column("payload_json", Text, nullable=False),
    Column("payload_hash", String(64), nullable=False),
    Column("created_at", String(64), nullable=False),
)

observability = Table(
    "trial2_observability_events", metadata,
    Column("event_id", String(128), primary_key=True),
    Column("mission_id", String(128), nullable=False),
    Column("from_identity", String(64)),
    Column("from_instance", String(128)),
    Column("to_identity", String(64)),
    Column("to_instance", String(128)),
    Column("role", String(128)),
    Column("gate", String(128), nullable=False),
    Column("authority_ref", String(256)),
    Column("fencing_epoch", Integer),
    Column("state_before_hash", String(64), nullable=False),
    Column("state_after_hash", String(64), nullable=False),
    Column("handoff_ref", String(128)),
    Column("receipt_ref", String(128)),
    Column("checkpoint_ref", String(128)),
    Column("outcome", String(64), nullable=False),
    Column("created_at", String(64), nullable=False),
)

effects = Table(
    "trial2_effects", metadata,
    Column("effect_id", String(128), primary_key=True),
    Column("mission_id", String(128), nullable=False),
    Column("instance_id", String(128), nullable=False),
    Column("ocs_id", String(64), nullable=False),
    Column("fencing_epoch", Integer, nullable=False),
    Column("authority_ref", String(256), nullable=False),
    Column("idempotency_key", String(128), nullable=False),
    Column("payload_hash", String(64), nullable=False),
    Column("receipt_ref", String(128), nullable=False),
    Column("created_at", String(64), nullable=False),
    UniqueConstraint("mission_id", "idempotency_key", name="uq_trial2_effect_idempotency"),
)

state_entries = Table(
    "trial2_state_entries", metadata,
    Column("mission_id", String(128), primary_key=True),
    Column("namespace_key", String(320), primary_key=True),
    Column("value_hash", String(64), nullable=False),
    Column("last_instance_id", String(128), nullable=False),
    Column("last_epoch", Integer, nullable=False),
)

ROUTES = {
    "L2-SINGLE-SURFACE-DEDALA-TO-SOFIA-PLAN-001": ("DÉDALA", "SOFIA"),
    "L2-SINGLE-SURFACE-SOFIA-TO-SYNESIS-ASSURANCE-001": ("SOFIA", "SÝNESIS"),
    "L2-SINGLE-SURFACE-IMPLEMENTER-TO-SYNESIS-IMPLEMENTATION-ASSURANCE-001": (None, "SÝNESIS"),
}

class Trial2Hold(RuntimeError):
    pass

@dataclass(frozen=True, slots=True)
class RecoverySnapshot:
    mission_id: str
    current_primary_actor: str
    current_instance: str
    current_gate: str
    current_handoff_ref: str | None
    last_valid_checkpoint: str
    authority_ref: str
    role: str
    fencing_epoch: int
    autonomous_step_counter: int
    autonomous_handoff_counter: int
    repair_cycle_counter: int

@dataclass(frozen=True, slots=True)
class EffectResult:
    effect_id: str
    receipt_ref: str
    mutation_count: int
    duplicate_reconciled: bool

def _now() -> str:
    return datetime.now(UTC).isoformat()

def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()

def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _state_ns(mission_id: str, ocs_id: str) -> str:
    return f"trial2:{mission_id}:{ocs_id}:state:"

class Trial2PersistentStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create_schema(self) -> None:
        metadata.create_all(self._engine)

    def create_mission(self, mission_id: str, *, canonical_state_ref: str, current_gate: str, autonomy_budget: int) -> None:
        if autonomy_budget < 1:
            raise Trial2Hold("autonomy_budget_required")
        with self._engine.begin() as conn:
            conn.execute(insert(missions).values(
                mission_id=mission_id, canonical_state_ref=canonical_state_ref,
                current_gate=current_gate, status="TRIAL_2_BUILD",
                autonomy_budget=autonomy_budget, autonomous_step_counter=0,
                autonomous_handoff_counter=0, repair_cycle_counter=0, version=1,
            ))
            self._observe(conn, mission_id, {}, self._mission(conn, mission_id), outcome="mission_created")

    def bind(self, mission_id: str, ocs_id: str, instance_id: str, *, authority_ref: str, role: str, activate_if_empty: bool = False) -> dict[str, Any]:
        if not all((mission_id, ocs_id, instance_id, authority_ref, role)):
            raise Trial2Hold("binding_identity_authority_or_role_ambiguous")
        with self._engine.begin() as conn:
            mission = self._mission(conn, mission_id)
            before = dict(mission)
            prior_epoch = conn.execute(select(fencing.c.epoch).where(and_(fencing.c.mission_id == mission_id, fencing.c.ocs_id == ocs_id))).scalar_one_or_none()
            epoch = 1 if prior_epoch is None else int(prior_epoch) + 1
            if prior_epoch is None:
                conn.execute(insert(fencing).values(mission_id=mission_id, ocs_id=ocs_id, epoch=epoch))
                generation = 1
            else:
                conn.execute(update(fencing).where(and_(fencing.c.mission_id == mission_id, fencing.c.ocs_id == ocs_id)).values(epoch=epoch))
                generation = int(conn.execute(select(bindings.c.generation).where(and_(bindings.c.mission_id == mission_id, bindings.c.ocs_id == ocs_id)).order_by(bindings.c.generation.desc()).limit(1)).scalar_one()) + 1
            active = activate_if_empty and mission["active_instance_id"] is None
            status = "ACTIVE" if active else "BOUND"
            binding_id = "binding:" + _hash({"mission": mission_id, "ocs": ocs_id, "instance": instance_id, "epoch": epoch})
            conn.execute(insert(bindings).values(binding_id=binding_id, mission_id=mission_id, ocs_id=ocs_id, instance_id=instance_id, generation=generation, fencing_epoch=epoch, authority_ref=authority_ref, role=role, status=status, created_at=_now()))
            if active:
                conn.execute(update(missions).where(missions.c.mission_id == mission_id).values(active_ocs_id=ocs_id, active_instance_id=instance_id, version=int(mission["version"]) + 1))
            receipt = self._receipt(conn, mission_id, "binding", {"binding_id": binding_id, "instance_id": instance_id, "ocs_id": ocs_id, "epoch": epoch})
            self._observe(conn, mission_id, before, self._mission(conn, mission_id), from_identity=mission.get("active_ocs_id"), from_instance=mission.get("active_instance_id"), to_identity=ocs_id if active else mission.get("active_ocs_id"), to_instance=instance_id if active else mission.get("active_instance_id"), role=role, authority_ref=authority_ref, fencing_epoch=epoch, receipt_ref=receipt, outcome="binding_persisted")
            return {"binding_id": binding_id, "epoch": epoch, "generation": generation, "receipt_ref": receipt}

    def checkpoint(self, mission_id: str, *, instance_id: str, local_state: dict[str, Any]) -> str:
        with self._engine.begin() as conn:
            mission = self._mission(conn, mission_id)
            if mission["active_instance_id"] != instance_id:
                raise Trial2Hold("checkpoint_requires_active_instance")
            binding = self._binding(conn, mission_id, instance_id)
            if binding["status"] != "ACTIVE":
                raise Trial2Hold("checkpoint_requires_active_binding")
            seq = int(conn.execute(select(checkpoints.c.sequence).where(checkpoints.c.mission_id == mission_id).order_by(checkpoints.c.sequence.desc()).limit(1)).scalar_one_or_none() or 0) + 1
            checkpoint_id = "checkpoint:" + _hash({"mission": mission_id, "instance": instance_id, "sequence": seq, "state": local_state})
            conn.execute(insert(checkpoints).values(checkpoint_id=checkpoint_id, mission_id=mission_id, instance_id=instance_id, ocs_id=binding["ocs_id"], sequence=seq, canonical_state_ref=mission["canonical_state_ref"], local_state_json=_json(local_state), local_state_hash=_hash(local_state), created_at=_now()))
            conn.execute(update(bindings).where(bindings.c.binding_id == binding["binding_id"]).values(checkpoint_ref=checkpoint_id))
            receipt = self._receipt(conn, mission_id, "checkpoint", {"checkpoint_id": checkpoint_id, "instance_id": instance_id})
            self._observe(conn, mission_id, mission, self._mission(conn, mission_id), from_identity=binding["ocs_id"], from_instance=instance_id, to_identity=binding["ocs_id"], to_instance=instance_id, role=binding["role"], authority_ref=binding["authority_ref"], fencing_epoch=int(binding["fencing_epoch"]), receipt_ref=receipt, checkpoint_ref=checkpoint_id, outcome="checkpoint_persisted")
            return checkpoint_id

    def issue_handoff(self, mission_id: str, *, route_id: str, target_instance_id: str, target_ocs_id: str, envelope: dict[str, Any]) -> str:
        route = ROUTES.get(route_id)
        if route is None:
            raise Trial2Hold("unlisted_l2_route")
        with self._engine.begin() as conn:
            mission = self._mission(conn, mission_id)
            source_ocs = mission.get("active_ocs_id")
            source_instance = mission.get("active_instance_id")
            if not source_ocs or not source_instance:
                raise Trial2Hold("active_source_missing")
            if route[0] is not None and route[0] != source_ocs:
                raise Trial2Hold("route_source_mismatch")
            if route[1] != target_ocs_id:
                raise Trial2Hold("route_target_mismatch")
            source = self._binding(conn, mission_id, str(source_instance))
            target = self._binding(conn, mission_id, target_instance_id)
            if not source.get("checkpoint_ref"):
                raise Trial2Hold("source_checkpoint_required")
            if target["ocs_id"] != target_ocs_id or target["status"] != "BOUND":
                raise Trial2Hold("target_binding_required")
            handoff_id = "handoff:" + _hash({"mission": mission_id, "route": route_id, "source": source_instance, "target": target_instance_id, "checkpoint": source["checkpoint_ref"], "envelope": envelope})
            conn.execute(insert(handoffs).values(handoff_id=handoff_id, mission_id=mission_id, route_id=route_id, source_ocs_id=source_ocs, source_instance_id=source_instance, target_ocs_id=target_ocs_id, target_instance_id=target_instance_id, checkpoint_ref=source["checkpoint_ref"], envelope_json=_json(envelope), envelope_hash=_hash(envelope), accepted=False, created_at=_now()))
            conn.execute(update(missions).where(missions.c.mission_id == mission_id).values(current_handoff_ref=handoff_id))
            receipt = self._receipt(conn, mission_id, "handoff_envelope", {"handoff_id": handoff_id})
            self._observe(conn, mission_id, mission, self._mission(conn, mission_id), from_identity=source_ocs, from_instance=str(source_instance), to_identity=target_ocs_id, to_instance=target_instance_id, role=source["role"], authority_ref=source["authority_ref"], fencing_epoch=int(source["fencing_epoch"]), handoff_ref=handoff_id, receipt_ref=receipt, checkpoint_ref=source["checkpoint_ref"], outcome="handoff_persisted")
            return handoff_id

    def accept_handoff(self, mission_id: str, handoff_id: str) -> str:
        with self._engine.begin() as conn:
            mission = self._mission(conn, mission_id)
            row = dict(conn.execute(select(handoffs).where(and_(handoffs.c.mission_id == mission_id, handoffs.c.handoff_id == handoff_id))).mappings().one())
            if row["accepted"]:
                raise Trial2Hold("blind_retry_forbidden")
            if mission["active_instance_id"] != row["source_instance_id"]:
                raise Trial2Hold("source_no_longer_active")
            source = self._binding(conn, mission_id, row["source_instance_id"])
            target = self._binding(conn, mission_id, row["target_instance_id"])
            if not source.get("checkpoint_ref") or source["checkpoint_ref"] != row["checkpoint_ref"]:
                raise Trial2Hold("checkpoint_integrity_or_continuity_failure")
            if target["status"] != "BOUND":
                raise Trial2Hold("target_binding_required")
            if int(mission["autonomous_step_counter"]) + 1 > int(mission["autonomy_budget"]):
                raise Trial2Hold("autonomy_budget_exhausted")
            conn.execute(update(bindings).where(bindings.c.binding_id == source["binding_id"]).values(status="QUIESCENT"))
            conn.execute(update(bindings).where(bindings.c.binding_id == target["binding_id"]).values(status="ACTIVE"))
            receipt = self._receipt(conn, mission_id, "handoff_acceptance", {"handoff_id": handoff_id, "target_instance_id": row["target_instance_id"]})
            conn.execute(update(handoffs).where(handoffs.c.handoff_id == handoff_id).values(accepted=True, acceptance_receipt_ref=receipt))
            conn.execute(update(missions).where(missions.c.mission_id == mission_id).values(active_ocs_id=row["target_ocs_id"], active_instance_id=row["target_instance_id"], current_handoff_ref=handoff_id, autonomous_step_counter=int(mission["autonomous_step_counter"]) + 1, autonomous_handoff_counter=int(mission["autonomous_handoff_counter"]) + 1, version=int(mission["version"]) + 1))
            self._observe(conn, mission_id, mission, self._mission(conn, mission_id), from_identity=row["source_ocs_id"], from_instance=row["source_instance_id"], to_identity=row["target_ocs_id"], to_instance=row["target_instance_id"], role=target["role"], authority_ref=target["authority_ref"], fencing_epoch=int(target["fencing_epoch"]), handoff_ref=handoff_id, receipt_ref=receipt, checkpoint_ref=row["checkpoint_ref"], outcome="handoff_accepted")
            return receipt

    def recover_snapshot(self, mission_id: str, *, authority_validator: Callable[[str, str, str], bool]) -> RecoverySnapshot:
        with self._engine.begin() as conn:
            mission = self._mission(conn, mission_id)
            actor = mission.get("active_ocs_id")
            instance = mission.get("active_instance_id")
            if not actor or not instance:
                raise Trial2Hold("unknown_recovery_state")
            binding = self._binding(conn, mission_id, str(instance))
            if binding["status"] != "ACTIVE":
                raise Trial2Hold("unknown_recovery_state")
            checkpoint_ref = binding.get("checkpoint_ref")
            if not checkpoint_ref:
                raise Trial2Hold("no_checkpoint_for_required_recovery")
            cp = dict(conn.execute(select(checkpoints).where(checkpoints.c.checkpoint_id == checkpoint_ref)).mappings().one())
            try:
                local_state = json.loads(cp["local_state_json"])
            except Exception as exc:
                raise Trial2Hold("checkpoint_integrity_failure") from exc
            if _hash(local_state) != cp["local_state_hash"]:
                raise Trial2Hold("checkpoint_integrity_failure")
            epoch = conn.execute(select(fencing.c.epoch).where(and_(fencing.c.mission_id == mission_id, fencing.c.ocs_id == actor))).scalar_one_or_none()
            if epoch is None or int(epoch) != int(binding["fencing_epoch"]):
                raise Trial2Hold("fencing_revalidation_failure")
            if not authority_validator(binding["authority_ref"], str(actor), binding["role"]):
                raise Trial2Hold("authority_revalidation_failure")
            current_handoff = mission.get("current_handoff_ref")
            if current_handoff:
                h = dict(conn.execute(select(handoffs).where(handoffs.c.handoff_id == current_handoff)).mappings().one())
                if h["accepted"]:
                    if not h["acceptance_receipt_ref"]:
                        raise Trial2Hold("handoff_receipt_recovery_failure")
                    if conn.execute(select(receipts.c.receipt_id).where(receipts.c.receipt_id == h["acceptance_receipt_ref"])).scalar_one_or_none() is None:
                        raise Trial2Hold("handoff_receipt_recovery_failure")
            snapshot = RecoverySnapshot(mission_id, str(actor), str(instance), mission["current_gate"], current_handoff, str(checkpoint_ref), binding["authority_ref"], binding["role"], int(binding["fencing_epoch"]), int(mission["autonomous_step_counter"]), int(mission["autonomous_handoff_counter"]), int(mission["repair_cycle_counter"]))
            self._observe(conn, mission_id, mission, mission, from_identity=str(actor), from_instance=str(instance), to_identity=str(actor), to_instance=str(instance), role=binding["role"], authority_ref=binding["authority_ref"], fencing_epoch=int(binding["fencing_epoch"]), handoff_ref=current_handoff, checkpoint_ref=str(checkpoint_ref), outcome="restart_recovery_revalidated")
            return snapshot

    def apply_synthetic_effect(self, mission_id: str, *, ocs_id: str, instance_id: str, epoch: int, authority_ref: str, idempotency_key: str, payload: dict[str, Any]) -> EffectResult:
        with self._engine.begin() as conn:
            mission = self._mission(conn, mission_id)
            if mission["active_ocs_id"] != ocs_id or mission["active_instance_id"] != instance_id:
                raise Trial2Hold("unauthorized_effect")
            binding = self._binding(conn, mission_id, instance_id)
            if int(binding["fencing_epoch"]) != epoch:
                raise Trial2Hold("stale_epoch")
            if binding["authority_ref"] != authority_ref:
                raise Trial2Hold("authority_mismatch")
            prior = conn.execute(select(effects).where(and_(effects.c.mission_id == mission_id, effects.c.idempotency_key == idempotency_key))).mappings().one_or_none()
            if prior is not None:
                return EffectResult(prior["effect_id"], prior["receipt_ref"], 0, True)
            receipt = self._receipt(conn, mission_id, "effect", {"idempotency_key": idempotency_key, "payload_hash": _hash(payload)})
            effect_id = "effect:" + _hash({"mission": mission_id, "key": idempotency_key, "payload": payload})
            conn.execute(insert(effects).values(effect_id=effect_id, mission_id=mission_id, instance_id=instance_id, ocs_id=ocs_id, fencing_epoch=epoch, authority_ref=authority_ref, idempotency_key=idempotency_key, payload_hash=_hash(payload), receipt_ref=receipt, created_at=_now()))
            return EffectResult(effect_id, receipt, 1, False)

    def write_state(self, mission_id: str, *, ocs_id: str, instance_id: str, epoch: int, namespace_key: str, value: Any) -> int:
        with self._engine.begin() as conn:
            mission = self._mission(conn, mission_id)
            if mission["active_ocs_id"] != ocs_id or mission["active_instance_id"] != instance_id:
                return 0
            if not namespace_key.startswith(_state_ns(mission_id, ocs_id)):
                return 0
            binding = self._binding(conn, mission_id, instance_id)
            if int(binding["fencing_epoch"]) != epoch:
                return 0
            current = conn.execute(select(state_entries).where(and_(state_entries.c.mission_id == mission_id, state_entries.c.namespace_key == namespace_key))).mappings().one_or_none()
            values = {"value_hash": _hash(value), "last_instance_id": instance_id, "last_epoch": epoch}
            if current is None:
                conn.execute(insert(state_entries).values(mission_id=mission_id, namespace_key=namespace_key, **values))
            else:
                conn.execute(update(state_entries).where(and_(state_entries.c.mission_id == mission_id, state_entries.c.namespace_key == namespace_key)).values(**values))
            return 1

    def observability_count(self, mission_id: str) -> int:
        with self._engine.connect() as conn:
            return len(conn.execute(select(observability.c.event_id).where(observability.c.mission_id == mission_id)).all())

    def effect_count(self, mission_id: str) -> int:
        with self._engine.connect() as conn:
            return len(conn.execute(select(effects.c.effect_id).where(effects.c.mission_id == mission_id)).all())

    def _mission(self, conn: Any, mission_id: str) -> dict[str, Any]:
        row = conn.execute(select(missions).where(missions.c.mission_id == mission_id)).mappings().one_or_none()
        if row is None:
            raise Trial2Hold("unknown_recovery_state")
        return dict(row)

    def _binding(self, conn: Any, mission_id: str, instance_id: str) -> dict[str, Any]:
        row = conn.execute(select(bindings).where(and_(bindings.c.mission_id == mission_id, bindings.c.instance_id == instance_id))).mappings().one_or_none()
        if row is None:
            raise Trial2Hold("binding_missing")
        return dict(row)

    def _receipt(self, conn: Any, mission_id: str, kind: str, payload: dict[str, Any]) -> str:
        at = _now()
        receipt_id = "receipt:" + _hash({"mission": mission_id, "kind": kind, "payload": payload, "at": at})
        conn.execute(insert(receipts).values(receipt_id=receipt_id, mission_id=mission_id, kind=kind, payload_json=_json(payload), payload_hash=_hash(payload), created_at=at))
        return receipt_id

    def _observe(self, conn: Any, mission_id: str, before: dict[str, Any], after: dict[str, Any], *, from_identity: str | None = None, from_instance: str | None = None, to_identity: str | None = None, to_instance: str | None = None, role: str | None = None, authority_ref: str | None = None, fencing_epoch: int | None = None, handoff_ref: str | None = None, receipt_ref: str | None = None, checkpoint_ref: str | None = None, outcome: str) -> str:
        at = _now()
        event_id = "obs:" + _hash({"mission": mission_id, "outcome": outcome, "at": at, "before": before, "after": after})
        conn.execute(insert(observability).values(event_id=event_id, mission_id=mission_id, from_identity=from_identity, from_instance=from_instance, to_identity=to_identity, to_instance=to_instance, role=role, gate=str(after.get("current_gate") or before.get("current_gate") or "UNKNOWN"), authority_ref=authority_ref, fencing_epoch=fencing_epoch, state_before_hash=_hash(before), state_after_hash=_hash(after), handoff_ref=handoff_ref, receipt_ref=receipt_ref, checkpoint_ref=checkpoint_ref, outcome=outcome, created_at=at))
        return event_id
