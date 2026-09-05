from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.governance_refactor.contracts import Completeness, MissionMetricsRecord

FOUNDER_TIMEZONE = ZoneInfo("America/Sao_Paulo")


@dataclass(frozen=True, slots=True)
class MissionTimingInput:
    record_id: str
    mission_id: str
    ocs_id: str
    started_at: datetime
    completed_at: datetime | None
    active_execution_seconds: int | None
    waiting_seconds: int | None
    founder_wait_seconds: int | None
    external_wait_seconds: int | None
    retries: int
    failures: int
    refactors: int
    founder_interventions: int
    autonomous_completion: bool | None
    source_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    observed_at: datetime
    product_id: str | None = None
    gate_id: str | None = None


@dataclass(frozen=True, slots=True)
class MissionTimingSnapshot:
    elapsed_seconds: int | None
    elapsed_minutes: float | None
    elapsed_hours: float | None
    active_execution_seconds: int | None
    waiting_seconds: int | None
    founder_wait_seconds: int | None
    external_wait_seconds: int | None
    retries: int
    failures: int
    refactors: int
    founder_interventions: int
    autonomous_completion: bool | None
    throughput_per_hour: float | None
    founder_local_started_at: datetime
    founder_local_completed_at: datetime | None


class MetricsValidationError(ValueError):
    pass


def instrument_mission(
    input_data: MissionTimingInput,
) -> tuple[MissionMetricsRecord, MissionTimingSnapshot]:
    """Build evidence-oriented timing records without verdict or authority."""
    _aware(input_data.started_at, input_data.completed_at, input_data.observed_at)
    counters = (
        input_data.retries,
        input_data.failures,
        input_data.refactors,
        input_data.founder_interventions,
    )
    durations = (
        input_data.active_execution_seconds,
        input_data.waiting_seconds,
        input_data.founder_wait_seconds,
        input_data.external_wait_seconds,
    )
    if any(value < 0 for value in counters):
        raise MetricsValidationError("negative_counter")
    if any(value is not None and value < 0 for value in durations):
        raise MetricsValidationError("negative_duration")
    elapsed_seconds: int | None = None
    if input_data.completed_at is not None:
        elapsed = input_data.completed_at - input_data.started_at
        elapsed_seconds = int(elapsed.total_seconds())
        if elapsed_seconds < 0:
            raise MetricsValidationError("completed_before_started")
    completeness = (
        Completeness.COMPLETE
        if input_data.completed_at is not None and input_data.source_refs
        else Completeness.PARTIAL
    )
    record = MissionMetricsRecord(
        record_id=input_data.record_id,
        mission_id=input_data.mission_id,
        ocs_id=input_data.ocs_id,
        product_id=input_data.product_id,
        gate_id=input_data.gate_id,
        started_at=input_data.started_at,
        completed_at=input_data.completed_at,
        active_execution_seconds=input_data.active_execution_seconds,
        waiting_seconds=input_data.waiting_seconds,
        founder_wait_seconds=input_data.founder_wait_seconds,
        external_wait_seconds=input_data.external_wait_seconds,
        retries=input_data.retries,
        failures=input_data.failures,
        refactors=input_data.refactors,
        founder_interventions=input_data.founder_interventions,
        autonomous_completion=input_data.autonomous_completion,
        source_refs=input_data.source_refs,
        source_links=(),
        provenance_refs=input_data.provenance_refs,
        measurement_method="actual_clock_timestamps",
        measurement_version="r7-v0.1",
        observed_at=input_data.observed_at,
        completeness=completeness,
    )
    throughput = None
    if elapsed_seconds and elapsed_seconds > 0:
        throughput = 3600.0 / elapsed_seconds
    snapshot = MissionTimingSnapshot(
        elapsed_seconds=elapsed_seconds,
        elapsed_minutes=None if elapsed_seconds is None else elapsed_seconds / 60.0,
        elapsed_hours=None if elapsed_seconds is None else elapsed_seconds / 3600.0,
        active_execution_seconds=input_data.active_execution_seconds,
        waiting_seconds=input_data.waiting_seconds,
        founder_wait_seconds=input_data.founder_wait_seconds,
        external_wait_seconds=input_data.external_wait_seconds,
        retries=input_data.retries,
        failures=input_data.failures,
        refactors=input_data.refactors,
        founder_interventions=input_data.founder_interventions,
        autonomous_completion=input_data.autonomous_completion,
        throughput_per_hour=throughput,
        founder_local_started_at=input_data.started_at.astimezone(FOUNDER_TIMEZONE),
        founder_local_completed_at=(
            None
            if input_data.completed_at is None
            else input_data.completed_at.astimezone(FOUNDER_TIMEZONE)
        ),
    )
    return record, snapshot


def _aware(*values: datetime | None) -> None:
    for value in values:
        if value is not None and value.tzinfo is None:
            raise MetricsValidationError("timezone_aware_timestamp_required")
