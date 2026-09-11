from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from app.ocs_instances.contracts import InstanceBinding

from .causal_mission import DR5A_ORDER, mission_has_all_specialty_contributions
from .recovery import RecoverableElevenOCSFleet, RecoveredMissionResult


@dataclass(frozen=True, slots=True)
class LongitudinalCycleRecord:
    cycle_index: int
    mission_id: str
    failed_ocs: str
    trace_id: str
    correlation_id: str
    recovered_generation: int
    recovered_instance_id: str
    receipt_count: int
    contribution_count: int
    identity_binding_stable: bool
    authority_binding_stable: bool
    profile_binding_stable: bool
    state_namespace_stable: bool
    memory_namespace_stable: bool
    causal_reconstruction_valid: bool
    mission_isolation_valid: bool


@dataclass(frozen=True, slots=True)
class LongitudinalQualificationResult:
    cycles: tuple[LongitudinalCycleRecord, ...]
    final_generations: dict[str, int]
    mission_ids: tuple[str, ...]
    trace_ids: tuple[str, ...]
    correlation_ids: tuple[str, ...]
    completed: bool


class LongitudinalDistributedOperation:
    """DR7 repeated distributed operation over one evolving 11-OCS fleet.

    The same fleet persists across missions. Every scheduled recovery advances only
    the failed actor generation while stable institutional binding properties are
    checked after every cycle. Mission-local payload identity and causal receipts
    must remain isolated across the full run.
    """

    def __init__(self, bindings: dict[str, InstanceBinding]) -> None:
        if tuple(bindings.keys()) != DR5A_ORDER or len(bindings) != 11:
            raise PermissionError("dr7_requires_exact_canonical_11_ocs_order")
        self._initial = dict(bindings)
        self._fleet = RecoverableElevenOCSFleet(bindings)
        self._started = False

    def start(self) -> None:
        if self._started:
            raise RuntimeError("dr7_already_started")
        self._fleet.start()
        self._started = True

    def execute_cycles(
        self,
        failure_schedule: Iterable[str],
        *,
        mission_prefix: str = "mission:dr7",
    ) -> LongitudinalQualificationResult:
        if not self._started:
            raise RuntimeError("dr7_not_started")
        schedule = tuple(failure_schedule)
        if len(schedule) < 11:
            raise ValueError("dr7_requires_at_least_eleven_longitudinal_cycles")
        if any(ocs_id not in DR5A_ORDER for ocs_id in schedule):
            raise ValueError("dr7_unknown_failure_target")

        records: list[LongitudinalCycleRecord] = []
        seen_missions: set[str] = set()
        seen_traces: set[str] = set()
        seen_correlations: set[str] = set()

        for index, failed_ocs in enumerate(schedule, start=1):
            mission_id = f"{mission_prefix}:{index:04d}"
            marker = f"DR7_CYCLE_{index:04d}"
            result = self._fleet.execute_with_midflight_recovery(
                {"goal": "longitudinal-distributed-operation", "cycle_marker": marker},
                failed_ocs=failed_ocs,
                mission_id=mission_id,
            )
            self._validate_cycle(result, marker, seen_missions, seen_traces, seen_correlations)
            recovery = result.recovery
            initial = self._initial[failed_ocs]
            contributions = result.final_payload.get("contributions", {})
            records.append(LongitudinalCycleRecord(
                cycle_index=index,
                mission_id=result.mission_id,
                failed_ocs=failed_ocs,
                trace_id=result.trace_id,
                correlation_id=result.correlation_id,
                recovered_generation=recovery.new_generation,
                recovered_instance_id=recovery.new_instance_id,
                receipt_count=len(result.receipts),
                contribution_count=len(contributions),
                identity_binding_stable=recovery.identity_preserved and recovery.ocs_id == initial.ocs_id,
                authority_binding_stable=recovery.authority_preserved,
                profile_binding_stable=recovery.profile_preserved,
                state_namespace_stable=recovery.state_namespace_preserved,
                memory_namespace_stable=recovery.memory_namespace_preserved,
                causal_reconstruction_valid=self._causal_reconstruction_valid(result),
                mission_isolation_valid=result.final_payload.get("cycle_marker") == marker,
            ))
            seen_missions.add(result.mission_id)
            seen_traces.add(result.trace_id)
            seen_correlations.add(result.correlation_id)

        if len(seen_missions) != len(schedule):
            raise RuntimeError("dr7_mission_identity_drift_or_reuse")
        if len(seen_traces) != len(schedule):
            raise RuntimeError("dr7_trace_reuse_detected")
        if len(seen_correlations) != len(schedule):
            raise RuntimeError("dr7_correlation_reuse_detected")
        if not all(
            record.identity_binding_stable
            and record.authority_binding_stable
            and record.profile_binding_stable
            and record.state_namespace_stable
            and record.memory_namespace_stable
            and record.causal_reconstruction_valid
            and record.mission_isolation_valid
            and record.receipt_count == 11
            and record.contribution_count == 11
            for record in records
        ):
            raise RuntimeError("dr7_longitudinal_invariant_failure")

        final_generations = {
            ocs_id: self._fleet._fence.current(ocs_id)  # qualification readback only
            for ocs_id in DR5A_ORDER
        }
        return LongitudinalQualificationResult(
            cycles=tuple(records),
            final_generations=final_generations,
            mission_ids=tuple(record.mission_id for record in records),
            trace_ids=tuple(record.trace_id for record in records),
            correlation_ids=tuple(record.correlation_id for record in records),
            completed=True,
        )

    @staticmethod
    def _validate_cycle(
        result: RecoveredMissionResult,
        marker: str,
        seen_missions: set[str],
        seen_traces: set[str],
        seen_correlations: set[str],
    ) -> None:
        if result.mission_id in seen_missions:
            raise RuntimeError("dr7_duplicate_mission_id")
        if result.trace_id in seen_traces:
            raise RuntimeError("dr7_duplicate_trace_id")
        if result.correlation_id in seen_correlations:
            raise RuntimeError("dr7_duplicate_correlation_id")
        if result.final_payload.get("cycle_marker") != marker:
            raise RuntimeError("dr7_cross_mission_payload_contamination")
        if len(result.receipts) != 11:
            raise RuntimeError("dr7_receipt_count_drift")
        if len({receipt.target_ocs for receipt in result.receipts}) != 11:
            raise RuntimeError("dr7_duplicate_or_missing_actor_contribution")
        if not mission_has_all_specialty_contributions(result.final_payload):
            raise RuntimeError("dr7_specialty_contribution_drift")

    @staticmethod
    def _causal_reconstruction_valid(result: RecoveredMissionResult) -> bool:
        receipts = result.receipts
        if len(receipts) != 11:
            return False
        if any(receipt.trace_id != result.trace_id for receipt in receipts):
            return False
        if any(receipt.correlation_id != result.correlation_id for receipt in receipts):
            return False
        if any(receipt.mission_id != result.mission_id for receipt in receipts):
            return False
        for previous, current in zip(receipts, receipts[1:]):
            if previous.output_payload_hash != current.input_payload_hash:
                return False
        return True

    def stop(self) -> None:
        if self._started:
            self._fleet.stop_all()
            self._started = False
