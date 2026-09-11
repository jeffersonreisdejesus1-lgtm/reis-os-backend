from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
import os
import time
import uuid
from dataclasses import asdict, dataclass
from enum import StrEnum
from multiprocessing.connection import Connection
from typing import Any

from app.cognitive_physiology.binding import bind_cognitive_runtime
from app.ocs_instances.contracts import InstanceBinding


class WorkerLifecycle(StrEnum):
    DECLARED = "declared"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    STOPPED = "stopped"
    HOLD = "hold"


@dataclass(frozen=True, slots=True)
class MaterialWorkerSnapshot:
    ocs_id: str
    logical_runtime_id: str
    instance_id: str
    generation: int
    execution_context_id: str
    failure_domain_id: str
    lifecycle_state: WorkerLifecycle
    pid: int
    state_namespace: str
    memory_namespace: str
    authority_ref: str
    profile_hash: str
    monotonic_sequence: int
    checkpoint_hash: str | None = None


@dataclass(frozen=True, slots=True)
class _WorkerCommand:
    kind: str


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _send_snapshot(
    conn: Connection,
    *,
    binding: InstanceBinding,
    logical_runtime_id: str,
    instance_id: str,
    lifecycle: WorkerLifecycle,
    sequence: int,
    checkpoint_hash: str | None = None,
) -> None:
    pid = os.getpid()
    snapshot = MaterialWorkerSnapshot(
        ocs_id=binding.ocs_id,
        logical_runtime_id=logical_runtime_id,
        instance_id=instance_id,
        generation=binding.generation,
        execution_context_id=f"process:{pid}",
        failure_domain_id=f"process:{pid}",
        lifecycle_state=lifecycle,
        pid=pid,
        state_namespace=binding.state_namespace,
        memory_namespace=binding.memory_namespace,
        authority_ref=binding.authority_ref,
        profile_hash=binding.profile_hash,
        monotonic_sequence=sequence,
        checkpoint_hash=checkpoint_hash,
    )
    conn.send(("snapshot", asdict(snapshot)))


def _noesis_worker_main(
    conn: Connection,
    binding: InstanceBinding,
    logical_runtime_id: str,
    instance_id: str,
) -> None:
    sequence = 0
    try:
        if binding.ocs_id != "NÓESIS":
            raise PermissionError("dr1_reference_worker_requires_noesis")
        context = bind_cognitive_runtime(binding)
        sequence += 1
        _send_snapshot(
            conn,
            binding=binding,
            logical_runtime_id=logical_runtime_id,
            instance_id=instance_id,
            lifecycle=WorkerLifecycle.ACTIVE,
            sequence=sequence,
        )

        while True:
            command = conn.recv()
            if not isinstance(command, _WorkerCommand):
                raise RuntimeError("invalid_worker_command")

            if command.kind == "health":
                sequence += 1
                _send_snapshot(
                    conn,
                    binding=binding,
                    logical_runtime_id=logical_runtime_id,
                    instance_id=instance_id,
                    lifecycle=WorkerLifecycle.ACTIVE,
                    sequence=sequence,
                )
                continue

            if command.kind == "checkpoint":
                sequence += 1
                payload = {
                    "ocs_id": binding.ocs_id,
                    "logical_runtime_id": logical_runtime_id,
                    "instance_id": instance_id,
                    "generation": context.runtime.generation,
                    "state_namespace": context.runtime.state_namespace,
                    "memory_namespace": context.runtime.memory_namespace,
                    "workspace_generation": context.runtime.workspace.generation,
                    "world_generation": context.runtime.world.generation,
                    "workspace_candidates": sorted(
                        context.runtime.workspace.candidates.keys()
                    ),
                    "workspace_broadcast_ids": list(
                        context.runtime.workspace.broadcast_ids
                    ),
                    "world_values": context.runtime.world.values,
                }
                _send_snapshot(
                    conn,
                    binding=binding,
                    logical_runtime_id=logical_runtime_id,
                    instance_id=instance_id,
                    lifecycle=WorkerLifecycle.ACTIVE,
                    sequence=sequence,
                    checkpoint_hash=_stable_hash(payload),
                )
                continue

            if command.kind == "stop":
                sequence += 1
                _send_snapshot(
                    conn,
                    binding=binding,
                    logical_runtime_id=logical_runtime_id,
                    instance_id=instance_id,
                    lifecycle=WorkerLifecycle.STOPPED,
                    sequence=sequence,
                )
                return

            raise RuntimeError(f"unsupported_worker_command:{command.kind}")
    except BaseException as exc:
        conn.send(("error", f"{type(exc).__name__}:{exc}"))
        raise
    finally:
        conn.close()


