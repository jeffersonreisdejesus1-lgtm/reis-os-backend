from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    and_,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine

from .contracts import (
    BindingStatus,
    Decision,
    L2_ROUTES,
    MissionStatus,
    TrialHold,
    canonical_hash,
    memory_namespace,
    state_namespace,
)

metadata = MetaData()

missions = Table(
    "trial_missions",
    metadata,
    Column("mission_id", String(128), primary_key=True),
    Column("canonical_state_ref", String(256), nullable=False),
    Column("active_ocs_id", String(64)),
    Column("active_instance_id", String(128)),
    Column("current_gate", String(128), nullable=False),
    Column("status", String(64), nullable=False),
    Column("autonomy_budget", Integer, nullable=False),
    Column("autonomous_step_counter", Integer, nullable=False, default=0),
    Column("autonomous_handoff_counter", Integer, nullable=False, default=0),
    Column("repair_cycle_counter", Integer, nullable=False, default=0),
    Column("version", Integer, nullable=False, default=1),
)

bindings = Table(
    "trial_bindings",
    metadata,
    Column("binding_id", String(128), primary_key=True),
    Column("mission_id", String(128), nullable=False),
    Column("ocs_id", String(64), nullable=False),
    Column("instance_id", String(128), nullable=False),
    Column("predecessor_instance_id", String(128)),
    Column("generation", Integer, nullable=False),
    Column("fencing_epoch", Integer, nullable=False),
    Column("state_namespace_ref", String(256), nullable=False),
    Column("memory_namespace_ref", String(256), nullable=False),
    Column("authority_ref", String(256), nullable=False),
    Column("status", String(64), nullable=False),
    Column("checkpoint_ref", String(128)),
    Column("created_at", String(64), nullable=False),
    UniqueConstraint(
        "mission_id", "ocs_id", "generation", name="uq_trial_binding_generation"
    ),
)

fencing = Table(
    "trial_fencing",
    metadata,
    Column("mission_id", String(128), primary_key=True),
    Column("ocs_id", String(64), primary_key=True),
    Column("epoch", Integer, nullable=False),
)

checkpoints = Table(
    "trial_checkpoints",
    metadata,
    Column("checkpoint_id", String(128), primary_key=True),
    Column("mission_id", String(128), nullable=False),
    Column("instance_id", String(128), nullable=False),
    Column("ocs_id", String(64), nullable=False),
    Column("sequence", Integer, nullable=False),
    Column("canonical_state_ref", String(256), nullable=False),
    Column("local_state_hash", String(64), nullable=False),
    Column("created_at", String(64), nullable=False),
    UniqueConstraint("mission_id", "sequence", name="uq_trial_checkpoint_sequence"),
)

handoffs = Table(
    "trial_handoffs",
    metadata,
    Column("handoff_id", String(128), primary_key=True),
    Column("mission_id", String(128), nullable=False),
    Column("route_id", String(160), nullable=False),
    Column("source_instance_id", String(128), nullable=False),
    Column("source_ocs_id", String(64), nullable=False),
    Column("target_instance_id", String(128), nullable=False),
    Column("target_ocs_id", String(64), nullable=False),
    Column("checkpoint_ref", String(128), nullable=False),
    Column("envelope_hash", String(64), nullable=False),
    Column("accepted", Boolean, nullable=False, default=False),
    Column("acceptance_receipt_ref", String(128)),
    Column("created_at", String(64), nullable=False),
)

receipts = Table(
    "trial_receipts",
    metadata,
    Column("receipt_id", String(128), primary_key=True),
    Column("mission_id", String(128), nullable=False),
    Column("kind", String(64), nullable=False),
    Column("payload_hash", String(64), nullable=False),
    Column("created_at", String(64), nullable=False),
)

state_entries = Table(
    "trial_state_entries",
    metadata,
    Column("mission_id", String(128), primary_key=True),
    Column("namespace_key", String(320), primary_key=True),
    Column("value_hash", String(64), nullable=False),
    Column("last_instance_id", String(128), nullable=False),
    Column("last_epoch", Integer, nullable=False),
)

