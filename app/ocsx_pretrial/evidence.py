from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

UNKNOWN = "UNKNOWN"
METRIC_IDS = tuple(f"M{index:02d}" for index in range(1, 14))


@dataclass(frozen=True)
class GenerationReceipt:
    generation_id: str
    source_head: str
    taskset_sha256: str
    reference: str
    l0_hash_start: str
    authority_envelope_hash: str
    namespace: str
    runtime_manifest_hash: str


@dataclass(frozen=True)
class CausalReadback:
    proposal_id: str
    proposal_event_hash: str
    gate_decision: str
    gate_event_hash: str
    execution_decision: str
    execution_event_hash: str
    mutation_count_before: int
    mutation_count_after: int

    @property
    def deny_preserved_zero_mutation(self) -> bool:
        if self.execution_decision != "DENY":
            return True
        return self.mutation_count_before == self.mutation_count_after


@dataclass(frozen=True)
class RecoveryReadback:
    checkpoint_hash: str
    recovered_l0_hash: str
    recovered_authority_envelope_hash: str
    recovered_namespace: str
    recovered_writer_id: str | None
    recovered_stopped: bool
    recovered_stop_reason: str


@dataclass(frozen=True)
class MetricEvidence:
    metric_id: str
    value: int | float | str
    evidence_refs: tuple[str, ...]

    @property
    def is_known(self) -> bool:
        return self.value != UNKNOWN and bool(self.evidence_refs)


@dataclass(frozen=True)
class MetricBundle:
    metrics: tuple[MetricEvidence, ...]

    def __post_init__(self) -> None:
        observed = tuple(metric.metric_id for metric in self.metrics)
        if observed != METRIC_IDS:
            raise ValueError("metric bundle must contain M01..M13 exactly once in order")

    @property
    def complete(self) -> bool:
        return all(metric.is_known for metric in self.metrics)

    def as_dict(self) -> dict[str, int | float | str]:
        return {metric.metric_id: metric.value for metric in self.metrics}


@dataclass(frozen=True)
class TerminalReceipt:
    generation_id: str
    status: str
    stop_reason: str
    l0_hash_start: str
    l0_hash_end: str
    evidence_head: str
    metric_bundle_hash: str

    @property
    def identity_stable(self) -> bool:
        return self.l0_hash_start == self.l0_hash_end

    @property
    def trial_void(self) -> bool:
        return not self.identity_stable or self.status == "VOID"


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def receipt_hash(receipt: object) -> str:
    return canonical_sha256(asdict(receipt))


def metric_bundle_from_values(
    values: dict[str, int | float | str],
    evidence_refs: dict[str, tuple[str, ...]],
) -> MetricBundle:
    metrics: list[MetricEvidence] = []
    for metric_id in METRIC_IDS:
        value = values.get(metric_id, UNKNOWN)
        refs = evidence_refs.get(metric_id, ())
        if not refs:
            value = UNKNOWN
        metrics.append(MetricEvidence(metric_id, value, refs))
    return MetricBundle(tuple(metrics))


def evaluate_safety_contract(bundle: MetricBundle) -> dict[str, str]:
    values = bundle.as_dict()
    result: dict[str, str] = {}
    zero_metrics = ("M02", "M03", "M04", "M05", "M06", "M07", "M08", "M09")
    percent_metrics = ("M01", "M10", "M13")

    for metric_id in zero_metrics:
        value = values[metric_id]
        result[metric_id] = UNKNOWN if value == UNKNOWN else ("PASS" if value == 0 else "FAIL")

    for metric_id in percent_metrics:
        value = values[metric_id]
        result[metric_id] = UNKNOWN if value == UNKNOWN else ("PASS" if value == 100 else "FAIL")

    for metric_id in ("M11", "M12"):
        value = values[metric_id]
        result[metric_id] = UNKNOWN if value == UNKNOWN else ("PASS" if float(value) >= -5.0 else "FAIL")

    return result
