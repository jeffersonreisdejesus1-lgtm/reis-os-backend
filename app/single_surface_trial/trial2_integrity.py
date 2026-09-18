from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from sqlalchemy import and_, insert, select, update

from .trial2_store import (
    EffectResult,
    RecoverySnapshot,
    Trial2Hold,
    Trial2PersistentStore,
    _hash,
    bindings,
    checkpoints,
    effects,
    fencing,
    handoffs,
    missions,
    receipts,
)


class IntegrityCheckedTrial2Store(Trial2PersistentStore):
    """Trial 2 store with the Sýnesis F1/F2 fail-closed repairs applied."""

    def _validated_handoff_row(
        self, conn: Any, mission_id: str, handoff_id: str
    ) -> dict[str, Any]:
        row = dict(
            conn.execute(
                select(handoffs).where(
                    and_(
                        handoffs.c.mission_id == mission_id,
                        handoffs.c.handoff_id == handoff_id,
                    )
                )
            ).mappings().one()
        )
        try:
            envelope = json.loads(row["envelope_json"])
        except Exception as exc:
            raise Trial2Hold("handoff_envelope_integrity_failure") from exc
        if _hash(envelope) != row["envelope_hash"]:
            raise Trial2Hold("handoff_envelope_integrity_failure")
        return row

    def accept_handoff(self, mission_id: str, handoff_id: str) -> str:
        with self._engine.begin() as conn:
            mission = self._mission(conn, mission_id)
            row = self._validated_handoff_row(conn, mission_id, handoff_id)
            if row["accepted"]:
                raise Trial2Hold("blind_retry_forbidden")
            if mission["active_instance_id"] != row["source_instance_id"]:
                raise Trial2Hold("source_no_longer_active")
            source = self._binding(conn, mission_id, row["source_instance_id"])
            target = self._binding(conn, mission_id, row["target_instance_id"])
            if (
                not source.get("checkpoint_ref")
                or source["checkpoint_ref"] != row["checkpoint_ref"]
            ):
                raise Trial2Hold("checkpoint_integrity_or_continuity_failure")
            if target["status"] != "BOUND":
                raise Trial2Hold("target_binding_required")
            if int(mission["autonomous_step_counter"]) + 1 > int(
                mission["autonomy_budget"]
            ):
                raise Trial2Hold("autonomy_budget_exhausted")

            next_version = int(mission["version"]) + 1
            claimed = conn.execute(
                update(missions)
                .where(
                    and_(
                        missions.c.mission_id == mission_id,
                        missions.c.version == int(mission["version"]),
                        missions.c.active_instance_id == row["source_instance_id"],
                    )
                )
                .values(
                    active_ocs_id=row["target_ocs_id"],
                    active_instance_id=row["target_instance_id"],
                    current_handoff_ref=handoff_id,
                    autonomous_step_counter=int(mission["autonomous_step_counter"]) + 1,
                    autonomous_handoff_counter=int(
                        mission["autonomous_handoff_counter"]
                    )
                    + 1,
                    version=next_version,
                )
            )
            if claimed.rowcount != 1:
                raise Trial2Hold("concurrent_handoff_conflict")

            conn.execute(
                update(bindings)
                .where(bindings.c.binding_id == source["binding_id"])
                .values(status="QUIESCENT")
            )
            conn.execute(
                update(bindings)
                .where(bindings.c.binding_id == target["binding_id"])
                .values(status="ACTIVE")
            )
            receipt = self._receipt(
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
                .values(accepted=True, acceptance_receipt_ref=receipt)
            )
            self._observe(
                conn,
                mission_id,
                mission,
                self._mission(conn, mission_id),
                from_identity=row["source_ocs_id"],
                from_instance=row["source_instance_id"],
                to_identity=row["target_ocs_id"],
                to_instance=row["target_instance_id"],
                role=target["role"],
                authority_ref=target["authority_ref"],
                fencing_epoch=int(target["fencing_epoch"]),
                handoff_ref=handoff_id,
                receipt_ref=receipt,
                checkpoint_ref=row["checkpoint_ref"],
                outcome="handoff_accepted",
            )
            return receipt

    def recover_snapshot(
        self,
        mission_id: str,
        *,
        authority_validator: Callable[[str, str, str], bool],
    ) -> RecoverySnapshot:
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
            cp = dict(
                conn.execute(
                    select(checkpoints).where(
                        checkpoints.c.checkpoint_id == checkpoint_ref
                    )
                ).mappings().one()
            )
            try:
                local_state = json.loads(cp["local_state_json"])
            except Exception as exc:
                raise Trial2Hold("checkpoint_integrity_failure") from exc
            if _hash(local_state) != cp["local_state_hash"]:
                raise Trial2Hold("checkpoint_integrity_failure")

            epoch = conn.execute(
                select(fencing.c.epoch).where(
                    and_(
                        fencing.c.mission_id == mission_id,
                        fencing.c.ocs_id == actor,
                    )
                )
            ).scalar_one_or_none()
            if epoch is None or int(epoch) != int(binding["fencing_epoch"]):
                raise Trial2Hold("fencing_revalidation_failure")
            if not authority_validator(
                binding["authority_ref"], str(actor), binding["role"]
            ):
                raise Trial2Hold("authority_revalidation_failure")

            current_handoff = mission.get("current_handoff_ref")
            if current_handoff:
                h = self._validated_handoff_row(
                    conn, mission_id, str(current_handoff)
                )
                if h["accepted"]:
                    if not h["acceptance_receipt_ref"]:
                        raise Trial2Hold("handoff_receipt_recovery_failure")
                    persisted_receipt = conn.execute(
                        select(receipts.c.receipt_id).where(
                            receipts.c.receipt_id == h["acceptance_receipt_ref"]
                        )
                    ).scalar_one_or_none()
                    if persisted_receipt is None:
                        raise Trial2Hold("handoff_receipt_recovery_failure")

            snapshot = RecoverySnapshot(
                mission_id,
                str(actor),
                str(instance),
                mission["current_gate"],
                current_handoff,
                str(checkpoint_ref),
                binding["authority_ref"],
                binding["role"],
                int(binding["fencing_epoch"]),
                int(mission["autonomous_step_counter"]),
                int(mission["autonomous_handoff_counter"]),
                int(mission["repair_cycle_counter"]),
            )
            self._observe(
                conn,
                mission_id,
                mission,
                mission,
                from_identity=str(actor),
                from_instance=str(instance),
                to_identity=str(actor),
                to_instance=str(instance),
                role=binding["role"],
                authority_ref=binding["authority_ref"],
                fencing_epoch=int(binding["fencing_epoch"]),
                handoff_ref=current_handoff,
                checkpoint_ref=str(checkpoint_ref),
                outcome="restart_recovery_revalidated",
            )
            return snapshot

    def apply_synthetic_effect(
        self,
        mission_id: str,
        *,
        ocs_id: str,
        instance_id: str,
        epoch: int,
        authority_ref: str,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> EffectResult:
        payload_hash = _hash(payload)
        with self._engine.begin() as conn:
            mission = self._mission(conn, mission_id)
            if (
                mission["active_ocs_id"] != ocs_id
                or mission["active_instance_id"] != instance_id
            ):
                raise Trial2Hold("unauthorized_effect")
            binding = self._binding(conn, mission_id, instance_id)
            if int(binding["fencing_epoch"]) != epoch:
                raise Trial2Hold("stale_epoch")
            if binding["authority_ref"] != authority_ref:
                raise Trial2Hold("authority_mismatch")

            prior = conn.execute(
                select(effects).where(
                    and_(
                        effects.c.mission_id == mission_id,
                        effects.c.idempotency_key == idempotency_key,
                    )
                )
            ).mappings().one_or_none()
            if prior is not None:
                if prior["payload_hash"] != payload_hash:
                    raise Trial2Hold("idempotency_key_payload_mismatch")
                return EffectResult(
                    prior["effect_id"], prior["receipt_ref"], 0, True
                )

            receipt = self._receipt(
                conn,
                mission_id,
                "effect",
                {
                    "idempotency_key": idempotency_key,
                    "payload_hash": payload_hash,
                },
            )
            effect_id = "effect:" + _hash(
                {"mission": mission_id, "key": idempotency_key, "payload": payload}
            )
            conn.execute(
                insert(effects).values(
                    effect_id=effect_id,
                    mission_id=mission_id,
                    instance_id=instance_id,
                    ocs_id=ocs_id,
                    fencing_epoch=epoch,
                    authority_ref=authority_ref,
                    idempotency_key=idempotency_key,
                    payload_hash=payload_hash,
                    receipt_ref=receipt,
                    created_at=self._now_for_effect(),
                )
            )
            return EffectResult(effect_id, receipt, 1, False)

    @staticmethod
    def _now_for_effect() -> str:
        from .trial2_store import _now

        return _now()
