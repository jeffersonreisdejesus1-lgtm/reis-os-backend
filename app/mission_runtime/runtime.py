from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from .contracts import MissionSnapshot, MissionStatus, RepositoryEffectReceipt
from .store import MissionRuntimeStore


def _hash_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


class RepositoryMaintenanceAdapter:
    """Bounded filesystem effect used by the IB9 repository-maintenance pilot."""

    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root
        self.effect_count = 0

    def apply(self, relative_path: str, content: str) -> tuple[str, str, str]:
        target = self.repository_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        before = target.read_bytes() if target.exists() else b""
        before_hash = _hash_bytes(before)
        target.write_text(content, encoding="utf-8")
        self.effect_count += 1
        after = target.read_bytes()
        after_hash = _hash_bytes(after)
        return before_hash, after_hash, _hash_bytes(target.read_bytes())

    def readback_hash(self, relative_path: str) -> str:
        return _hash_bytes((self.repository_root / relative_path).read_bytes())


class MissionRuntime:
    def __init__(
        self,
        store: MissionRuntimeStore,
        adapter: RepositoryMaintenanceAdapter,
    ) -> None:
        self.store = store
        self.adapter = adapter

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
            mission_id,
            generation=generation,
            instance_id=instance_id,
        )
        replay = self.store.effect(mission_id, idempotency_key)
        if replay is not None:
            if replay.path != relative_path:
                raise ValueError("mission_effect_idempotency_conflict")
            if self.adapter.readback_hash(relative_path) != replay.after_hash:
                raise ValueError("mission_effect_readback_drift")
            return replace(replay, duplicate_effect=False)

        before_hash, after_hash, readback_hash = self.adapter.apply(
            relative_path,
            content,
        )
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
        self.store.record_effect(receipt, {"content_hash": after_hash})
        return receipt

    def checkpoint(
        self,
        mission_id: str,
        *,
        generation: int,
        instance_id: str,
    ) -> MissionSnapshot:
        snapshot = self._require_current_generation(
            mission_id,
            generation=generation,
            instance_id=instance_id,
        )
        effects = self.store.event_types(mission_id)
        checkpoint_hash = sha256("|".join(effects).encode()).hexdigest()
        checkpointed = replace(
            snapshot,
            status=MissionStatus.CHECKPOINTED,
            checkpoint_version=snapshot.checkpoint_version + 1,
            checkpoint_hash=checkpoint_hash,
        )
        self.store.save(checkpointed, "MISSION_CHECKPOINTED")
        return checkpointed

    def replace_instance(
        self,
        mission_id: str,
        *,
        old_generation: int,
        old_instance_id: str,
        new_instance_id: str,
    ) -> MissionSnapshot:
        snapshot = self._require_current_generation(
            mission_id,
            generation=old_generation,
            instance_id=old_instance_id,
        )
        if snapshot.status is not MissionStatus.CHECKPOINTED:
            raise ValueError("mission_checkpoint_required_for_replacement")
        pending = replace(snapshot, status=MissionStatus.REPLACEMENT_PENDING)
        self.store.save(pending, "MISSION_REPLACEMENT_PENDING")
        successor = replace(
            pending,
            generation=old_generation + 1,
            instance_id=new_instance_id,
            status=MissionStatus.RECOVERED,
            transcript_ref=None,
        )
        self.store.save(successor, "MISSION_RECOVERED_WITHOUT_TRANSCRIPT")
        return successor

    def recover_without_transcript(self, mission_id: str) -> MissionSnapshot:
        snapshot = self.store.load(mission_id)
        if snapshot.transcript_ref is not None:
            raise ValueError("conversation_transcript_must_not_be_recovery_input")
        if snapshot.checkpoint_hash is None:
            raise ValueError("mission_checkpoint_required_for_recovery")
        return snapshot

    def close(
        self,
        mission_id: str,
        *,
        generation: int,
        instance_id: str,
    ) -> MissionSnapshot:
        snapshot = self._require_current_generation(
            mission_id,
            generation=generation,
            instance_id=instance_id,
        )
        closed = replace(snapshot, status=MissionStatus.CLOSED)
        self.store.save(closed, "MISSION_CLOSED")
        return closed

    def _require_current_generation(
        self,
        mission_id: str,
        *,
        generation: int,
        instance_id: str,
    ) -> MissionSnapshot:
        snapshot = self.store.load(mission_id)
        if snapshot.status is MissionStatus.CLOSED:
            raise ValueError("mission_closed")
        if snapshot.generation != generation:
            raise ValueError("mission_generation_fenced")
        if snapshot.instance_id != instance_id:
            raise ValueError("mission_instance_fenced")
        return snapshot
