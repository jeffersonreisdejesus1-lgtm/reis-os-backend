# ruff: noqa: E501,I001
from __future__ import annotations

import json
import os
import stat
from collections.abc import Callable
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from .contracts import BindingStatus, MissionSnapshot, MissionStatus, RepositoryEffectReceipt
from .store import MissionRuntimeStore


def _hash_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


class RepositoryMaintenanceAdapter:
    """Bounded POSIX adapter. Missing parents are created through dirfds; all opens use O_NOFOLLOW."""

    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root.resolve()
        self.effect_count = 0

    def _validate_relative(self, relative_path: str) -> list[str]:
        if not relative_path or "\x00" in relative_path:
            raise ValueError("repository_path_invalid")
        candidate = Path(relative_path)
        if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
            raise ValueError("repository_path_escape")
        return list(candidate.parts)

    def _open_parent_dir(self, parts: list[str]) -> tuple[int, str]:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        fd = os.open(self.repository_root, flags)
        try:
            for part in parts[:-1]:
                try:
                    child = os.open(part, flags, dir_fd=fd)
                except FileNotFoundError:
                    os.mkdir(part, mode=0o755, dir_fd=fd)
                    child = os.open(part, flags, dir_fd=fd)
                except OSError as exc:
                    if exc.errno in {getattr(os, "ELOOP", 40), getattr(os, "ENOTDIR", 20)}:
                        raise ValueError("repository_path_symlink") from exc
                    raise
                os.close(fd)
                fd = child
            return fd, parts[-1]
        except Exception:
            os.close(fd)
            raise

    def apply(self, relative_path: str, content: str) -> tuple[str, str, str]:
        parts = self._validate_relative(relative_path)
        parent_fd, leaf = self._open_parent_dir(parts)
        flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
        try:
            fd = os.open(leaf, flags, mode=0o644, dir_fd=parent_fd)
            try:
                before = os.pread(fd, os.fstat(fd).st_size, 0)
                before_hash = _hash_bytes(before)
                data = content.encode("utf-8")
                os.ftruncate(fd, 0)
                os.pwrite(fd, data, 0)
                os.fsync(fd)
                after = os.pread(fd, len(data), 0)
                after_hash = _hash_bytes(after)
            finally:
                os.close(fd)
        except OSError as exc:
            if exc.errno in {getattr(os, "ELOOP", 40), getattr(os, "EISDIR", 21)}:
                raise ValueError("repository_path_symlink") from exc
            raise
        finally:
            os.close(parent_fd)
        self.effect_count += 1
        return before_hash, after_hash, after_hash

    def readback_hash(self, relative_path: str) -> str:
        parts = self._validate_relative(relative_path)
        parent_fd, leaf = self._open_parent_dir(parts)
        try:
            fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
            try:
                mode = os.fstat(fd).st_mode
                if not stat.S_ISREG(mode):
                    raise ValueError("repository_path_not_regular")
                return _hash_bytes(os.read(fd, os.fstat(fd).st_size))
            finally:
                os.close(fd)
        finally:
            os.close(parent_fd)


