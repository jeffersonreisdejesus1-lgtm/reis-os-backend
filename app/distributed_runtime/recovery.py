from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, replace
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
class RecoveryEvent:
    ocs_id: str
    old_instance_id: str
    new_instance_id: str
    old_generation: int
    new_generation: int
    replayed_message_id: str
    identity_preserved: bool
    authority_preserved: bool
    profile_preserved: bool
    state_namespace_preserved: bool
    memory_namespace_preserved: bool


@dataclass(frozen=True, slots=True)
class RecoveredMissionResult:
    mission_id: str
    trace_id: str
    correlation_id: str
    receipts: tuple[CausalMissionReceipt, ...]
    final_payload: dict[str, Any]
    recovery: RecoveryEvent


@dataclass(frozen=True, slots=True)
class LiveStaleFenceEvidence:
    ocs_id: str
    stale_instance_id: str
    current_instance_id: str
    stale_generation: int
    current_generation: int
    stale_process_alive_after_advance: bool
    stale_receipt_produced: bool
    stale_commit_denied: bool
    stale_effect_denied: bool
    current_receipt_produced: bool
    current_commit_allowed: bool
    current_effect_allowed: bool
    stale_message_id: str
    current_message_id: str


class GenerationFenceRegistry:
    """Supervisor-owned generation fencing used by DR6 commit/effect guards."""

    def __init__(self, bindings: dict[str, InstanceBinding]) -> None:
        self._lock = threading.Lock()
        self._current = {ocs_id: binding.generation for ocs_id, binding in bindings.items()}

    def current(self, ocs_id: str) -> int:
        with self._lock:
            return self._current[ocs_id]

    def advance(self, ocs_id: str, old_generation: int) -> int:
        with self._lock:
            if self._current[ocs_id] != old_generation:
                raise PermissionError("dr6_generation_advance_race")
            self._current[ocs_id] = old_generation + 1
            return self._current[ocs_id]

    def assert_current(self, ocs_id: str, generation: int) -> None:
        with self._lock:
            if self._current[ocs_id] != generation:
                raise PermissionError("dr6_stale_generation_fenced")


