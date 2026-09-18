from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from app.ocs_instances.contracts import InstanceBinding

from .causal_mission import (
    DR5A_ORDER,
    CausalMissionEnvelope,
    CausalMissionReceipt,
    CausalMissionWorker,
    _hash_payload,
    mission_has_all_specialty_contributions,
)


@dataclass(frozen=True, slots=True)
class ConcurrentMissionResult:
    mission_id: str
    trace_id: str
    correlation_id: str
    receipts: tuple[CausalMissionReceipt, ...]
    final_payload: dict[str, Any]


class SharedElevenOCSMissionFleet:
    """DR5B shared 11-OCS fleet for naturally concurrent missions.

    One material worker exists per OCS and is shared by multiple mission
    executions. Per-worker locks serialize pipe access while allowing different
    missions to occupy different OCS stages concurrently. Mission state remains
    envelope-local; no cross-mission mutable cognitive state is shared here.
    """

    def __init__(
        self,
        bindings: dict[str, InstanceBinding],
        *,
        max_inflight_missions: int = 4,
    ) -> None:
        if tuple(bindings.keys()) != DR5A_ORDER or len(bindings) != 11:
            raise PermissionError("dr5b_requires_exact_canonical_11_ocs_order")
        if max_inflight_missions < 2:
            raise ValueError("dr5b_requires_multi_mission_capacity")
        self._bindings = bindings
        self._max_inflight = max_inflight_missions
        self._workers: dict[str, CausalMissionWorker] = {}
        self._worker_locks = {ocs_id: threading.Lock() for ocs_id in DR5A_ORDER}
        self._admission = threading.BoundedSemaphore(max_inflight_missions)
        self._active_lock = threading.Lock()
        self._active_missions: set[str] = set()
        self._max_observed_active = 0

    @property
    def max_observed_active_missions(self) -> int:
        with self._active_lock:
            return self._max_observed_active

    def start(self) -> None:
        try:
            for index, ocs_id in enumerate(DR5A_ORDER, start=1):
                worker = CausalMissionWorker(
                    self._bindings[ocs_id],
                    f"dr5b-{index:02d}-{ocs_id.casefold()}-shared",
                )
                worker.start()
                self._workers[ocs_id] = worker
            if len({worker.instance_id for worker in self._workers.values()}) != 11:
                raise RuntimeError("dr5b_requires_eleven_shared_material_workers")
        except BaseException:
            self.stop_all()
            raise

    def execute_mission(
        self,
        initial_payload: dict[str, Any],
        *,
        mission_id: str | None = None,
    ) -> ConcurrentMissionResult:
        if len(self._workers) != 11:
            raise RuntimeError("dr5b_fleet_not_started")
        mission_id = mission_id or f"mission:dr5b:{uuid.uuid4()}"
        if not self._admission.acquire(blocking=False):
            raise RuntimeError("dr5b_backpressure_inflight_limit")
        with self._active_lock:
            if mission_id in self._active_missions:
                self._admission.release()
                raise RuntimeError("dr5b_duplicate_active_mission_id")
            self._active_missions.add(mission_id)
            self._max_observed_active = max(
                self._max_observed_active,
                len(self._active_missions),
            )
        try:
            trace_id = f"dr5b-trace:{uuid.uuid4()}"
            correlation_id = f"dr5b-correlation:{uuid.uuid4()}"
            payload = {**initial_payload, "mission_id": mission_id, "contributions": {}}
            receipts: list[CausalMissionReceipt] = []
            previous_message_id = "FOUNDER_ROOT"
            predecessor_output_hash = _hash_payload(payload)

            for ocs_id in DR5A_ORDER:
                worker = self._workers[ocs_id]
                with self._worker_locks[ocs_id]:
                    target = worker.health()
                    payload_hash = _hash_payload(payload)
                    if payload_hash != predecessor_output_hash:
                        raise RuntimeError("dr5b_causal_hash_chain_break")
                    envelope = CausalMissionEnvelope(
                        message_id=f"dr5b-msg:{uuid.uuid4()}",
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
                    receipt = worker.process(envelope)
                if receipt.mission_id != mission_id:
                    raise RuntimeError("dr5b_cross_mission_receipt_contamination")
                if receipt.trace_id != trace_id or receipt.correlation_id != correlation_id:
                    raise RuntimeError("dr5b_trace_or_correlation_break")
                if receipt.input_payload_hash != envelope.payload_hash:
                    raise RuntimeError("dr5b_input_hash_mismatch")
                if _hash_payload(receipt.output_payload) != receipt.output_payload_hash:
                    raise RuntimeError("dr5b_output_hash_mismatch")
                if receipt.output_payload.get("mission_id") != mission_id:
                    raise RuntimeError("dr5b_cross_mission_payload_contamination")
                receipts.append(receipt)
                payload = receipt.output_payload
                predecessor_output_hash = receipt.output_payload_hash
                previous_message_id = envelope.message_id

            if not mission_has_all_specialty_contributions(payload):
                raise RuntimeError("dr5b_all_specialty_contributions_required")
            return ConcurrentMissionResult(
                mission_id=mission_id,
                trace_id=trace_id,
                correlation_id=correlation_id,
                receipts=tuple(receipts),
                final_payload=payload,
            )
        finally:
            with self._active_lock:
                self._active_missions.discard(mission_id)
            self._admission.release()

    def execute_many(
        self,
        missions: list[tuple[str, dict[str, Any]]],
    ) -> list[ConcurrentMissionResult]:
        if len(missions) < 2:
            raise ValueError("dr5b_execute_many_requires_multiple_missions")
        mission_ids = [mission_id for mission_id, _ in missions]
        if len(set(mission_ids)) != len(mission_ids):
            raise ValueError("dr5b_mission_ids_must_be_unique")
        with ThreadPoolExecutor(max_workers=self._max_inflight) as executor:
            futures = [
                executor.submit(self.execute_mission, payload, mission_id=mission_id)
                for mission_id, payload in missions
            ]
            return [future.result() for future in futures]

    def stop_all(self) -> None:
        for worker in self._workers.values():
            worker.stop()
        self._workers.clear()
