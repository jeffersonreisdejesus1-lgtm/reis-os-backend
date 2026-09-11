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
from app.profile_bindings.profiles import PROFILES

from .worker import MaterialWorkerSnapshot, WorkerLifecycle


DR5A_ORDER = (
    "NÓESIS",
    "MÊTIS",
    "DÉDALA",
    "ÍRIS",
    "LYRA",
    "SOFIA",
    "ÁGORA",
    "AURI",
    "SYNERGEIA",
    "TÊMIS",
    "SÝNESIS",
)

SPECIALTY_CONTRIBUTION = {
    "NÓESIS": ("orchestration_frame", "mission_orchestration_framed"),
    "MÊTIS": ("strategic_hypothesis", "strategic_hypothesis_added"),
    "DÉDALA": ("architecture_review", "architecture_risk_reviewed"),
    "ÍRIS": ("human_interface_review", "human_interface_reviewed"),
    "LYRA": ("language_identity_review", "language_identity_reviewed"),
    "SOFIA": ("implementation_shape", "implementation_shape_defined"),
    "ÁGORA": ("technical_qualification", "technical_qualification_added"),
    "AURI": ("record_continuity", "record_continuity_added"),
    "SYNERGEIA": ("integration_coordination", "integration_coordination_added"),
    "TÊMIS": ("android_play_stewardship", "android_play_stewardship_added"),
    "SÝNESIS": ("independent_assurance", "independent_assurance_added"),
}


@dataclass(frozen=True, slots=True)
class CausalMissionEnvelope:
    message_id: str
    mission_id: str
    source_ocs: str
    source_instance_id: str
    source_generation: int
    target_ocs: str
    target_expected_generation: int
    payload: dict[str, Any]
    payload_hash: str
    predecessor_output_hash: str
    causation_id: str
    correlation_id: str
    trace_id: str


@dataclass(frozen=True, slots=True)
class CausalMissionReceipt:
    message_id: str
    mission_id: str
    target_ocs: str
    target_instance_id: str
    target_generation: int
    declared_specialty: str
    transformation: str
    contribution_key: str
    input_payload_hash: str
    output_payload_hash: str
    output_payload: dict[str, Any]
    causation_id: str
    correlation_id: str
    trace_id: str
    accepted: bool


@dataclass(frozen=True, slots=True)
class _MissionCommand:
    kind: str
    envelope: CausalMissionEnvelope | None = None


def _hash_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


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


