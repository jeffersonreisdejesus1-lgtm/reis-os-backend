"""Shared modular constitutional runtime kernel for REIS OS.

This package implements the R1 frozen runtime contracts without migrating any OCS
profile and without conferring authority.
"""

from .contracts import (
    ActionProposal,
    AuthorizedActionEnvelope,
    EffectAttemptResult,
    GovernanceDecision,
    GovernanceResult,
    HandoffPackage,
    StateCommitRecord,
)

__all__ = [
    "ActionProposal",
    "AuthorizedActionEnvelope",
    "EffectAttemptResult",
    "GovernanceDecision",
    "GovernanceResult",
    "HandoffPackage",
    "StateCommitRecord",
]
