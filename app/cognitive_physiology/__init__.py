"""Universal cognitive physiology contracts for REIS OS OCSs.

This package is intentionally authority-neutral: it provides shared mechanisms
and fail-closed contracts but never grants institutional authority.
"""

from .binding import CognitiveBindingContext, bind_cognitive_runtime
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
from .runtime import (
    CognitivePhysiologyRuntime,
    InstitutionalState,
    WorkspaceState,
)

__all__ = [
    "BudgetEnvelope",
    "Candidate",
    "CognitiveBindingContext",
    "CognitiveCycleResult",
    "CognitivePhysiologyRuntime",
    "CompetitionResult",
    "EvidenceClass",
    "EpistemicGrade",
    "ExpectedOutcome",
    "HandoffEnvelope",
    "InstitutionalState",
    "LocalMemoryStore",
    "MemoryLevel",
    "NMState",
    "ObservedOutcome",
    "OperationalCommitContext",
    "PredictionResidual",
    "UniversalCognitiveEngine",
    "WorkspaceState",
    "bind_cognitive_runtime",
]
