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
    "CognitivePhysiologyRuntime",
    "InstitutionalState",
    "WorkspaceState",
]
