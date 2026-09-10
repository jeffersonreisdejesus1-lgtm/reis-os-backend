from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import Decision


@dataclass(frozen=True, slots=True)
class AuthorityDecision:
    decision: Decision
    reason: str


class KernelAuthorityPort(Protocol):
    def check_authority(
        self, *, authority_ref: str, effect_class: str, founder_gate_open: bool
    ) -> AuthorityDecision: ...


class HazelContinuityPort(Protocol):
    def checkpoint(self, *, checkpoint_ref: str) -> str: ...

    def recover(self, *, checkpoint_ref: str) -> str: ...


class TrialKernelAdapter:
    """Trial-only authority boundary; it never executes an effect."""

    _allowed_effect_classes = frozenset({"SYNTHETIC", "REVERSIBLE"})

    def check_authority(
        self, *, authority_ref: str, effect_class: str, founder_gate_open: bool
    ) -> AuthorityDecision:
        if not authority_ref:
            return AuthorityDecision(Decision.HOLD, "authority_unknown")
        if founder_gate_open:
            return AuthorityDecision(Decision.DENY, "founder_reserved_gate")
        if effect_class not in self._allowed_effect_classes:
            return AuthorityDecision(Decision.DENY, "material_effect_restricted")
        return AuthorityDecision(Decision.ALLOW, "trial_build_boundary_only")


class TrialHazelAdapter:
    """Continuity adapter for builder verification; no authority is created."""

    def checkpoint(self, *, checkpoint_ref: str) -> str:
        if not checkpoint_ref:
            raise ValueError("checkpoint_ref_required")
        return checkpoint_ref

    def recover(self, *, checkpoint_ref: str) -> str:
        if not checkpoint_ref:
            raise ValueError("checkpoint_ref_required")
        return checkpoint_ref
