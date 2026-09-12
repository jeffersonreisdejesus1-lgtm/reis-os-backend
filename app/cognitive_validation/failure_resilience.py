from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FaultKind(StrEnum):
    STALE_MEMORY = "stale_memory"
    CORRUPT_MEMORY = "corrupt_memory"
    STALE_GENERATION = "stale_generation"
    DUPLICATE_EXPERIENCE = "duplicate_experience"
    FALSE_FEEDBACK = "false_feedback"
    PARTIAL_COMMIT = "partial_commit"
    CORRUPT_CHECKPOINT = "corrupt_checkpoint"


class ProtectiveAction(StrEnum):
    DENY = "deny"
    QUARANTINE = "quarantine"
    DEDUPLICATE = "deduplicate"
    RECONCILE = "reconcile"
    ROLLBACK = "rollback"


@dataclass(frozen=True, slots=True)
class FaultProbe:
    kind: FaultKind
    current_generation: int = 3
    presented_generation: int = 3
    current_memory_version: int = 7
    presented_memory_version: int = 7
    memory_checksum_valid: bool = True
    experience_seen: bool = False
    feedback_verified: bool = True
    commit_complete: bool = True
    checkpoint_checksum_valid: bool = True


@dataclass(frozen=True, slots=True)
class FaultDisposition:
    kind: FaultKind
    action: ProtectiveAction
    mutation_allowed: bool
    learning_allowed: bool
    advance_allowed: bool
    reason: str


class CognitiveFailureResilienceGate:
    """Deterministic AB8 fail-closed cognitive fault boundary."""

    def evaluate(self, probe: FaultProbe) -> FaultDisposition:
        if probe.kind is FaultKind.STALE_GENERATION:
            stale = probe.presented_generation != probe.current_generation
            if stale:
                return self._blocked(probe.kind, ProtectiveAction.DENY, "stale_generation_fenced")
            return self._safe(probe.kind, "generation_current")

        if probe.kind is FaultKind.STALE_MEMORY:
            stale = probe.presented_memory_version < probe.current_memory_version
            if stale:
                return self._blocked(probe.kind, ProtectiveAction.DENY, "stale_memory_rejected")
            return self._safe(probe.kind, "memory_version_current")

        if probe.kind is FaultKind.CORRUPT_MEMORY:
            if not probe.memory_checksum_valid:
                return self._blocked(probe.kind, ProtectiveAction.QUARANTINE, "memory_checksum_invalid")
            return self._safe(probe.kind, "memory_checksum_valid")

        if probe.kind is FaultKind.DUPLICATE_EXPERIENCE:
            if probe.experience_seen:
                return FaultDisposition(
                    kind=probe.kind,
                    action=ProtectiveAction.DEDUPLICATE,
                    mutation_allowed=False,
                    learning_allowed=False,
                    advance_allowed=True,
                    reason="duplicate_experience_suppressed",
                )
            return self._safe(probe.kind, "experience_new")

        if probe.kind is FaultKind.FALSE_FEEDBACK:
            if not probe.feedback_verified:
                return self._blocked(probe.kind, ProtectiveAction.QUARANTINE, "unverified_feedback_quarantined")
            return self._safe(probe.kind, "feedback_verified")

        if probe.kind is FaultKind.PARTIAL_COMMIT:
            if not probe.commit_complete:
                return self._blocked(probe.kind, ProtectiveAction.RECONCILE, "partial_commit_requires_reconciliation")
            return self._safe(probe.kind, "commit_complete")

        if probe.kind is FaultKind.CORRUPT_CHECKPOINT:
            if not probe.checkpoint_checksum_valid:
                return self._blocked(probe.kind, ProtectiveAction.ROLLBACK, "checkpoint_corruption_detected")
            return self._safe(probe.kind, "checkpoint_valid")

        raise ValueError("unknown_ab8_fault_kind")

    @staticmethod
    def _blocked(kind: FaultKind, action: ProtectiveAction, reason: str) -> FaultDisposition:
        return FaultDisposition(
            kind=kind,
            action=action,
            mutation_allowed=False,
            learning_allowed=False,
            advance_allowed=False,
            reason=reason,
        )

    @staticmethod
    def _safe(kind: FaultKind, reason: str) -> FaultDisposition:
        return FaultDisposition(
            kind=kind,
            action=ProtectiveAction.DENY,
            mutation_allowed=True,
            learning_allowed=True,
            advance_allowed=True,
            reason=reason,
        )


def run_ab8_fault_matrix() -> tuple[FaultDisposition, ...]:
    gate = CognitiveFailureResilienceGate()
    probes = (
        FaultProbe(kind=FaultKind.STALE_MEMORY, presented_memory_version=6),
        FaultProbe(kind=FaultKind.CORRUPT_MEMORY, memory_checksum_valid=False),
        FaultProbe(kind=FaultKind.STALE_GENERATION, presented_generation=2),
        FaultProbe(kind=FaultKind.DUPLICATE_EXPERIENCE, experience_seen=True),
        FaultProbe(kind=FaultKind.FALSE_FEEDBACK, feedback_verified=False),
        FaultProbe(kind=FaultKind.PARTIAL_COMMIT, commit_complete=False),
        FaultProbe(kind=FaultKind.CORRUPT_CHECKPOINT, checkpoint_checksum_valid=False),
    )
    return tuple(gate.evaluate(probe) for probe in probes)
