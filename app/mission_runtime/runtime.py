# ruff: noqa: E501
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from .contracts import (
    BindingStatus,
    MissionSnapshot,
    MissionStatus,
    RepositoryEffectReceipt,
)
from .store import MissionRuntimeStore


def _hash_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


class RepositoryMaintenanceAdapter:
    """Bounded filesystem effect used by the IB9 repository-maintenance pilot."""

    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root.resolve()
        self.effect_count = 0

    def _safe_target(self, relative_path: str) -> Path:
        if not relative_path or "\x00" in relative_path:
            raise ValueError("repository_path_invalid")
        candidate = Path(relative_path)
        if candidate.is_absolute() or any(part == ".." for part in candidate.parts):
            raise ValueError("repository_path_escape")
        current = self.repository_root
        for part in candidate.parts:
            current /= part
            if current.is_symlink():
                raise ValueError("repository_path_symlink")
        target = (self.repository_root / candidate).resolve(strict=False)
        if target == self.repository_root or self.repository_root not in target.parents:
            raise ValueError("repository_path_escape")
        return target

    def apply(self, relative_path: str, content: str) -> tuple[str, str, str]:
        target = self._safe_target(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        before = target.read_bytes() if target.exists() else b""
        before_hash = _hash_bytes(before)
        target.write_text(content, encoding="utf-8")
        self.effect_count += 1
        after = target.read_bytes()
        after_hash = _hash_bytes(after)
        return before_hash, after_hash, after_hash

    def readback_hash(self, relative_path: str) -> str:
        return _hash_bytes(self._safe_target(relative_path).read_bytes())


class MissionRuntime:
    def __init__(
        self,
        store: MissionRuntimeStore,
        adapter: RepositoryMaintenanceAdapter,
        *,
        binding_validator: Callable[[MissionSnapshot], BindingStatus] | None = None,
    ) -> None:
        self.store = store
        self.adapter = adapter
        self.binding_validator = binding_validator

    def _binding_status(self, snapshot: MissionSnapshot) -> BindingStatus:
        if self.binding_validator is None:
            return BindingStatus.UNKNOWN
        return (
            BindingStatus.VERIFIED
            if self.binding_validator(snapshot) is BindingStatus.VERIFIED
            else BindingStatus.HOLD
        )

    def start(
        self,
        *,
        mission_id: str,
        organization_id: str,
        ocs_id: str,
        authority_ref: str,
        state_namespace: str,
        memory_namespace: str,
        instance_id: str,
    ) -> MissionSnapshot:
        snapshot = MissionSnapshot(
            mission_id=mission_id,
            organization_id=organization_id,
            ocs_id=ocs_id,
            authority_ref=authority_ref,
            state_namespace=state_namespace,
            memory_namespace=memory_namespace,
            generation=1,
            instance_id=instance_id,
            status=MissionStatus.ACTIVE,
            checkpoint_version=0,
            checkpoint_hash=None,
            transcript_ref=None,
        )
        self.store.create(snapshot)
        return snapshot

    def execute_repository_effect(
        self,
        *,
        mission_id: str,
        generation: int,
        instance_id: str,
        idempotency_key: str,
        relative_path: str,
        content: str,
    ) -> RepositoryEffectReceipt:
        snapshot = self._require_current_generation(
            mission_id, generation=generation, instance_id=instance_id
        )
        requested_hash = _hash_bytes(content.encode("utf-8"))
        existing = self.store.claim_effect(
            mission_id, idempotency_key, generation=generation, path=relative_path,
            requested_hash=requested_hash,
        )
        if existing is not None:
            status, existing_path, existing_hash = existing
            # An abandoned claim is fail-closed. Do not reinterpret it as a
            # payload conflict or apply an effect without an explicit recovery
            # protocol for the pending claim.
            if status == "PENDING":
                raise ValueError("mission_effect_pending")
            if existing_path != relative_path or existing_hash != requested_hash:
                raise ValueError("mission_effect_idempotency_conflict")
            replay = self.store.effect(mission_id, idempotency_key)
            if replay is None:
                raise ValueError("mission_effect_record_missing")
            if self.adapter.readback_hash(relative_path) != replay.after_hash:
                raise ValueError("mission_effect_readback_drift")
            return replace(replay, duplicate_effect=True)

        before_hash, after_hash, readback_hash = self.adapter.apply(relative_path, content)
        receipt = RepositoryEffectReceipt(
            mission_id=mission_id,
            idempotency_key=idempotency_key,
            generation=snapshot.generation,
            path=relative_path,
            before_hash=before_hash,
            after_hash=after_hash,
            duplicate_effect=False,
            readback_hash=readback_hash,
        )
        if after_hash != readback_hash:
            raise ValueError("mission_effect_readback_mismatch")
        self.store.apply_effect(
            receipt, {"content_hash": requested_hash, "command": "repository_maintenance"}
        )
        return receipt

    def checkpoint(self, mission_id: str, *, generation: int, instance_id: str) -> MissionSnapshot:
        snapshot = self._require_current_generation(
            mission_id, generation=generation, instance_id=instance_id
        )
        if snapshot.status is not MissionStatus.ACTIVE:
            raise ValueError("mission_checkpoint_invalid_state")
        records = self.store.effect_records(mission_id)
        material = {
            "mission": {
                "mission_id": snapshot.mission_id,
                "organization_id": snapshot.organization_id,
                "ocs_id": snapshot.ocs_id,
                "authority_ref": snapshot.authority_ref,
                "state_namespace": snapshot.state_namespace,
                "memory_namespace": snapshot.memory_namespace,
                "generation": snapshot.generation,
                "instance_id": snapshot.instance_id,
            },
            "effects": records,
        }
        material_json = json.dumps(material, sort_keys=True, separators=(",", ":"))
        checkpointed = replace(
            snapshot, status=MissionStatus.CHECKPOINTED,
            checkpoint_version=snapshot.checkpoint_version + 1,
            checkpoint_hash=sha256(material_json.encode()).hexdigest(),
            checkpoint_material_json=material_json,
        )
        self.store.save(checkpointed, "MISSION_CHECKPOINTED")
        return checkpointed

    def replace_instance(
        self, mission_id: str, *, old_generation: int, old_instance_id: str,
        new_instance_id: str,
    ) -> MissionSnapshot:
        snapshot = self.store.load(mission_id)
        # Replacement is the one deliberate transition authorized from a
        # checkpoint. It must still fence identity/generation, while effects
        # remain disallowed in CHECKPOINTED and REPLACEMENT_PENDING.
        if snapshot.status is not MissionStatus.CHECKPOINTED:
            if snapshot.status is MissionStatus.CLOSED:
                raise ValueError("mission_closed")
            raise ValueError("mission_state_fenced")
        if snapshot.generation != old_generation:
            raise ValueError("mission_generation_fenced")
        if snapshot.instance_id != old_instance_id:
            raise ValueError("mission_instance_fenced")
        pending = replace(snapshot, status=MissionStatus.REPLACEMENT_PENDING)
        self.store.save(pending, "MISSION_REPLACEMENT_PENDING")
        successor = replace(
            pending, generation=old_generation + 1, instance_id=new_instance_id,
            status=MissionStatus.RECOVERED, transcript_ref=None,
        )
        self.store.save(successor, "MISSION_RECOVERED_WITHOUT_TRANSCRIPT")
        return successor

    def recover_without_transcript(self, mission_id: str) -> MissionSnapshot:
        snapshot = self.store.load(mission_id)
        if snapshot.transcript_ref is not None:
            raise ValueError("conversation_transcript_must_not_be_recovery_input")
        if snapshot.checkpoint_hash is None or snapshot.checkpoint_material_json is None:
            raise ValueError("mission_checkpoint_required_for_recovery")
        if sha256(snapshot.checkpoint_material_json.encode()).hexdigest() != snapshot.checkpoint_hash:
            raise ValueError("mission_checkpoint_hash_mismatch")
        material = json.loads(snapshot.checkpoint_material_json)
        if not isinstance(material, dict):
            raise ValueError("mission_checkpoint_material_malformed")
        if material.get("mission") != {
            "mission_id": snapshot.mission_id,
            "organization_id": snapshot.organization_id,
            "ocs_id": snapshot.ocs_id,
            "authority_ref": snapshot.authority_ref,
            "state_namespace": snapshot.state_namespace,
            "memory_namespace": snapshot.memory_namespace,
            "generation": snapshot.generation - 1,
            "instance_id": material["mission"]["instance_id"],
        }:
            raise ValueError("mission_checkpoint_identity_mismatch")
        if not self.store.checkpoint_effects_match(mission_id, material.get("effects", [])):
            raise ValueError("mission_checkpoint_material_mismatch")
        if snapshot.status not in {MissionStatus.RECOVERED, MissionStatus.CLOSED}:
            raise ValueError("mission_recovery_invalid_state")
        return snapshot

    def close(self, mission_id: str, *, generation: int, instance_id: str) -> MissionSnapshot:
        snapshot = self._require_current_generation(
            mission_id, generation=generation, instance_id=instance_id
        )
        if snapshot.status is not MissionStatus.RECOVERED:
            raise ValueError("mission_close_invalid_state")
        binding_status = self._binding_status(snapshot)
        if binding_status is not BindingStatus.VERIFIED:
            held = replace(snapshot, binding_status=BindingStatus.HOLD)
            self.store.save(held, "MISSION_CLOSE_HOLD_BINDING_UNKNOWN")
            raise ValueError("mission_binding_validation_unknown")
        closed = replace(snapshot, status=MissionStatus.CLOSED, binding_status=binding_status)
        self.store.save(closed, "MISSION_CLOSED")
        return closed

    def _require_current_generation(
        self, mission_id: str, *, generation: int, instance_id: str
    ) -> MissionSnapshot:
        snapshot = self.store.load(mission_id)
        if snapshot.status is MissionStatus.CLOSED:
            raise ValueError("mission_closed")
        if snapshot.status not in {MissionStatus.ACTIVE, MissionStatus.RECOVERED}:
            raise ValueError("mission_state_fenced")
        if snapshot.generation != generation:
            raise ValueError("mission_generation_fenced")
        if snapshot.instance_id != instance_id:
            raise ValueError("mission_instance_fenced")
        return snapshot
