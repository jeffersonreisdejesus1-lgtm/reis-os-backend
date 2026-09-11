from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
import os
import time
import uuid
from dataclasses import asdict, dataclass, replace
from multiprocessing.connection import Connection
from typing import Any

from app.cognitive_physiology.binding import bind_cognitive_runtime
from app.ocs_instances.contracts import InstanceBinding

from .worker import MaterialWorkerSnapshot, WorkerLifecycle


@dataclass(frozen=True, slots=True)
class PairMessage:
    message_id: str
    mission_id: str
    source_ocs: str
    source_instance_id: str
    source_generation: int
    target_ocs: str
    target_expected_generation: int
    payload: dict[str, Any]
    payload_hash: str
    causation_id: str

    @classmethod
    def build(
        cls,
        *,
        mission_id: str,
        source: MaterialWorkerSnapshot,
        target: MaterialWorkerSnapshot,
        payload: dict[str, Any],
        causation_id: str,
    ) -> "PairMessage":
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        return cls(
            message_id=f"dr2-msg:{uuid.uuid4()}",
            mission_id=mission_id,
            source_ocs=source.ocs_id,
            source_instance_id=source.instance_id,
            source_generation=source.generation,
            target_ocs=target.ocs_id,
            target_expected_generation=target.generation,
            payload=payload,
            payload_hash=hashlib.sha256(encoded).hexdigest(),
            causation_id=causation_id,
        )


@dataclass(frozen=True, slots=True)
class HandoffReceipt:
    message_id: str
    source_ocs: str
    target_ocs: str
    target_instance_id: str
    target_generation: int
    payload_hash: str
    accepted: bool
    monotonic_sequence: int


@dataclass(frozen=True, slots=True)
class _Command:
    kind: str
    payload: Any = None