class NoesisMaterialWorker:
    """DR1 reference worker for one materially separate Nóesis process.

    This supervisor materializes exactly one OCS actor. It does not grant
    authority, expose institutional commit operations, or imply multi-OCS
    independence.
    """

    def __init__(
        self,
        binding: InstanceBinding,
        *,
        logical_runtime_id: str = "noesis-primary",
        response_timeout_seconds: float = 5.0,
    ) -> None:
        if binding.ocs_id != "NÓESIS":
            raise PermissionError("dr1_reference_worker_requires_noesis")
        if not logical_runtime_id:
            raise ValueError("logical_runtime_id_required")
        if response_timeout_seconds <= 0:
            raise ValueError("response_timeout_must_be_positive")

        # Validate the existing institutional binding before process creation.
        bind_cognitive_runtime(binding)
        self._binding = binding
        self.logical_runtime_id = logical_runtime_id
        self.instance_id = f"noesis-worker:{uuid.uuid4()}"
        self._timeout = response_timeout_seconds
        self._ctx = mp.get_context("spawn")
        self._parent_conn: Connection | None = None
        self._process: mp.Process | None = None
        self._last_snapshot: MaterialWorkerSnapshot | None = None
        self.lifecycle_state = WorkerLifecycle.DECLARED

    @property
    def pid(self) -> int | None:
        if self._process is None:
            return None
        return self._process.pid

    @property
    def is_alive(self) -> bool:
        return self._process is not None and self._process.is_alive()

    def start(self) -> MaterialWorkerSnapshot:
        if self._process is not None:
            raise RuntimeError("worker_already_started")
        parent_conn, child_conn = self._ctx.Pipe(duplex=True)
        process = self._ctx.Process(
            target=_noesis_worker_main,
            args=(
                child_conn,
                self._binding,
                self.logical_runtime_id,
                self.instance_id,
            ),
            name=f"reis-os-{self.logical_runtime_id}",
            daemon=False,
        )
        self.lifecycle_state = WorkerLifecycle.STARTING
        self._parent_conn = parent_conn
        self._process = process
        process.start()
        child_conn.close()
        snapshot = self._receive_snapshot()
        if snapshot.lifecycle_state is not WorkerLifecycle.ACTIVE:
            self._force_close()
            raise RuntimeError("worker_failed_to_become_active")
        if snapshot.pid == os.getpid():
            self._force_close()
            raise RuntimeError("worker_execution_context_not_distinct")
        self.lifecycle_state = WorkerLifecycle.ACTIVE
        self._last_snapshot = snapshot
        return snapshot

    def health(self) -> MaterialWorkerSnapshot:
        self._require_active()
        assert self._parent_conn is not None
        self._parent_conn.send(_WorkerCommand("health"))
        snapshot = self._receive_snapshot()
        self._last_snapshot = snapshot
        return snapshot

    def checkpoint(self) -> MaterialWorkerSnapshot:
        self._require_active()
        assert self._parent_conn is not None
        self._parent_conn.send(_WorkerCommand("checkpoint"))
        snapshot = self._receive_snapshot()
        if not snapshot.checkpoint_hash:
            raise RuntimeError("worker_checkpoint_hash_missing")
        self._last_snapshot = snapshot
        return snapshot

    def stop(self) -> MaterialWorkerSnapshot:
        self._require_active()
        assert self._parent_conn is not None
        assert self._process is not None
        self.lifecycle_state = WorkerLifecycle.STOPPING
        self._parent_conn.send(_WorkerCommand("stop"))
        snapshot = self._receive_snapshot()
        self._process.join(timeout=self._timeout)
        if self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=self._timeout)
            self.lifecycle_state = WorkerLifecycle.HOLD
            raise RuntimeError("worker_stop_timeout")
        self.lifecycle_state = WorkerLifecycle.STOPPED
        self._last_snapshot = snapshot
        self._parent_conn.close()
        return snapshot

    def _require_active(self) -> None:
        if self.lifecycle_state is not WorkerLifecycle.ACTIVE:
            raise RuntimeError("worker_not_active")
        if not self.is_alive:
            self.lifecycle_state = WorkerLifecycle.HOLD
            raise RuntimeError("worker_process_not_alive")

    def _receive_snapshot(self) -> MaterialWorkerSnapshot:
        assert self._parent_conn is not None
        deadline = time.monotonic() + self._timeout
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not self._parent_conn.poll(remaining):
            self._force_close()
            raise TimeoutError("worker_response_timeout")
        kind, payload = self._parent_conn.recv()
        if kind == "error":
            self._force_close()
            raise RuntimeError(f"worker_child_error:{payload}")
        if kind != "snapshot" or not isinstance(payload, dict):
            self._force_close()
            raise RuntimeError("invalid_worker_response")
        payload["lifecycle_state"] = WorkerLifecycle(payload["lifecycle_state"])
        return MaterialWorkerSnapshot(**payload)

    def _force_close(self) -> None:
        if self._process is not None and self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=self._timeout)
        if self._parent_conn is not None:
            self._parent_conn.close()
        self.lifecycle_state = WorkerLifecycle.HOLD