def _transform(ocs_id: str, payload: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    if ocs_id not in SPECIALTY_CONTRIBUTION:
        raise PermissionError("dr5a_unknown_ocs")
    transformation, contribution_key = SPECIALTY_CONTRIBUTION[ocs_id]
    contributions = dict(payload.get("contributions", {}))
    if ocs_id in contributions:
        raise PermissionError("dr5a_duplicate_ocs_contribution")
    contributions[ocs_id] = {
        "transformation": transformation,
        "specialty": PROFILES[ocs_id].specialty,
        "result": contribution_key,
    }
    output = {
        **payload,
        "contributions": contributions,
        "last_contributor": ocs_id,
    }
    return transformation, contribution_key, output


def mission_has_all_specialty_contributions(payload: dict[str, Any]) -> bool:
    contributions = payload.get("contributions")
    if not isinstance(contributions, dict):
        return False
    if set(contributions) != set(DR5A_ORDER):
        return False
    for ocs_id in DR5A_ORDER:
        contribution = contributions.get(ocs_id)
        if not isinstance(contribution, dict):
            return False
        if contribution.get("specialty") != PROFILES[ocs_id].specialty:
            return False
        if contribution.get("result") != SPECIALTY_CONTRIBUTION[ocs_id][1]:
            return False
    return True


def _worker_main(
    conn: Connection,
    binding: InstanceBinding,
    logical_runtime_id: str,
    instance_id: str,
) -> None:
    sequence = 0
    try:
        if binding.ocs_id not in DR5A_ORDER:
            raise PermissionError("dr5a_worker_not_in_canonical_order")
        context = bind_cognitive_runtime(binding)
        sequence += 1
        conn.send((
            "snapshot",
            asdict(_snapshot(
                binding,
                logical_runtime_id,
                instance_id,
                WorkerLifecycle.ACTIVE,
                sequence,
            )),
        ))

        while True:
            command = conn.recv()
            if not isinstance(command, _MissionCommand):
                raise RuntimeError("invalid_dr5a_command")

            if command.kind == "health":
                sequence += 1
                conn.send((
                    "snapshot",
                    asdict(_snapshot(
                        binding,
                        logical_runtime_id,
                        instance_id,
                        WorkerLifecycle.ACTIVE,
                        sequence,
                    )),
                ))
                continue

            if command.kind == "process":
                envelope = command.envelope
                if envelope is None:
                    raise RuntimeError("dr5a_envelope_required")
                if envelope.target_ocs != binding.ocs_id:
                    raise PermissionError("dr5a_target_mismatch")
                if envelope.target_expected_generation != binding.generation:
                    raise PermissionError("dr5a_stale_generation")
                if _hash_payload(envelope.payload) != envelope.payload_hash:
                    raise PermissionError("dr5a_payload_hash_mismatch")
                if envelope.predecessor_output_hash != envelope.payload_hash:
                    raise PermissionError("dr5a_predecessor_hash_break")

                transformation, contribution_key, output = _transform(
                    binding.ocs_id,
                    envelope.payload,
                )
                sequence += 1
                conn.send((
                    "receipt",
                    asdict(CausalMissionReceipt(
                        message_id=envelope.message_id,
                        mission_id=envelope.mission_id,
                        target_ocs=binding.ocs_id,
                        target_instance_id=instance_id,
                        target_generation=context.runtime.generation,
                        declared_specialty=PROFILES[binding.ocs_id].specialty,
                        transformation=transformation,
                        contribution_key=contribution_key,
                        input_payload_hash=envelope.payload_hash,
                        output_payload_hash=_hash_payload(output),
                        output_payload=output,
                        causation_id=envelope.causation_id,
                        correlation_id=envelope.correlation_id,
                        trace_id=envelope.trace_id,
                        accepted=True,
                    )),
                ))
                continue

            if command.kind == "stop":
                sequence += 1
                conn.send((
                    "snapshot",
                    asdict(_snapshot(
                        binding,
                        logical_runtime_id,
                        instance_id,
                        WorkerLifecycle.STOPPED,
                        sequence,
                    )),
                ))
                return

            raise RuntimeError(f"unsupported_dr5a_command:{command.kind}")
    except BaseException as exc:
        try:
            conn.send(("error", f"{type(exc).__name__}:{exc}"))
        except (BrokenPipeError, EOFError, OSError):
            pass
        raise
    finally:
        conn.close()


class CausalMissionWorker:
    def __init__(
        self,
        binding: InstanceBinding,
        logical_runtime_id: str,
        timeout: float = 5.0,
    ) -> None:
        bind_cognitive_runtime(binding)
        if binding.ocs_id not in DR5A_ORDER:
            raise PermissionError("dr5a_worker_not_in_canonical_order")
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
        if self._process is not None:
            raise RuntimeError("dr5a_worker_already_started")
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
            raise RuntimeError("dr5a_execution_context_not_distinct")
        self.lifecycle_state = WorkerLifecycle.ACTIVE
        return snapshot

    def health(self) -> MaterialWorkerSnapshot:
        self._require_active()
        assert self._conn is not None
        self._conn.send(_MissionCommand("health"))
        return self._recv("snapshot", MaterialWorkerSnapshot)

    def process(self, envelope: CausalMissionEnvelope) -> CausalMissionReceipt:
        self._require_active()
        assert self._conn is not None
        self._conn.send(_MissionCommand("process", envelope))
        return self._recv("receipt", CausalMissionReceipt)

    def stop(self) -> None:
        if not self.is_alive:
            return
        assert self._conn is not None and self._process is not None
        self._conn.send(_MissionCommand("stop"))
        self._recv("snapshot", MaterialWorkerSnapshot)
        self._process.join(timeout=self._timeout)
        if self._process.is_alive():
            self.crash()
            raise RuntimeError("dr5a_worker_stop_timeout")
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
            raise RuntimeError("dr5a_worker_not_active")

    def _recv(self, expected: str, model: type[Any]) -> Any:
        assert self._conn is not None
        if not self._conn.poll(self._timeout):
            self.crash()
            raise TimeoutError("dr5a_worker_response_timeout")
        kind, payload = self._conn.recv()
        if kind == "error":
            self.crash()
            raise RuntimeError(f"dr5a_worker_child_error:{payload}")
        if kind != expected or not isinstance(payload, dict):
            self.crash()
            raise RuntimeError("invalid_dr5a_worker_response")
        if model is MaterialWorkerSnapshot:
            payload["lifecycle_state"] = WorkerLifecycle(payload["lifecycle_state"])
        return model(**payload)


class ForcedElevenOCSCausalMission:
    def __init__(self, bindings: dict[str, InstanceBinding]) -> None:
        if tuple(bindings.keys()) != DR5A_ORDER:
            raise PermissionError("dr5a_requires_exact_canonical_11_ocs_order")
        if len(bindings) != 11:
            raise PermissionError("dr5a_requires_exactly_eleven_bindings")
        self._bindings = bindings
        self._workers: dict[str, CausalMissionWorker] = {}
        self._snapshots: dict[str, MaterialWorkerSnapshot] = {}

    def start(self) -> dict[str, MaterialWorkerSnapshot]:
        try:
            for index, ocs_id in enumerate(DR5A_ORDER, start=1):
                logical_id = f"dr5a-{index:02d}-{ocs_id.casefold()}"
                worker = CausalMissionWorker(self._bindings[ocs_id], logical_id)
                self._workers[ocs_id] = worker
                self._snapshots[ocs_id] = worker.start()
            if len({s.pid for s in self._snapshots.values()}) != 11:
                raise RuntimeError("dr5a_requires_eleven_distinct_execution_contexts")
            return dict(self._snapshots)
        except BaseException:
            self.stop_all()
            raise

    def execute(
        self,
        initial_payload: dict[str, Any],
        mission_id: str = "mission:dr5a-forced-11ocs",
    ) -> list[CausalMissionReceipt]:
        if not self._workers:
            raise RuntimeError("dr5a_workers_not_started")
        trace_id = f"dr5a-trace:{uuid.uuid4()}"
        correlation_id = f"dr5a-correlation:{uuid.uuid4()}"
        payload = {**initial_payload, "contributions": {}}
        receipts: list[CausalMissionReceipt] = []
        previous_message_id = "FOUNDER_ROOT"
        predecessor_output_hash = _hash_payload(payload)

        for ocs_id in DR5A_ORDER:
            target = self._workers[ocs_id].health()
            payload_hash = _hash_payload(payload)
            if payload_hash != predecessor_output_hash:
                raise RuntimeError("dr5a_causal_hash_chain_break")
            envelope = CausalMissionEnvelope(
                message_id=f"dr5a-msg:{uuid.uuid4()}",
                mission_id=mission_id,
                source_ocs="FOUNDER_INPUT" if not receipts else receipts[-1].target_ocs,
                source_instance_id="external" if not receipts else receipts[-1].target_instance_id,
                source_generation=0 if not receipts else receipts[-1].target_generation,
                target_ocs=ocs_id,
                target_expected_generation=target.generation,
                payload=payload,
                payload_hash=payload_hash,
                predecessor_output_hash=predecessor_output_hash,
                causation_id=previous_message_id,
                correlation_id=correlation_id,
                trace_id=trace_id,
            )
            receipt = self._workers[ocs_id].process(envelope)
            if receipt.input_payload_hash != envelope.payload_hash:
                raise RuntimeError("dr5a_input_hash_mismatch")
            if _hash_payload(receipt.output_payload) != receipt.output_payload_hash:
                raise RuntimeError("dr5a_output_hash_mismatch")
            if receipt.declared_specialty != PROFILES[ocs_id].specialty:
                raise RuntimeError("dr5a_specialty_mismatch")
            if receipt.trace_id != trace_id or receipt.correlation_id != correlation_id:
                raise RuntimeError("dr5a_trace_or_correlation_break")
            receipts.append(receipt)
            payload = receipt.output_payload
            predecessor_output_hash = receipt.output_payload_hash
            previous_message_id = envelope.message_id

        if not mission_has_all_specialty_contributions(payload):
            raise RuntimeError("dr5a_all_specialty_contributions_required")
        return receipts

    def ablation_result(self, receipts: list[CausalMissionReceipt], removed_ocs: str) -> bool:
        if removed_ocs not in DR5A_ORDER:
            raise ValueError("dr5a_unknown_ablation_actor")
        contributions: dict[str, Any] = {}
        for receipt in receipts:
            if receipt.target_ocs == removed_ocs:
                continue
            contributions[receipt.target_ocs] = receipt.output_payload["contributions"][receipt.target_ocs]
        synthetic = {"contributions": contributions}
        return mission_has_all_specialty_contributions(synthetic)

    def stop_all(self) -> None:
        for worker in self._workers.values():
            worker.stop()