def _snapshot(
    *,
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
        sequence += 1
        conn.send(("snapshot", asdict(_snapshot(
            binding=binding,
            logical_runtime_id=logical_runtime_id,
            instance_id=instance_id,
            lifecycle=WorkerLifecycle.ACTIVE,
            sequence=sequence,
        ))))

        while True:
            command = conn.recv()
            if not isinstance(command, _Command):
                raise RuntimeError("invalid_pair_worker_command")
            if command.kind == "health":
                sequence += 1
                conn.send(("snapshot", asdict(_snapshot(
                    binding=binding,
                    logical_runtime_id=logical_runtime_id,
                    instance_id=instance_id,
                    lifecycle=WorkerLifecycle.ACTIVE,
                    sequence=sequence,
                ))))
                continue
            if command.kind == "handoff":
                message = command.payload
                if not isinstance(message, PairMessage):
                    raise RuntimeError("invalid_pair_message")
                if message.target_ocs != binding.ocs_id:
                    raise PermissionError("cross_target_delivery_denied")
                if message.target_expected_generation != binding.generation:
                    raise PermissionError("stale_target_generation")
                encoded = json.dumps(
                    message.payload,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode()
                if hashlib.sha256(encoded).hexdigest() != message.payload_hash:
                    raise PermissionError("payload_hash_mismatch")
                sequence += 1
                receipt = HandoffReceipt(
                    message_id=message.message_id,
                    source_ocs=message.source_ocs,
                    target_ocs=binding.ocs_id,
                    target_instance_id=instance_id,
                    target_generation=context.runtime.generation,
                    payload_hash=message.payload_hash,
                    accepted=True,
                    monotonic_sequence=sequence,
                )
                conn.send(("receipt", asdict(receipt)))
                continue
            if command.kind == "stop":
                sequence += 1
                conn.send(("snapshot", asdict(_snapshot(
                    binding=binding,
                    logical_runtime_id=logical_runtime_id,
                    instance_id=instance_id,
                    lifecycle=WorkerLifecycle.STOPPED,
                    sequence=sequence,
                ))))
                return
            raise RuntimeError(f"unsupported_pair_worker_command:{command.kind}")
    except BaseException as exc:
        try:
            conn.send(("error", f"{type(exc).__name__}:{exc}"))
        except (BrokenPipeError, EOFError, OSError):
            pass
        raise
    finally:
        conn.close()


class MaterialOCSWorker:
    def __init__(
        self,
        binding: InstanceBinding,
        *,
        logical_runtime_id: str,
        response_timeout_seconds: float = 5.0,
    ) -> None:
        bind_cognitive_runtime(binding)
        self.binding = binding
        self.logical_runtime_id = logical_runtime_id
        self.instance_id = f"{binding.ocs_id.lower()}-worker:{uuid.uuid4()}"
        self._timeout = response_timeout_seconds
        self._ctx = mp.get_context("spawn")
        self._parent_conn: Connection | None = None
        self._process: mp.Process | None = None
        self.lifecycle_state = WorkerLifecycle.DECLARED

    @property
    def is_alive(self) -> bool:
        return self._process is not None and self._process.is_alive()

    def start(self) -> MaterialWorkerSnapshot:
        if self._process is not None:
            raise RuntimeError("worker_already_started")
        parent_conn, child_conn = self._ctx.Pipe(duplex=True)
        process = self._ctx.Process(
            target=_worker_main,
            args=(child_conn, self.binding, self.logical_runtime_id, self.instance_id),
            name=f"reis-os-{self.logical_runtime_id}",
            daemon=False,
        )
        self._parent_conn = parent_conn
        self._process = process
        self.lifecycle_state = WorkerLifecycle.STARTING
        process.start()
        child_conn.close()
        snapshot = self._receive("snapshot", MaterialWorkerSnapshot)
        if snapshot.pid == os.getpid():
            self.crash()
            raise RuntimeError("worker_execution_context_not_distinct")
        self.lifecycle_state = WorkerLifecycle.ACTIVE
        return snapshot

    def health(self) -> MaterialWorkerSnapshot:
        self._require_active()
        assert self._parent_conn is not None
        self._parent_conn.send(_Command("health"))
        return self._receive("snapshot", MaterialWorkerSnapshot)

    def accept_handoff(self, message: PairMessage) -> HandoffReceipt:
        self._require_active()
        assert self._parent_conn is not None
        self._parent_conn.send(_Command("handoff", message))
        return self._receive("receipt", HandoffReceipt)

    def stop(self) -> MaterialWorkerSnapshot:
        self._require_active()
        assert self._parent_conn is not None and self._process is not None
        self._parent_conn.send(_Command("stop"))
        snapshot = self._receive("snapshot", MaterialWorkerSnapshot)
        self._process.join(timeout=self._timeout)
        if self._process.is_alive():
            self.crash()
            raise RuntimeError("worker_stop_timeout")
        self.lifecycle_state = WorkerLifecycle.STOPPED
        self._parent_conn.close()
        return snapshot

    def crash(self) -> None:
        if self._process is not None and self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=self._timeout)
        if self._parent_conn is not None:
            self._parent_conn.close()
        self.lifecycle_state = WorkerLifecycle.HOLD

    def _require_active(self) -> None:
        if self.lifecycle_state is not WorkerLifecycle.ACTIVE or not self.is_alive:
            self.lifecycle_state = WorkerLifecycle.HOLD
            raise RuntimeError("worker_not_active")

    def _receive(self, expected_kind: str, model: type[Any]) -> Any:
        assert self._parent_conn is not None
        if not self._parent_conn.poll(self._timeout):
            self.crash()
            raise TimeoutError("worker_response_timeout")
        kind, payload = self._parent_conn.recv()
        if kind == "error":
            self.crash()
            raise RuntimeError(f"worker_child_error:{payload}")
        if kind != expected_kind or not isinstance(payload, dict):
            self.crash()
            raise RuntimeError("invalid_worker_response")
        if model is MaterialWorkerSnapshot:
            payload["lifecycle_state"] = WorkerLifecycle(payload["lifecycle_state"])
        return model(**payload)


class NoesisDedalaPairRuntime:
    ALLOWED = frozenset({"NÓESIS", "DÉDALA"})

    def __init__(self, noesis_binding: InstanceBinding, dedala_binding: InstanceBinding) -> None:
        if {noesis_binding.ocs_id, dedala_binding.ocs_id} != self.ALLOWED:
            raise PermissionError("dr2_requires_noesis_and_dedala")
        self._bindings = {
            "NÓESIS": noesis_binding,
            "DÉDALA": dedala_binding,
        }
        self._workers: dict[str, MaterialOCSWorker] = {}
        self._snapshots: dict[str, MaterialWorkerSnapshot] = {}

    def start(self) -> dict[str, MaterialWorkerSnapshot]:
        for ocs_id, logical_id in (("NÓESIS", "noesis-primary"), ("DÉDALA", "dedala-primary")):
            worker = MaterialOCSWorker(self._bindings[ocs_id], logical_runtime_id=logical_id)
            self._workers[ocs_id] = worker
            self._snapshots[ocs_id] = worker.start()
        if self._snapshots["NÓESIS"].pid == self._snapshots["DÉDALA"].pid:
            self.stop_all()
            raise RuntimeError("pair_execution_contexts_must_be_distinct")
        return dict(self._snapshots)

    def handoff(self, *, source_ocs: str, target_ocs: str, payload: dict[str, Any], causation_id: str) -> HandoffReceipt:
        if source_ocs == target_ocs or {source_ocs, target_ocs} != self.ALLOWED:
            raise PermissionError("pair_handoff_route_denied")
        source = self._workers[source_ocs].health()
        target = self._workers[target_ocs].health()
        message = PairMessage.build(
            mission_id=source_ocs.lower() + "-to-" + target_ocs.lower(),
            source=source,
            target=target,
            payload=payload,
            causation_id=causation_id,
        )
        receipt = self._workers[target_ocs].accept_handoff(message)
        if receipt.payload_hash != message.payload_hash:
            raise RuntimeError("handoff_receipt_hash_mismatch")
        return receipt

    def restart(self, ocs_id: str) -> MaterialWorkerSnapshot:
        if ocs_id not in self.ALLOWED:
            raise KeyError(ocs_id)
        other = "DÉDALA" if ocs_id == "NÓESIS" else "NÓESIS"
        if not self._workers[other].is_alive:
            raise RuntimeError("peer_must_remain_alive_during_restart")
        old = self._workers[ocs_id]
        old.crash()
        old_binding = self._bindings[ocs_id]
        new_binding = replace(
            old_binding,
            binding_id=f"{old_binding.binding_id}:g{old_binding.generation + 1}",
            generation=old_binding.generation + 1,
            predecessor_binding_id=old_binding.binding_id,
            version=old_binding.version + 1,
            updated_at=max(old_binding.updated_at + 1.0, time.time()),
        )
        self._bindings[ocs_id] = new_binding
        logical_id = "noesis-primary" if ocs_id == "NÓESIS" else "dedala-primary"
        replacement = MaterialOCSWorker(new_binding, logical_runtime_id=logical_id)
        self._workers[ocs_id] = replacement
        snapshot = replacement.start()
        self._snapshots[ocs_id] = snapshot
        if not self._workers[other].is_alive:
            raise RuntimeError("peer_died_during_independent_restart")
        return snapshot

    def health(self, ocs_id: str) -> MaterialWorkerSnapshot:
        return self._workers[ocs_id].health()

    def stop_all(self) -> None:
        for worker in self._workers.values():
            if worker.lifecycle_state is WorkerLifecycle.ACTIVE and worker.is_alive:
                worker.stop()
            elif worker.is_alive:
                worker.crash()