class RecoverableElevenOCSFleet:
    """DR6 distributed fleet with independent crash, fencing, restart and safe replay.

    Recovery preserves institutional identity/binding properties while replacing
    only the material incarnation and incrementing generation. The message that
    was in-flight at the failed actor is replayed once against the replacement
    only after the old generation is fenced.
    """

    def __init__(self, bindings: dict[str, InstanceBinding]) -> None:
        if tuple(bindings.keys()) != DR5A_ORDER or len(bindings) != 11:
            raise PermissionError("dr6_requires_exact_canonical_11_ocs_order")
        self._bindings = dict(bindings)
        self._workers: dict[str, CausalMissionWorker] = {}
        self._worker_locks = {ocs_id: threading.RLock() for ocs_id in DR5A_ORDER}
        self._fence = GenerationFenceRegistry(bindings)

    def start(self) -> None:
        try:
            for index, ocs_id in enumerate(DR5A_ORDER, start=1):
                worker = CausalMissionWorker(
                    self._bindings[ocs_id],
                    f"dr6-{index:02d}-{ocs_id.casefold()}-recoverable",
                )
                worker.start()
                self._workers[ocs_id] = worker
            if len({worker.instance_id for worker in self._workers.values()}) != 11:
                raise RuntimeError("dr6_requires_eleven_material_workers")
        except BaseException:
            self.stop_all()
            raise

    def health_instance_ids(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for ocs_id, worker in self._workers.items():
            with self._worker_locks[ocs_id]:
                result[ocs_id] = worker.health().instance_id
        return result

    def assert_commit_allowed(self, ocs_id: str, generation: int) -> None:
        self._fence.assert_current(ocs_id, generation)

    def assert_effect_allowed(self, ocs_id: str, generation: int) -> None:
        self._fence.assert_current(ocs_id, generation)

    def exercise_live_stale_writer_fencing(
        self,
        ocs_id: str = "DÉDALA",
    ) -> LiveStaleFenceEvidence:
        """Prove fencing while the old worker remains alive and can still compute.

        The stale worker is deliberately kept alive after generation advances.
        It may produce a local receipt, but supervisor-owned commit/effect gates
        must deny generation N while generation N+1 is current. A replacement
        worker at N+1 must be able to compute and cross those same gates.
        """
        if len(self._workers) != 11:
            raise RuntimeError("dr6_fleet_not_started")
        if ocs_id not in DR5A_ORDER:
            raise ValueError("dr6_unknown_failed_ocs")

        with self._worker_locks[ocs_id]:
            stale_worker = self._workers[ocs_id]
            stale_binding = self._bindings[ocs_id]
            stale_health = stale_worker.health()
            stale_generation = stale_binding.generation
            current_generation = self._fence.advance(ocs_id, stale_generation)

            current_binding = replace(
                stale_binding,
                generation=current_generation,
                predecessor_binding_id=stale_binding.binding_id,
                binding_id=f"{stale_binding.binding_id}:g{current_generation}:supplemental",
                version=stale_binding.version + 1,
            )
            current_worker = CausalMissionWorker(
                current_binding,
                stale_worker.logical_runtime_id,
            )
            current_worker.start()

            try:
                stale_alive_after_advance = stale_worker.health().instance_id == stale_health.instance_id
                mission_id = f"mission:dr6s:{uuid.uuid4()}"
                trace_id = f"dr6s-trace:{uuid.uuid4()}"
                correlation_id = f"dr6s-correlation:{uuid.uuid4()}"
                payload = {
                    "goal": "live stale writer fencing supplemental qualification",
                    "mission_id": mission_id,
                    "contributions": {},
                }
                payload_hash = _hash_payload(payload)

                stale_envelope = CausalMissionEnvelope(
                    message_id=f"dr6s-stale-msg:{uuid.uuid4()}",
                    mission_id=mission_id,
                    source_ocs="FOUNDER_INPUT",
                    source_instance_id="external",
                    source_generation=0,
                    target_ocs=ocs_id,
                    target_expected_generation=stale_generation,
                    payload=payload,
                    payload_hash=payload_hash,
                    predecessor_output_hash=payload_hash,
                    causation_id="FOUNDER_ROOT",
                    correlation_id=correlation_id,
                    trace_id=trace_id,
                )
                stale_receipt = stale_worker.process(stale_envelope)

                stale_commit_denied = False
                stale_effect_denied = False
                try:
                    self.assert_commit_allowed(ocs_id, stale_generation)
                except PermissionError as exc:
                    stale_commit_denied = str(exc) == "dr6_stale_generation_fenced"
                try:
                    self.assert_effect_allowed(ocs_id, stale_generation)
                except PermissionError as exc:
                    stale_effect_denied = str(exc) == "dr6_stale_generation_fenced"

                current_envelope = replace(
                    stale_envelope,
                    message_id=f"dr6s-current-msg:{uuid.uuid4()}",
                    target_expected_generation=current_generation,
                )
                current_receipt = current_worker.process(current_envelope)
                self.assert_commit_allowed(ocs_id, current_generation)
                self.assert_effect_allowed(ocs_id, current_generation)

                evidence = LiveStaleFenceEvidence(
                    ocs_id=ocs_id,
                    stale_instance_id=stale_health.instance_id,
                    current_instance_id=current_worker.instance_id,
                    stale_generation=stale_generation,
                    current_generation=current_generation,
                    stale_process_alive_after_advance=stale_alive_after_advance,
                    stale_receipt_produced=stale_receipt.target_generation == stale_generation,
                    stale_commit_denied=stale_commit_denied,
                    stale_effect_denied=stale_effect_denied,
                    current_receipt_produced=current_receipt.target_generation == current_generation,
                    current_commit_allowed=True,
                    current_effect_allowed=True,
                    stale_message_id=stale_envelope.message_id,
                    current_message_id=current_envelope.message_id,
                )
            except BaseException:
                current_worker.stop()
                raise

            # Retire the deliberately stale split-brain incarnation only after
            # its compute + denied commit/effect attempt has been observed.
            stale_worker.stop()
            self._bindings[ocs_id] = current_binding
            self._workers[ocs_id] = current_worker
            return evidence

    def _restart_actor(self, ocs_id: str, replayed_message_id: str) -> RecoveryEvent:
        with self._worker_locks[ocs_id]:
            old_worker = self._workers[ocs_id]
            old_binding = self._bindings[ocs_id]
            old_instance_id = old_worker.instance_id
            old_generation = old_binding.generation

            old_worker.crash()
            new_generation = self._fence.advance(ocs_id, old_generation)
            new_binding = replace(
                old_binding,
                generation=new_generation,
                predecessor_binding_id=old_binding.binding_id,
                binding_id=f"{old_binding.binding_id}:g{new_generation}",
                version=old_binding.version + 1,
            )
            replacement = CausalMissionWorker(
                new_binding,
                old_worker.logical_runtime_id,
            )
            replacement.start()
            self._bindings[ocs_id] = new_binding
            self._workers[ocs_id] = replacement

            return RecoveryEvent(
                ocs_id=ocs_id,
                old_instance_id=old_instance_id,
                new_instance_id=replacement.instance_id,
                old_generation=old_generation,
                new_generation=new_generation,
                replayed_message_id=replayed_message_id,
                identity_preserved=new_binding.ocs_id == old_binding.ocs_id,
                authority_preserved=new_binding.authority_ref == old_binding.authority_ref,
                profile_preserved=new_binding.profile_hash == old_binding.profile_hash,
                state_namespace_preserved=new_binding.state_namespace == old_binding.state_namespace,
                memory_namespace_preserved=new_binding.memory_namespace == old_binding.memory_namespace,
            )

    def execute_with_midflight_recovery(
        self,
        initial_payload: dict[str, Any],
        *,
        failed_ocs: str = "DÉDALA",
        mission_id: str | None = None,
    ) -> RecoveredMissionResult:
        if len(self._workers) != 11:
            raise RuntimeError("dr6_fleet_not_started")
        if failed_ocs not in DR5A_ORDER:
            raise ValueError("dr6_unknown_failed_ocs")

        mission_id = mission_id or f"mission:dr6:{uuid.uuid4()}"
        trace_id = f"dr6-trace:{uuid.uuid4()}"
        correlation_id = f"dr6-correlation:{uuid.uuid4()}"
        payload = {**initial_payload, "mission_id": mission_id, "contributions": {}}
        receipts: list[CausalMissionReceipt] = []
        previous_message_id = "FOUNDER_ROOT"
        predecessor_output_hash = _hash_payload(payload)
        recovery: RecoveryEvent | None = None

        for ocs_id in DR5A_ORDER:
            worker = self._workers[ocs_id]
            with self._worker_locks[ocs_id]:
                target = worker.health()
                self._fence.assert_current(ocs_id, target.generation)
                payload_hash = _hash_payload(payload)
                if payload_hash != predecessor_output_hash:
                    raise RuntimeError("dr6_causal_hash_chain_break")
                envelope = CausalMissionEnvelope(
                    message_id=f"dr6-msg:{uuid.uuid4()}",
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

            if ocs_id == failed_ocs:
                recovery = self._restart_actor(ocs_id, envelope.message_id)
                self._fence.assert_current(ocs_id, recovery.new_generation)
                envelope = replace(
                    envelope,
                    target_expected_generation=recovery.new_generation,
                )

            worker = self._workers[ocs_id]
            with self._worker_locks[ocs_id]:
                current = worker.health()
                self._fence.assert_current(ocs_id, current.generation)
                receipt = worker.process(envelope)

            if receipt.mission_id != mission_id:
                raise RuntimeError("dr6_cross_mission_receipt_contamination")
            if receipt.trace_id != trace_id or receipt.correlation_id != correlation_id:
                raise RuntimeError("dr6_trace_or_correlation_break")
            if receipt.input_payload_hash != envelope.payload_hash:
                raise RuntimeError("dr6_input_hash_mismatch")
            if _hash_payload(receipt.output_payload) != receipt.output_payload_hash:
                raise RuntimeError("dr6_output_hash_mismatch")
            if receipt.output_payload.get("mission_id") != mission_id:
                raise RuntimeError("dr6_cross_mission_payload_contamination")
            receipts.append(receipt)
            payload = receipt.output_payload
            predecessor_output_hash = receipt.output_payload_hash
            previous_message_id = envelope.message_id

        if recovery is None:
            raise RuntimeError("dr6_recovery_not_exercised")
        if not mission_has_all_specialty_contributions(payload):
            raise RuntimeError("dr6_all_specialty_contributions_required")
        if len({receipt.target_ocs for receipt in receipts}) != 11:
            raise RuntimeError("dr6_duplicate_or_missing_contribution")
        return RecoveredMissionResult(
            mission_id=mission_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            receipts=tuple(receipts),
            final_payload=payload,
            recovery=recovery,
        )

    def stop_all(self) -> None:
        for ocs_id, worker in list(self._workers.items()):
            with self._worker_locks[ocs_id]:
                worker.stop()
        self._workers.clear()
