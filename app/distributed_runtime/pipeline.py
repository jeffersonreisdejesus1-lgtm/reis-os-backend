from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
import os
import uuid
from dataclasses import asdict, dataclass
from multiprocessing.connection import Connection
from typing import Any

from app.cognitive_physiology.binding import bind_cognitive_runtime
from app.ocs_instances.contracts import InstanceBinding

from .worker import MaterialWorkerSnapshot, WorkerLifecycle


@dataclass(frozen=True, slots=True)
class PipelineEnvelope:
    message_id: str
    mission_id: str
    source_ocs: str
    source_instance_id: str
    source_generation: int
    target_ocs: str
    target_expected_generation: int
    input_payload_hash: str
    payload: dict[str, Any]
    payload_hash: str
    causation_id: str
    trace_id: str


@dataclass(frozen=True, slots=True)
class PipelineReceipt:
    message_id: str
    target_ocs: str
    target_instance_id: str
    target_generation: int
    input_payload_hash: str
    output_payload_hash: str
    output_payload: dict[str, Any]
    transformation: str
    causation_id: str
    trace_id: str
    accepted: bool


@dataclass(frozen=True, slots=True)
class _PipelineCommand:
    kind: str
    envelope: PipelineEnvelope | None = None


def _hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


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


def _transform(ocs_id: str, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if ocs_id == "NÓESIS":
        return "mission_framing", {**payload, "noesis_framed": True}
    if ocs_id == "DÉDALA":
        return "architectural_review", {**payload, "dedala_reviewed": True}
    if ocs_id == "ÁGORA":
        return "material_qualification", {**payload, "agora_qualified": True}
    raise PermissionError("dr3_pipeline_ocs_not_allowed")


def _worker_main(
    conn: Connection,
    binding: InstanceBinding,
    logical_runtime_id: str,
    instance_id: str,
) -> None:
    sequence = 0
    try:
        if binding.ocs_id not in {"NÓESIS", "DÉDALA", "ÁGORA"}:
            raise PermissionError("dr3_pipeline_ocs_not_allowed")
        context = bind_cognitive_runtime(binding)
        sequence += 1
        conn.send(("snapshot", asdict(_snapshot(binding, logical_runtime_id, instance_id, WorkerLifecycle.ACTIVE, sequence))))

        while True:
            command = conn.recv()
            if not isinstance(command, _PipelineCommand):
                raise RuntimeError("invalid_pipeline_command")
            if command.kind == "health":
                sequence += 1
                conn.send(("snapshot", asdict(_snapshot(binding, logical_runtime_id, instance_id, WorkerLifecycle.ACTIVE, sequence))))
                continue
            if command.kind == "process":
                envelope = command.envelope
                if envelope is None:
                    raise RuntimeError("pipeline_envelope_required")
                if envelope.target_ocs != binding.ocs_id:
                    raise PermissionError("pipeline_target_mismatch")
                if envelope.target_expected_generation != binding.generation:
                    raise PermissionError("pipeline_stale_generation")
                if _hash_payload(envelope.payload) != envelope.payload_hash:
                    raise PermissionError("pipeline_payload_hash_mismatch")
                transformation, output = _transform(binding.ocs_id, envelope.payload)
                sequence += 1
                conn.send(("receipt", asdict(PipelineReceipt(
                    message_id=envelope.message_id,
                    target_ocs=binding.ocs_id,
                    target_instance_id=instance_id,
                    target_generation=context.runtime.generation,
                    input_payload_hash=envelope.payload_hash,
                    output_payload_hash=_hash_payload(output),
                    output_payload=output,
                    transformation=transformation,
                    causation_id=envelope.causation_id,
                    trace_id=envelope.trace_id,
                    accepted=True,
                ))))
                continue
            if command.kind == "stop":
                sequence += 1
                conn.send(("snapshot", asdict(_snapshot(binding, logical_runtime_id, instance_id, WorkerLifecycle.STOPPED, sequence))))
                return
            raise RuntimeError(f"unsupported_pipeline_command:{command.kind}")
    except BaseException as exc:
        try:
            conn.send(("error", f"{type(exc).__name__}:{exc}"))
        except (BrokenPipeError, EOFError, OSError):
            pass
        raise
    finally:
        conn.close()


class PipelineWorker:
    def __init__(self, binding: InstanceBinding, logical_runtime_id: str, timeout: float = 5.0) -> None:
        bind_cognitive_runtime(binding)
        if binding.ocs_id not in {"NÓESIS", "DÉDALA", "ÁGORA"}:
            raise PermissionError("dr3_pipeline_ocs_not_allowed")
        self.binding = binding
        self.logical_runtime_id = logical_runtime_id
        self.instance_id = f"{logical_runtime_id}:{uuid.uuid4()}"
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
        process = self._ctx.Process(target=_worker_main, args=(child, self.binding, self.logical_runtime_id, self.instance_id), daemon=False)
        self._conn = parent
        self._process = process
        self.lifecycle_state = WorkerLifecycle.STARTING
        process.start()
        child.close()
        snapshot = self._recv("snapshot", MaterialWorkerSnapshot)
        if snapshot.pid == os.getpid():
            self.crash()
            raise RuntimeError("pipeline_execution_context_not_distinct")
        self.lifecycle_state = WorkerLifecycle.ACTIVE
        return snapshot

    def health(self) -> MaterialWorkerSnapshot:
        self._require_active()
        assert self._conn is not None
        self._conn.send(_PipelineCommand("health"))
        return self._recv("snapshot", MaterialWorkerSnapshot)

    def process(self, envelope: PipelineEnvelope) -> PipelineReceipt:
        self._require_active()
        assert self._conn is not None
        self._conn.send(_PipelineCommand("process", envelope))
        return self._recv("receipt", PipelineReceipt)

    def stop(self) -> None:
        if not self.is_alive:
            return
        assert self._conn is not None and self._process is not None
        self._conn.send(_PipelineCommand("stop"))
        self._recv("snapshot", MaterialWorkerSnapshot)
        self._process.join(timeout=self._timeout)
        if self._process.is_alive():
            self.crash()
            raise RuntimeError("pipeline_worker_stop_timeout")
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
            raise RuntimeError("pipeline_worker_not_active")

    def _recv(self, expected: str, model: type[Any]) -> Any:
        assert self._conn is not None
        if not self._conn.poll(self._timeout):
            self.crash()
            raise TimeoutError("pipeline_worker_response_timeout")
        kind, payload = self._conn.recv()
        if kind == "error":
            self.crash()
            raise RuntimeError(f"pipeline_worker_child_error:{payload}")
        if kind != expected or not isinstance(payload, dict):
            self.crash()
            raise RuntimeError("invalid_pipeline_worker_response")
        if model is MaterialWorkerSnapshot:
            payload["lifecycle_state"] = WorkerLifecycle(payload["lifecycle_state"])
        return model(**payload)


class NoesisDedalaAgoraPipeline:
    ORDER = ("NÓESIS", "DÉDALA", "ÁGORA")

    def __init__(self, bindings: dict[str, InstanceBinding]) -> None:
        if set(bindings) != set(self.ORDER):
            raise PermissionError("dr3_requires_noesis_dedala_agora")
        self._bindings = bindings
        self._workers: dict[str, PipelineWorker] = {}
        self._snapshots: dict[str, MaterialWorkerSnapshot] = {}

    def start(self) -> dict[str, MaterialWorkerSnapshot]:
        for ocs_id in self.ORDER:
            logical_id = {"NÓESIS": "noesis-primary", "DÉDALA": "dedala-support", "ÁGORA": "agora-support"}[ocs_id]
            worker = PipelineWorker(self._bindings[ocs_id], logical_id)
            self._workers[ocs_id] = worker
            self._snapshots[ocs_id] = worker.start()
        pids = {snapshot.pid for snapshot in self._snapshots.values()}
        if len(pids) != 3:
            self.stop_all()
            raise RuntimeError("dr3_requires_three_distinct_execution_contexts")
        return dict(self._snapshots)

    def execute(self, initial_payload: dict[str, Any], mission_id: str = "mission:dr3") -> list[PipelineReceipt]:
        trace_id = f"dr3-trace:{uuid.uuid4()}"
        payload = dict(initial_payload)
        receipts: list[PipelineReceipt] = []
        previous_message_id = "root"
        for ocs_id in self.ORDER:
            target = self._workers[ocs_id].health()
            envelope = PipelineEnvelope(
                message_id=f"dr3-msg:{uuid.uuid4()}",
                mission_id=mission_id,
                source_ocs="FOUNDER_INPUT" if not receipts else receipts[-1].target_ocs,
                source_instance_id="external" if not receipts else receipts[-1].target_instance_id,
                source_generation=0 if not receipts else receipts[-1].target_generation,
                target_ocs=ocs_id,
                target_expected_generation=target.generation,
                input_payload_hash=_hash_payload(payload),
                payload=payload,
                payload_hash=_hash_payload(payload),
                causation_id=previous_message_id,
                trace_id=trace_id,
            )
            receipt = self._workers[ocs_id].process(envelope)
            if receipt.input_payload_hash != envelope.payload_hash:
                raise RuntimeError("dr3_input_causal_hash_break")
            if _hash_payload(receipt.output_payload) != receipt.output_payload_hash:
                raise RuntimeError("dr3_output_hash_break")
            receipts.append(receipt)
            payload = receipt.output_payload
            previous_message_id = envelope.message_id
        return receipts

    def stop_all(self) -> None:
        for worker in self._workers.values():
            worker.stop()