ledger = Table(
    "trial_append_only_ledger",
    metadata,
    Column("ledger_id", String(128), primary_key=True),
    Column("mission_id", String(128), nullable=False),
    Column("event_type", String(64), nullable=False),
    Column("event_ref", String(128), nullable=False),
    Column("payload_hash", String(64), nullable=False),
    Column("created_at", String(64), nullable=False),
)


@dataclass(frozen=True, slots=True)
class BindingReceipt:
    binding_id: str
    mission_id: str
    ocs_id: str
    instance_id: str
    generation: int
    fencing_epoch: int
    status: BindingStatus
    receipt_id: str


@dataclass(frozen=True, slots=True)
class MutationReceipt:
    decision: Decision
    mutation_count: int
    reason: str
    receipt_id: str


@dataclass(frozen=True, slots=True)
class HandoffReceipt:
    handoff_id: str
    acceptance_receipt_id: str
    source_ocs_id: str
    target_ocs_id: str


class TrialStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create_schema(self) -> None:
        metadata.create_all(self._engine)

    def create_mission(
        self,
        mission_id: str,
        *,
        canonical_state_ref: str,
        current_gate: str,
        autonomy_budget: int,
    ) -> None:
        if autonomy_budget < 1:
            raise TrialHold("autonomy_budget_required")
        with self._engine.begin() as conn:
            conn.execute(
                insert(missions).values(
                    mission_id=mission_id,
                    canonical_state_ref=canonical_state_ref,
                    current_gate=current_gate,
                    status=MissionStatus.BUILD_VERIFICATION.value,
                    autonomy_budget=autonomy_budget,
                    autonomous_step_counter=0,
                    autonomous_handoff_counter=0,
                    repair_cycle_counter=0,
                    version=1,
                )
            )
            self._append_ledger(
                conn, mission_id, "mission_created", mission_id, {"gate": current_gate}
            )

    def bind(
        self,
        mission_id: str,
        ocs_id: str,
        instance_id: str,
        *,
        authority_ref: str,
        activate_if_empty: bool = False,
    ) -> BindingReceipt:
        if not all((mission_id, ocs_id, instance_id, authority_ref)):
            raise TrialHold("binding_identity_or_authority_ambiguous")
        with self._engine.begin() as conn:
            mission = conn.execute(
                select(missions).where(missions.c.mission_id == mission_id)
            ).mappings().one()
            current_epoch = conn.execute(
                select(fencing.c.epoch).where(
                    and_(
                        fencing.c.mission_id == mission_id,
                        fencing.c.ocs_id == ocs_id,
                    )
                )
            ).scalar_one_or_none()
            epoch = 1 if current_epoch is None else int(current_epoch) + 1
            if current_epoch is None:
                conn.execute(
                    insert(fencing).values(
                        mission_id=mission_id, ocs_id=ocs_id, epoch=epoch
                    )
                )
                generation = 1
                predecessor: str | None = None
            else:
                conn.execute(
                    update(fencing)
                    .where(
                        and_(
                            fencing.c.mission_id == mission_id,
                            fencing.c.ocs_id == ocs_id,
                        )
                    )
                    .values(epoch=epoch)
                )
                prior = conn.execute(
                    select(bindings)
                    .where(
                        and_(
                            bindings.c.mission_id == mission_id,
                            bindings.c.ocs_id == ocs_id,
                        )
                    )
                    .order_by(bindings.c.generation.desc())
                    .limit(1)
                ).mappings().one()
                generation = int(prior["generation"]) + 1
                predecessor = str(prior["instance_id"])
                conn.execute(
                    update(bindings)
                    .where(bindings.c.binding_id == prior["binding_id"])
                    .values(status=BindingStatus.FENCED.value)
                )

            should_activate = activate_if_empty and mission["active_instance_id"] is None
            status = BindingStatus.ACTIVE if should_activate else BindingStatus.BOUND
            binding_id = f"binding:{canonical_hash({'mission': mission_id, 'ocs': ocs_id, 'instance': instance_id, 'epoch': epoch})}"
            conn.execute(
                insert(bindings).values(
                    binding_id=binding_id,
                    mission_id=mission_id,
                    ocs_id=ocs_id,
                    instance_id=instance_id,
                    predecessor_instance_id=predecessor,
                    generation=generation,
                    fencing_epoch=epoch,
                    state_namespace_ref=state_namespace(mission_id, ocs_id),
                    memory_namespace_ref=memory_namespace(mission_id, ocs_id),
                    authority_ref=authority_ref,
                    status=status.value,
                    created_at=_now(),
                )
            )
            if should_activate:
                conn.execute(
                    update(missions)
                    .where(missions.c.mission_id == mission_id)
                    .values(
                        active_ocs_id=ocs_id,
                        active_instance_id=instance_id,
                        version=int(mission["version"]) + 1,
                    )
                )
            receipt_id = self._receipt(
                conn,
                mission_id,
                "binding",
                {
                    "binding_id": binding_id,
                    "ocs_id": ocs_id,
                    "instance_id": instance_id,
                    "epoch": epoch,
                },
            )
            return BindingReceipt(
                binding_id=binding_id,
                mission_id=mission_id,
                ocs_id=ocs_id,
                instance_id=instance_id,
                generation=generation,
                fencing_epoch=epoch,
                status=status,
                receipt_id=receipt_id,
            )

    def checkpoint(
        self,
        mission_id: str,
        *,
        instance_id: str,
        local_state: dict[str, Any],
    ) -> str:
        with self._engine.begin() as conn:
            mission = conn.execute(
                select(missions).where(missions.c.mission_id == mission_id)
            ).mappings().one()
            if mission["active_instance_id"] != instance_id:
                raise TrialHold("checkpoint_requires_active_instance")
            binding = conn.execute(
                select(bindings).where(
                    and_(
                        bindings.c.mission_id == mission_id,
                        bindings.c.instance_id == instance_id,
                        bindings.c.status == BindingStatus.ACTIVE.value,
                    )
                )
            ).mappings().one()
            seq = (
                conn.execute(
                    select(checkpoints.c.sequence)
                    .where(checkpoints.c.mission_id == mission_id)
                    .order_by(checkpoints.c.sequence.desc())
                    .limit(1)
                ).scalar_one_or_none()
                or 0
            ) + 1
            checkpoint_id = f"checkpoint:{canonical_hash({'mission': mission_id, 'instance': instance_id, 'sequence': seq, 'state': local_state})}"
            conn.execute(
                insert(checkpoints).values(
                    checkpoint_id=checkpoint_id,
                    mission_id=mission_id,
                    instance_id=instance_id,
                    ocs_id=binding["ocs_id"],
                    sequence=seq,
                    canonical_state_ref=mission["canonical_state_ref"],
                    local_state_hash=canonical_hash(local_state),
                    created_at=_now(),
                )
            )
            conn.execute(
                update(bindings)
                .where(bindings.c.binding_id == binding["binding_id"])
                .values(checkpoint_ref=checkpoint_id)
            )
            self._receipt(
                conn,
                mission_id,
                "checkpoint",
                {"checkpoint_id": checkpoint_id, "instance_id": instance_id},
            )
            self._append_ledger(
                conn,
                mission_id,
                "checkpoint",
                checkpoint_id,
                {"instance_id": instance_id},
            )
            return checkpoint_id

    def write_state(
        self,
        mission_id: str,
        *,
        ocs_id: str,
        instance_id: str,
        epoch: int,
        namespace_key: str,
        value: Any,
    ) -> MutationReceipt:
        with self._engine.begin() as conn:
            reason = self._write_denial_reason(
                conn,
                mission_id=mission_id,
                ocs_id=ocs_id,
                instance_id=instance_id,
                epoch=epoch,
                namespace_key=namespace_key,
            )
            if reason is not None:
                receipt_id = self._receipt(
                    conn,
                    mission_id,
                    "deny",
                    {
                        "reason": reason,
                        "instance_id": instance_id,
                        "epoch": epoch,
                        "mutation_count": 0,
                    },
                )
                return MutationReceipt(Decision.DENY, 0, reason, receipt_id)
            current = conn.execute(
                select(state_entries).where(
                    and_(
                        state_entries.c.mission_id == mission_id,
                        state_entries.c.namespace_key == namespace_key,
                    )
                )
            ).mappings().one_or_none()
            payload = {
                "value_hash": canonical_hash(value),
                "last_instance_id": instance_id,
                "last_epoch": epoch,
            }
            if current is None:
                conn.execute(
                    insert(state_entries).values(
                        mission_id=mission_id,
                        namespace_key=namespace_key,
                        **payload,
                    )
                )
            else:
                conn.execute(
                    update(state_entries)
                    .where(
                        and_(
                            state_entries.c.mission_id == mission_id,
                            state_entries.c.namespace_key == namespace_key,
                        )
                    )
                    .values(**payload)
                )
            receipt_id = self._receipt(
                conn,
                mission_id,
                "state_write",
                {
                    "instance_id": instance_id,
                    "epoch": epoch,
                    "namespace_key": namespace_key,
                    "mutation_count": 1,
                },
            )
            return MutationReceipt(Decision.ALLOW, 1, "ok", receipt_id)

    def issue_handoff(
        self,
        mission_id: str,
        *,
        route_id: str,
        target_instance_id: str,
        target_ocs_id: str,
        envelope: dict[str, Any],
    ) -> str:
        route = L2_ROUTES.get(route_id)
        if route is None:
            raise TrialHold("unlisted_l2_route")
        with self._engine.begin() as conn:
            mission = conn.execute(
                select(missions).where(missions.c.mission_id == mission_id)
            ).mappings().one()
            source_ocs = str(mission["active_ocs_id"] or "")
            source_instance = str(mission["active_instance_id"] or "")
            if not source_ocs or not source_instance:
                raise TrialHold("active_source_missing")
            if route.source_ocs is not None and route.source_ocs != source_ocs:
                raise TrialHold("route_source_mismatch")
            if route.target_ocs is not None and route.target_ocs != target_ocs_id:
                raise TrialHold("route_target_mismatch")
            source_binding = conn.execute(
                select(bindings).where(
                    and_(
                        bindings.c.mission_id == mission_id,
                        bindings.c.instance_id == source_instance,
                        bindings.c.status == BindingStatus.ACTIVE.value,
                    )
                )
            ).mappings().one()
            checkpoint_ref = source_binding["checkpoint_ref"]
            if checkpoint_ref is None:
                raise TrialHold("source_checkpoint_required")
            target_binding = conn.execute(
                select(bindings).where(
                    and_(
                        bindings.c.mission_id == mission_id,
                        bindings.c.instance_id == target_instance_id,
                        bindings.c.ocs_id == target_ocs_id,
                        bindings.c.status == BindingStatus.BOUND.value,
                    )
                )
            ).mappings().one_or_none()
            if target_binding is None:
                raise TrialHold("target_binding_required")
            handoff_id = f"handoff:{canonical_hash({'mission': mission_id, 'route': route_id, 'source': source_instance, 'target': target_instance_id, 'checkpoint': checkpoint_ref, 'envelope': envelope})}"
            conn.execute(
                insert(handoffs).values(
                    handoff_id=handoff_id,
                    mission_id=mission_id,
                    route_id=route_id,
                    source_instance_id=source_instance,
                    source_ocs_id=source_ocs,
                    target_instance_id=target_instance_id,
                    target_ocs_id=target_ocs_id,
                    checkpoint_ref=checkpoint_ref,
                    envelope_hash=canonical_hash(envelope),
                    accepted=False,
                    created_at=_now(),
                )
            )
            self._append_ledger(conn, mission_id, "handoff_issued", handoff_id, envelope)
            return handoff_id

    def accept_handoff(self, mission_id: str, handoff_id: str) -> HandoffReceipt:
        with self._engine.begin() as conn:
            row = conn.execute(
                select(handoffs).where(
                    and_(
                        handoffs.c.mission_id == mission_id,
                        handoffs.c.handoff_id == handoff_id,
                    )
                )
            ).mappings().one()
            if bool(row["accepted"]):
                raise TrialHold("blind_retry_forbidden")
            mission = conn.execute(
                select(missions).where(missions.c.mission_id == mission_id)
            ).mappings().one()
            if mission["active_instance_id"] != row["source_instance_id"]:
                raise TrialHold("source_no_longer_active")
            target = conn.execute(
                select(bindings).where(
                    and_(
                        bindings.c.mission_id == mission_id,
                        bindings.c.instance_id == row["target_instance_id"],
                        bindings.c.status == BindingStatus.BOUND.value,
                    )
                )
            ).mappings().one()
            current_steps = int(mission["autonomous_step_counter"])
            current_handoffs = int(mission["autonomous_handoff_counter"])
            if current_steps + 1 > int(mission["autonomy_budget"]):
                conn.execute(
                    update(missions)
                    .where(missions.c.mission_id == mission_id)
                    .values(status=MissionStatus.HOLD.value)
                )
                raise TrialHold("autonomy_budget_exhausted")
            conn.execute(
                update(bindings)
                .where(
                    and_(
                        bindings.c.mission_id == mission_id,
                        bindings.c.instance_id == row["source_instance_id"],
                    )
                )
                .values(status=BindingStatus.QUIESCENT.value)
            )
            conn.execute(
                update(bindings)
                .where(bindings.c.binding_id == target["binding_id"])
                .values(status=BindingStatus.ACTIVE.value)
            )
            receipt_id = self._receipt(
                conn,
                mission_id,
                "handoff_acceptance",
                {
                    "handoff_id": handoff_id,
                    "target_instance_id": row["target_instance_id"],
                },
            )
            conn.execute(
                update(handoffs)
                .where(handoffs.c.handoff_id == handoff_id)
                .values(accepted=True, acceptance_receipt_ref=receipt_id)
            )
            conn.execute(
                update(missions)
                .where(missions.c.mission_id == mission_id)
                .values(
                    active_ocs_id=row["target_ocs_id"],
                    active_instance_id=row["target_instance_id"],
                    autonomous_step_counter=current_steps + 1,
                    autonomous_handoff_counter=current_handoffs + 1,
                    version=int(mission["version"]) + 1,
                )
            )
            self._append_ledger(
                conn,
                mission_id,
                "handoff_accepted",
                receipt_id,
                {"handoff_id": handoff_id},
            )
            return HandoffReceipt(
                handoff_id=handoff_id,
                acceptance_receipt_id=receipt_id,
                source_ocs_id=str(row["source_ocs_id"]),
                target_ocs_id=str(row["target_ocs_id"]),
            )

    def recover(
        self,
        mission_id: str,
        *,
        ocs_id: str,
        successor_instance_id: str,
        authority_ref: str,
    ) -> BindingReceipt:
        with self._engine.begin() as conn:
            mission = conn.execute(
                select(missions).where(missions.c.mission_id == mission_id)
            ).mappings().one()
            if mission["active_ocs_id"] != ocs_id:
                raise TrialHold("recovery_requires_active_ocs")
            active_instance = str(mission["active_instance_id"] or "")
            active = conn.execute(
                select(bindings).where(
                    and_(
                        bindings.c.mission_id == mission_id,
                        bindings.c.instance_id == active_instance,
                    )
                )
            ).mappings().one()
            if active["checkpoint_ref"] is None:
                raise TrialHold("recovery_checkpoint_required")
            conn.execute(
                update(bindings)
                .where(bindings.c.binding_id == active["binding_id"])
                .values(status=BindingStatus.FENCED.value)
            )
            conn.execute(
                update(missions)
                .where(missions.c.mission_id == mission_id)
                .values(active_ocs_id=None, active_instance_id=None)
            )
        receipt = self.bind(
            mission_id,
            ocs_id,
            successor_instance_id,
            authority_ref=authority_ref,
            activate_if_empty=True,
        )
        with self._engine.begin() as conn:
            self._receipt(
                conn,
                mission_id,
                "recovery",
                {
                    "predecessor": active_instance,
                    "successor": successor_instance_id,
                    "epoch": receipt.fencing_epoch,
                },
            )
        return receipt

    def projection(self, mission_id: str) -> dict[str, Any]:
        with self._engine.connect() as conn:
            mission = dict(
                conn.execute(
                    select(missions).where(missions.c.mission_id == mission_id)
                ).mappings().one()
            )
            active = None
            if mission["active_instance_id"] is not None:
                active_row = conn.execute(
                    select(bindings).where(
                        and_(
                            bindings.c.mission_id == mission_id,
                            bindings.c.instance_id == mission["active_instance_id"],
                        )
                    )
                ).mappings().one()
                active = {
                    "ocs_id": active_row["ocs_id"],
                    "instance_id": active_row["instance_id"],
                    "fencing_epoch": active_row["fencing_epoch"],
                    "authority_ref": active_row["authority_ref"],
                    "checkpoint_ref": active_row["checkpoint_ref"],
                }
            return {
                "mission_id": mission_id,
                "mission_status": mission["status"],
                "current_gate": mission["current_gate"],
                "active": active,
                "counters": {
                    "autonomous_step_counter": mission["autonomous_step_counter"],
                    "autonomous_handoff_counter": mission["autonomous_handoff_counter"],
                    "repair_cycle_counter": mission["repair_cycle_counter"],
                },
            }

    def count_state_entries(self, mission_id: str) -> int:
        with self._engine.connect() as conn:
            return len(
                conn.execute(
                    select(state_entries.c.namespace_key).where(
                        state_entries.c.mission_id == mission_id
                    )
                ).all()
            )

    def mark_implementation_complete(self, mission_id: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                update(missions)
                .where(missions.c.mission_id == mission_id)
                .values(status=MissionStatus.IMPLEMENTATION_COMPLETE.value)
            )
            self._receipt(
                conn,
                mission_id,
                "builder_verification",
                {"status": "implementation_complete"},
            )

    def _write_denial_reason(
        self,
        conn: Any,
        *,
        mission_id: str,
        ocs_id: str,
        instance_id: str,
        epoch: int,
        namespace_key: str,
    ) -> str | None:
        mission = conn.execute(
            select(missions).where(missions.c.mission_id == mission_id)
        ).mappings().one()
        if mission["active_ocs_id"] != ocs_id or mission["active_instance_id"] != instance_id:
            return "instance_not_active"
        if not namespace_key.startswith(state_namespace(mission_id, ocs_id)):
            return "cross_ocs_namespace_write_forbidden"
        current_epoch = conn.execute(
            select(fencing.c.epoch).where(
                and_(
                    fencing.c.mission_id == mission_id,
                    fencing.c.ocs_id == ocs_id,
                )
            )
        ).scalar_one()
        if int(current_epoch) != epoch:
            return "stale_epoch"
        return None

    def _receipt(
        self, conn: Any, mission_id: str, kind: str, payload: dict[str, Any]
    ) -> str:
        receipt_id = f"receipt:{canonical_hash({'mission': mission_id, 'kind': kind, 'payload': payload, 'at': _now()})}"
        conn.execute(
            insert(receipts).values(
                receipt_id=receipt_id,
                mission_id=mission_id,
                kind=kind,
                payload_hash=canonical_hash(payload),
                created_at=_now(),
            )
        )
        self._append_ledger(conn, mission_id, f"receipt:{kind}", receipt_id, payload)
        return receipt_id

    def _append_ledger(
        self,
        conn: Any,
        mission_id: str,
        event_type: str,
        event_ref: str,
        payload: dict[str, Any],
    ) -> None:
        ledger_id = f"ledger:{canonical_hash({'mission': mission_id, 'event_type': event_type, 'event_ref': event_ref, 'payload': payload, 'at': _now()})}"
        conn.execute(
            insert(ledger).values(
                ledger_id=ledger_id,
                mission_id=mission_id,
                event_type=event_type,
                event_ref=event_ref,
                payload_hash=canonical_hash(payload),
                created_at=_now(),
            )
        )


def _now() -> str:
    return datetime.now(UTC).isoformat()
