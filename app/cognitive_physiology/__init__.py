"""Universal cognitive physiology contracts for REIS OS OCSs.

This package is intentionally authority-neutral: it provides shared mechanisms
and fail-closed contracts but never grants institutional authority.
"""

from .contracts import (
    BudgetEnvelope,
    Candidate,
    EvidenceClass,
    EpistemicGrade,
    HandoffEnvelope,
    MemoryLevel,
    NMState,
    OperationalCommitContext,
    PredictionResidual,
)
from .engine import (
    CognitiveCycleResult,
    CompetitionResult,
    ExpectedOutcome,
    LocalMemoryStore,
    ObservedOutcome,
    UniversalCognitiveEngine,
)
from .runtime import CognitivePhysiologyRuntime, InstitutionalState, WorkspaceState

__all__ = [
    "BudgetEnvelope",
    "Candidate",
    "EvidenceClass",
    "EpistemicGrade",
    "HandoffEnvelope",
    "MemoryLevel",
    "NMState",
    "OperationalCommitContext",
    "PredictionResidual",
    "CognitiveCycleResult",
    "CompetitionResult",
    "ExpectedOutcome",
    "LocalMemoryStore",
    "ObservedOutcome",
    "UniversalCognitiveEngine",
    "CognitivePhysiologyRuntime",
    "InstitutionalState",
    "WorkspaceState",
]