class MissionRuntime:
    def __init__(self, store: MissionRuntimeStore, adapter: RepositoryMaintenanceAdapter,
                 *, binding_validator: Callable[[MissionSnapshot], BindingStatus] | None = None,
                 effect_finalize_hook: Callable[[], None] | None = None) -> None:
        self.store = store
        self.adapter = adapter
        self.binding_validator = binding_validator
        self.effect_finalize_hook = effect_finalize_hook

    def _binding_status(self, snapshot: MissionSnapshot) -> BindingStatus:
        if self.binding_validator is None:
            return BindingStatus.UNKNOWN
        return BindingStatus.VERIFIED if self.binding_validator(snapshot) is BindingStatus.VERIFIED else BindingStatus.HOLD

    def start(self, *, mission_id: str, organization_id: str, ocs_id: str, authority_ref: str,
              state_namespace: str, memory_namespace: str, instance_id: str) -> MissionSnapshot:
        snapshot = MissionSnapshot(mission_id, organization_id, ocs_id, authority_ref,
            state_namespace, memory_namespace, 1, instance_id, MissionStatus.ACTIVE, 0, None, None)
        self.store.create(snapshot)
        return snapshot

    def execute_repository_effect(self, *, mission_id: str, generation: int, instance_id: str,
                                  idempotency_key: str, relative_path: str, content: str) -> RepositoryEffectReceipt:
        snapshot = self._require_current_generation(mission_id, generation=generation, instance_id=instance_id)
        requested_hash = _hash_bytes(content.encode("utf-8"))
        existing = self.store.claim_effect(mission_id, idempotency_key, generation=generation,
                                            path=relative_path, requested_hash=requested_hash)
        if existing is not None:
            status, existing_path, existing_hash = existing
            if status == "PENDING":
                self.reconcile_pending_effects(mission_id)
                status, existing_path, existing_hash = self.store.effect_claim(mission_id, idempotency_key)
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
        receipt = RepositoryEffectReceipt(mission_id, idempotency_key, snapshot.generation,
            relative_path, before_hash, after_hash, False, readback_hash)
        if after_hash != readback_hash:
            raise ValueError("mission_effect_readback_mismatch")
        if self.effect_finalize_hook is not None:
            self.effect_finalize_hook()
        self.store.apply_effect(receipt, {"content_hash": requested_hash, "command": "repository_maintenance"})
        return receipt

    def reconcile_pending_effects(self, mission_id: str) -> int:
        resolved = 0
        for claim in self.store.pending_effects(mission_id):
            try:
                actual = self.adapter.readback_hash(claim["path"])
            except (FileNotFoundError, ValueError):
                actual = None
            if actual == claim["requested_hash"]:
                assert actual is not None
                receipt = RepositoryEffectReceipt(mission_id, claim["idempotency_key"], claim["generation"],
                    claim["path"], claim["before_hash"], actual, False, actual)
                self.store.apply_effect(receipt, {"content_hash": claim["requested_hash"], "reconciled": "true"})
                resolved += 1
            elif actual is None:
                continue
            else:
                self.store.fail_pending(claim["mission_id"], claim["idempotency_key"], "material_drift")
        return resolved

    def checkpoint(self, mission_id: str, *, generation: int, instance_id: str) -> MissionSnapshot:
        snapshot = self._require_current_generation(mission_id, generation=generation, instance_id=instance_id)
        records = self.store.effect_records(mission_id)
        material = {"mission": {"mission_id": snapshot.mission_id, "organization_id": snapshot.organization_id,
            "ocs_id": snapshot.ocs_id, "authority_ref": snapshot.authority_ref,
            "state_namespace": snapshot.state_namespace, "memory_namespace": snapshot.memory_namespace,
            "generation": snapshot.generation, "instance_id": snapshot.instance_id}, "effects": records}
        material_json = json.dumps(material, sort_keys=True, separators=(",", ":"))
        checkpointed = replace(snapshot, status=MissionStatus.CHECKPOINTED,
            checkpoint_version=snapshot.checkpoint_version + 1,
            checkpoint_hash=sha256(material_json.encode()).hexdigest(), checkpoint_material_json=material_json)
        self.store.save(checkpointed, "MISSION_CHECKPOINTED")
        return checkpointed

    def replace_instance(self, mission_id: str, *, old_generation: int, old_instance_id: str,
                         new_instance_id: str) -> MissionSnapshot:
        snapshot = self.store.load(mission_id)
        if snapshot.status is MissionStatus.REPLACEMENT_PENDING:
            return self._recover_replacement(snapshot, new_instance_id)
        if snapshot.status is not MissionStatus.CHECKPOINTED:
            raise ValueError("mission_state_fenced")
        if snapshot.generation != old_generation or snapshot.instance_id != old_instance_id:
            raise ValueError("mission_generation_or_instance_fenced")
        pending = replace(snapshot, status=MissionStatus.REPLACEMENT_PENDING)
        self.store.save(pending, "MISSION_REPLACEMENT_PENDING")
        return self._recover_replacement(pending, new_instance_id)

    def _recover_replacement(self, pending: MissionSnapshot, new_instance_id: str) -> MissionSnapshot:
        if not self.store.checkpoint_material_matches(pending.mission_id):
            raise ValueError("mission_checkpoint_material_mismatch")
        successor = replace(pending, generation=pending.generation + 1,
            instance_id=new_instance_id, status=MissionStatus.RECOVERED, transcript_ref=None)
        self.store.save(successor, "MISSION_RECOVERED_WITHOUT_TRANSCRIPT")
        return successor

    def recover_without_transcript(self, mission_id: str) -> MissionSnapshot:
        snapshot = self.store.load(mission_id)
        if snapshot.transcript_ref is not None:
            raise ValueError("conversation_transcript_must_not_be_recovery_input")
        if snapshot.status is MissionStatus.REPLACEMENT_PENDING:
            return self._recover_replacement(snapshot, snapshot.instance_id)
        if snapshot.checkpoint_hash is None or snapshot.checkpoint_material_json is None:
            raise ValueError("mission_checkpoint_required_for_recovery")
        if sha256(snapshot.checkpoint_material_json.encode()).hexdigest() != snapshot.checkpoint_hash:
            raise ValueError("mission_checkpoint_hash_mismatch")
        if not self.store.checkpoint_material_matches(mission_id):
            raise ValueError("mission_checkpoint_material_mismatch")
        if snapshot.status not in {MissionStatus.RECOVERED, MissionStatus.CLOSED}:
            raise ValueError("mission_recovery_invalid_state")
        return snapshot

    def close(self, mission_id: str, *, generation: int, instance_id: str) -> MissionSnapshot:
        snapshot = self._require_current_generation(mission_id, generation=generation, instance_id=instance_id)
        if snapshot.status is not MissionStatus.RECOVERED:
            raise ValueError("mission_close_invalid_state")
        binding_status = self._binding_status(snapshot)
        if binding_status is not BindingStatus.VERIFIED:
            self.store.save(replace(snapshot, binding_status=BindingStatus.HOLD), "MISSION_CLOSE_HOLD_BINDING_UNKNOWN")
            raise ValueError("mission_binding_validation_unknown")
        closed = replace(snapshot, status=MissionStatus.CLOSED, binding_status=binding_status)
        self.store.save(closed, "MISSION_CLOSED")
        return closed

    def _require_current_generation(self, mission_id: str, *, generation: int, instance_id: str) -> MissionSnapshot:
        snapshot = self.store.load(mission_id)
        if snapshot.status is MissionStatus.CLOSED:
            raise ValueError("mission_closed")
        if snapshot.status not in {MissionStatus.ACTIVE, MissionStatus.RECOVERED}:
            raise ValueError("mission_state_fenced")
        if snapshot.generation != generation or snapshot.instance_id != instance_id:
            raise ValueError("mission_generation_or_instance_fenced")
        return snapshot
