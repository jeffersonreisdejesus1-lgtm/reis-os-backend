"""Synthetic pretrial enforcement harness for OCS-X.

This package does not instantiate an OCS identity and does not authorize trial runtime.
"""

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
    "Decision",
    "EvidenceEvent",
    "GenerationRecord",
    "GenerationStatus",
    "PretrialCheckpoint",
    "StopReason",
    "SyntheticPretrialHarness",
]
