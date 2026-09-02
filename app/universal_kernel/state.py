from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import time

from .contracts import StateCommitRecord
from .trace import TraceLedger


@dataclass(frozen=True)
class StateSnapshot:
    namespace: str
    version: int
    predecessor_version: int | None
    payload: dict[str, str]
    content_hash: str
    verified: bool


class StateConflictError(RuntimeError):
    pass


class InMemoryStateManager:
    def __init__(self, trace: TraceLedger) -> None:
        self._trace = trace
        self._streams: dict[str, list[StateSnapshot]] = {}
        self._checkpoints: dict[str, StateSnapshot] = {}

    def read_state(self, namespace: str) -> StateSnapshot | None:
        stream = self._streams.get(namespace, [])
        return stream[-1] if stream else None

    def commit_write(
        self,
        *,
        namespace: str,
        payload: dict[str, str],
        expected_predecessor: int | None,
        authority_ref: str,
        action_id: str,
        trace_ref: str,
    ) -> StateCommitRecord:
        current = self.read_state(namespace)
        current_version = current.version if current else None
        if current_version != expected_predecessor:
            raise StateConflictError("predecessor mismatch")
        if current is not None and current.predecessor_version is None and current.version != 1:
            raise StateConflictError("non-genesis state requires predecessor")

        version = 1 if current is None else current.version + 1
        content_hash = self._hash_payload(payload)
        snapshot = StateSnapshot(
            namespace=namespace,
            version=version,
            predecessor_version=current_version,
            payload=dict(payload),
            content_hash=content_hash,
            verified=False,
        )
        stream = self._streams.setdefault(namespace, [])
        stream.append(snapshot)

        readback = self.read_state(namespace)
        if readback is None or readback.content_hash != content_hash:
            stream.pop()
            raise RuntimeError("readback verification failed")

        verified = StateSnapshot(
            namespace=snapshot.namespace,
            version=snapshot.version,
            predecessor_version=snapshot.predecessor_version,
            payload=snapshot.payload,
            content_hash=snapshot.content_hash,
            verified=True,
        )
        stream[-1] = verified
        event = self._trace.append(
            "state_commit",
            {
                "namespace": namespace,
                "version": str(version),
                "predecessor": str(current_version),
                "action_id": action_id,
                "trace_ref": trace_ref,
            },
        )
        return StateCommitRecord(
            state_namespace=namespace,
            version=version,
            predecessor_version=current_version,
            content_hash=content_hash,
            write_set_ref=f"write://{namespace}/{version}",
            authority_ref=authority_ref,
            action_id=action_id,
            readback_hash=verified.content_hash,
            committed_at=int(time.time()),
            checkpoint_ref=None,
            trace_ref=event.event_hash,
        )

    def checkpoint(self, namespace: str) -> str:
        current = self.read_state(namespace)
        if current is None or not current.verified:
            raise RuntimeError("verified state required")
        ref = f"checkpoint://{namespace}/{current.version}/{current.content_hash}"
        self._checkpoints[ref] = current
        self._trace.append("state_checkpoint", {"checkpoint_ref": ref})
        return ref

    def rollback_to_verified(self, checkpoint_ref: str) -> StateSnapshot:
        checkpoint = self._checkpoints.get(checkpoint_ref)
        if checkpoint is None or not checkpoint.verified:
            raise RuntimeError("verified checkpoint required")
        stream = self._streams.setdefault(checkpoint.namespace, [])
        restored = StateSnapshot(
            namespace=checkpoint.namespace,
            version=checkpoint.version,
            predecessor_version=checkpoint.predecessor_version,
            payload=dict(checkpoint.payload),
            content_hash=checkpoint.content_hash,
            verified=True,
        )
        stream.append(restored)
        readback = self.read_state(checkpoint.namespace)
        if readback is None or readback.content_hash != checkpoint.content_hash:
            raise RuntimeError("recovery readback mismatch")
        self._trace.append(
            "state_recovery",
            {
                "checkpoint_ref": checkpoint_ref,
                "restored_hash": restored.content_hash,
            },
        )
        return restored

    @staticmethod
    def _hash_payload(payload: dict[str, str]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()
