"""R3 additive replay fixtures for frozen kernel and verified R2 profiles."""

from .fixtures import (
    CAUSAL_CHAIN,
    SLICE_VERSION,
    ReplayPackage,
    SliceExpectation,
    build_replay_packages,
)
from .harness import (
    CausalEvent,
    CausalReceipt,
    CausalRecorder,
    EffectBoundaryGuard,
    NamespaceGuard,
    SpecialtyExecution,
    SpecialtyGoalExecutor,
)

__all__ = [
    "CAUSAL_CHAIN",
    "SLICE_VERSION",
    "CausalEvent",
    "CausalReceipt",
    "CausalRecorder",
    "EffectBoundaryGuard",
    "NamespaceGuard",
    "ReplayPackage",
    "SliceExpectation",
    "SpecialtyExecution",
    "SpecialtyGoalExecutor",
    "build_replay_packages",
]
