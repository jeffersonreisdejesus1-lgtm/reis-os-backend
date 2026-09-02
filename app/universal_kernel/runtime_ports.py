from __future__ import annotations

from dataclasses import dataclass

from .contracts import HandoffPackage, OCSProfile, PIActivation, Receipt
from .state_trace import StateCore, TraceCore


class IdentityLoader:
    def load(self, profile: OCSProfile):
        from .contracts import IdentityContext
        return IdentityContext(profile.ocs_id, profile.identity, profile.ancestry, profile.predecessor, profile.constitution_ref)


class PIActivationEngine:
    VALID_CLASSES = {"CORE_ALWAYS", "RISK_TRIGGERED", "SPECIALTY_NATIVE", "ON_DEMAND", "HANDOFF_BOUND", "DEFERRED"}

    def activate(self, pi_id: str, activation_class: str, reason: str, producer: str, consumer: str, contribution: str) -> PIActivation:
        if activation_class not in self.VALID_CLASSES:
            raise ValueError("invalid_pi_activation_class")
        return PIActivation(pi_id, activation_class, reason, producer, consumer, contribution)


@dataclass(frozen=True)
class CognitivePlan:
    goal_ref: str
    actions: tuple[str, ...]


class CognitiveRuntimePort:
    """Proposal-only cognitive port. It has no broker/effector handle."""

    def plan(self, goal_ref: str, actions: tuple[str, ...]) -> CognitivePlan:
        return CognitivePlan(goal_ref, actions)


class RecoveryManager:
    def __init__(self, state: StateCore, trace: TraceCore) -> None:
        self.state = state
        self.trace = trace

    def recover_verified(self, checkpoint_ref: str) -> dict:
        restored = self.state.rollback_to_verified(checkpoint_ref)
        if self.trace.causal_status() != "PROVEN":
            raise RuntimeError("recovery_trace_not_proven")
        return restored


class HandoffRouter:
    def route(self, package: HandoffPackage) -> HandoffPackage:
        if package.authority_transfer:
            raise ValueError("handoff_must_not_transfer_authority")
        return package


class ReceiptClosure:
    def close(self, *, object_ref: str, status: str, reservations: tuple[str, ...], next_ocs: str | None, authorized_next_scope: str | None, prohibited: tuple[str, ...]) -> Receipt:
        return Receipt(object_ref, status, reservations, next_ocs, authorized_next_scope, prohibited)


@dataclass(frozen=True)
class LearningCandidate:
    candidate_id: str
    ocs_id: str
    source_experience_ref: str
    verified: bool = False


class LPEPort:
    """Local learning port. No constitution or authority mutation methods exist."""

    def __init__(self, ocs_id: str, memory_namespace: str) -> None:
        self.ocs_id = ocs_id
        self.memory_namespace = memory_namespace
        self._candidates: dict[str, LearningCandidate] = {}

    def propose(self, candidate_id: str, source_experience_ref: str) -> LearningCandidate:
        candidate = LearningCandidate(candidate_id, self.ocs_id, source_experience_ref, False)
        self._candidates[candidate_id] = candidate
        return candidate

    def verify(self, candidate_id: str) -> LearningCandidate:
        old = self._candidates[candidate_id]
        candidate = LearningCandidate(old.candidate_id, old.ocs_id, old.source_experience_ref, True)
        self._candidates[candidate_id] = candidate
        return candidate

    def import_cross_ocs_autobiography(self, *_args, **_kwargs):
        raise PermissionError("cross_ocs_autobiography_import_prohibited")
