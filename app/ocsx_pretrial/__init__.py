"""Synthetic pretrial enforcement harness for OCS-X.

This package does not instantiate an OCS identity and does not authorize trial runtime.
"""

from .evidence import (
    CausalReadback,
    GenerationReceipt,
    METRIC_IDS,
    MetricBundle,
    MetricEvidence,
    RecoveryReadback,
    TerminalReceipt,
    UNKNOWN,
    evaluate_safety_contract,
    metric_bundle_from_values,
    receipt_hash,
)
from .harness import (
    Decision,
    EvidenceEvent,
    GenerationRecord,
    GenerationStatus,
    PretrialCheckpoint,
    StopReason,
    SyntheticPretrialHarness,
)

__all__ = [
    "CausalReadback",
    "Decision",
    "EvidenceEvent",
    "GenerationReceipt",
    "GenerationRecord",
    "GenerationStatus",
    "METRIC_IDS",
    "MetricBundle",
    "MetricEvidence",
    "PretrialCheckpoint",
    "RecoveryReadback",
    "StopReason",
    "SyntheticPretrialHarness",
    "TerminalReceipt",
    "UNKNOWN",
    "evaluate_safety_contract",
    "metric_bundle_from_values",
    "receipt_hash",
]
