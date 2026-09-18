from __future__ import annotations

import multiprocessing as mp
import os
import uuid
from dataclasses import asdict, dataclass
from multiprocessing.connection import Connection
from typing import Any

from app.cognitive_physiology.binding import bind_cognitive_runtime
from app.cognitive_validation.bootstrap_binding import bind_bootstrap_to_cognition
from app.profile_bindings.profiles import PROFILES
from app.ocs_instances.contracts import InstanceBinding

from .worker import MaterialWorkerSnapshot, WorkerLifecycle


DR4_OCS_ORDER = tuple(PROFILES.keys())


@dataclass(frozen=True, slots=True)
class _FleetCommand:
    kind: str


def _snapshot(
    binding: InstanceBinding,
    logical_runtime_id: str,
    instance_id: str,
    lifecycle: WorkerLifecycle,
    sequence: int,
) -> MaterialWorkerSnapshot:
    pid = os.getpid()
    return MaterialWorkerSnapshot(
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
    )


def _worker_main(
    conn: Connection,
    binding: InstanceBinding,
    logical_runtime_id: str,
    instance_id: str,
) -> None:
    sequence = 0
    try:
        context = bind_cognitive_runtime(binding)
        cognitive_binding = bind_bootstrap_to_cognition(binding, ocs_instance_id=instance_id)
        sequence += 1
        conn.send(("snapshot", asdict(_snapshot(binding, logical_runtime_id, instance_id, WorkerLifecycle.ACTIVE, sequence))))
        while True:
            command = conn.recv()
            if not isinstance(command, _FleetCommand):
                raise RuntimeError("invalid_fleet_command")
            if command.kind == "health":
                sequence += 1
                conn.send(("snapshot", asdict(_snapshot(binding, logical_runtime_id, instance_id, WorkerLifecycle.ACTIVE, sequence))))
                continue
            if command.kind == "checkpoint":
                sequence += 1
                conn.send(("checkpoint", {
                    "ocs_id": binding.ocs_id,
                    "instance_id": instance_id,
                    "generation": context.runtime.generation,
                    "state_namespace": binding.state_namespace,
                    "memory_namespace": binding.memory_namespace,
                    "authority_ref": binding.authority_ref,
                    "cognitive_entrypoint": cognitive_binding.cognitive_entrypoint,
                    "brain_path": cognitive_binding.brain_path,
                    "cognitive_path_required": cognitive_binding.cognitive_path_required,
                    "sequence": sequence,
                }))
                continue
            if command.kind == "stop":
                sequence += 1
                conn.send(("snapshot", asdict(_snapshot(binding, logical_runtime_id, instance_id, WorkerLifecycle.STOPPED, sequence))))
                return
            raise RuntimeError(f"unsupported_fleet_command:{command.kind}")
    except BaseException as exc:
        try:
            conn.send(("error", f"{type(exc).__name__}:{exc}"))
        except (BrokenPipeError, EOFError, OSError):
            pass
        raise
    finally:
        conn.close()


class MaterialOCSWorker:
    def __init__(self, binding: InstanceBinding, logical_runtime_id: str, timeout: float = 5.0) -> None:
        bind_cognitive_runtime(binding)
        self.binding = binding
        self.logical_runtime_id = logical_runtime_id
        self.instance_id = f"{logical_runtime_id}:{uuid.uuid4()}"
        bind_bootstrap_to_cognition(binding, ocs_instance_id=self.instance_id)
        self._timeout = timeout
        self._ctx = mp.get_context("spawn")
        self._conn: Connection | None = None
        self._process: mp.Process | None = None
        self.lifecycle_state = WorkerLifecycle.DECLARED

    @property
    def is_alive(self) -> bool:
        return self._process is not None and self._process.is_alive()

    def start(self) -> MaterialWorkerSnapshot:
        parent, child = self._ctx.Pipe(duplex=True)
        process = self._ctx.Process(
            target=_worker_main,
            args=(child, self.binding, self.logical_runtime_id, self.instance_id),
            daemon=False,
        )
        self._conn = parent
        self._process = process
        self.lifecycle_state = WorkerLifecycle.STARTING
        process.start()
        child.close()
        snapshot = self._recv("snapshot", MaterialWorkerSnapshot)
        if snapshot.pid == os.getpid():
            self.crash()
            raise RuntimeError("fleet_execution_context_not_distinct")
        self.lifecycle_state = WorkerLifecycle.ACTIVE
        return snapshot

    def health(self) -> MaterialWorkerSnapshot:
        self._require_active()
        assert self._conn is not None
        self._conn.send(_FleetCommand("health"))
        return self._recv("snapshot", MaterialWorkerSnapshot)

    def checkpoint(self) -> dict[str, Any]:
        self._require_active()
        assert self._conn is not None
        self._conn.send(_FleetCommand("checkpoint"))
        return self._recv_raw("checkpoint")

    def stop(self) -> None:
        if not self.is_alive:
            return
        assert self._conn is not None and self._process is not None
        self._conn.send(_FleetCommand("stop"))
        self._recv("snapshot", MaterialWorkerSnapshot)
        self._process.join(timeout=self._timeout)
        if self._process.is_alive():
            self.crash()
            raise RuntimeError("fleet_worker_stop_timeout")
        self.lifecycle_state = WorkerLifecycle.STOPPED
        self._conn.close()

    def crash(self) -> None:
        if self._process is not None and self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=self._timeout)
        if self._conn is not None:
            self._conn.close()
        self.lifecycle_state = WorkerLifecycle.HOLD

    def _require_active(self) -> None:
        if self.lifecycle_state is not WorkerLifecycle.ACTIVE or not self.is_alive:
            self.lifecycle_state = WorkerLifecycle.HOLD
            raise RuntimeError("fleet_worker_not_active")

    def _recv_raw(self, expected: str) -> dict[str, Any]:
        assert self._conn is not None
        if not self._conn.poll(self._timeout):
            self.crash()
            raise TimeoutError("fleet_worker_response_timeout")
        kind, payload = self._conn.recv()
        if kind == "error":
            self.crash()
            raise RuntimeError(f"fleet_worker_child_error:{payload}")
        if kind != expected or not isinstance(payload, dict):
            self.crash()
            raise RuntimeError("invalid_fleet_worker_response")
        return payload

    def _recv(self, expected: str, model: type[Any]) -> Any:
        payload = self._recv_raw(expected)
        if model is MaterialWorkerSnapshot:
            payload["lifecycle_state"] = WorkerLifecycle(payload["lifecycle_state"])
        return model(**payload)


class ElevenOCSFleet:
    def __init__(self, bindings: dict[str, InstanceBinding]) -> None:
        if tuple(bindings.keys()) != DR4_OCS_ORDER:
            raise PermissionError("dr4_requires_exact_canonical_11_ocs_order")
        if len(bindings) != 11:
            raise PermissionError("dr4_requires_exactly_eleven_bindings")
        self._bindings = bindings
        self._workers: dict[str, MaterialOCSWorker] = {}
        self._snapshots: dict[str, MaterialWorkerSnapshot] = {}

    def start_all(self) -> dict[str, MaterialWorkerSnapshot]:
        try:
            for ocs_id in DR4_OCS_ORDER:
                logical_runtime_id = f"{ocs_id.casefold()}-runtime-primary"
                worker = MaterialOCSWorker(self._bindings[ocs_id], logical_runtime_id)
                self._workers[ocs_id] = worker
                self._snapshots[ocs_id] = worker.start()
            self._validate_material_distinctness()
            return dict(self._snapshots)
        except BaseException:
            self.stop_all()
            raise

    def _validate_material_distinctness(self) -> None:
        snapshots = tuple(self._snapshots.values())
        invariants = {
            "instance_id": {s.instance_id for s in snapshots},
            "execution_context_id": {s.execution_context_id for s in snapshots},
            "failure_domain_id": {s.failure_domain_id for s in snapshots},
            "state_namespace": {s.state_namespace for s in snapshots},
            "memory_namespace": {s.memory_namespace for s in snapshots},
        }
        for name, values in invariants.items():
            if len(values) != 11:
                raise RuntimeError(f"dr4_distinctness_failed:{name}")
        if {s.ocs_id for s in snapshots} != set(DR4_OCS_ORDER):
            raise RuntimeError("dr4_canonical_ocs_coverage_failed")
        if not all(s.lifecycle_state is WorkerLifecycle.ACTIVE for s in snapshots):
            raise RuntimeError("dr4_all_lifecycles_must_be_active")

    def health_all(self) -> dict[str, MaterialWorkerSnapshot]:
        return {ocs_id: worker.health() for ocs_id, worker in self._workers.items()}

    def checkpoint_all(self) -> dict[str, dict[str, Any]]:
        return {ocs_id: worker.checkpoint() for ocs_id, worker in self._workers.items()}

    def kill_one(self, ocs_id: str) -> None:
        self._workers[ocs_id].crash()

    def peer_health_after_kill(self, ocs_id: str) -> dict[str, MaterialWorkerSnapshot]:
        return {
            peer: worker.health()
            for peer, worker in self._workers.items()
            if peer != ocs_id
        }

    def stop_all(self) -> None:
        for worker in self._workers.values():
            worker.stop()
