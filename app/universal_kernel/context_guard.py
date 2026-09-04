from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ContextClass(StrEnum):
    CANONICAL_STATE = "canonical_state"
    RECOVERED_INSTITUTIONAL_STATE = "recovered_institutional_state"
    CURRENT_RUN_CONTEXT = "current_run_context"
    NON_CANONICAL_CONVERSATIONAL_CONTEXT = "non_canonical_conversational_context"
    FOREIGN_OCS_CONTEXT = "foreign_ocs_context"
    HOST_METADATA = "host_metadata"


@dataclass(frozen=True)
class ContextItem:
    context_ref: str
    context_class: ContextClass
    source_ocs: str | None = None
    autobiographical: bool = False
    declared_actor: str | None = None
    declared_host: str | None = None


@dataclass(frozen=True)
class ContextAssessment:
    accepted_refs: tuple[str, ...]
    rejected_refs: tuple[str, ...]
    identity_conflict: bool
    reasons: tuple[str, ...]


class ContextSanitizer:
    """Treat conversation context as input, never as canonical identity state."""

    def assess(self, active_ocs: str, items: tuple[ContextItem, ...]) -> ContextAssessment:
        accepted: list[str] = []
        rejected: list[str] = []
        reasons: list[str] = []
        identity_conflict = False

        for item in items:
            if not item.context_ref:
                rejected.append(item.context_ref)
                reasons.append("context_ref_required")
                continue

            if item.context_class is ContextClass.FOREIGN_OCS_CONTEXT:
                rejected.append(item.context_ref)
                reasons.append("foreign_ocs_context_rejected")
                if item.autobiographical:
                    identity_conflict = True
                continue

            if (
                item.source_ocs is not None
                and item.source_ocs != active_ocs
                and item.autobiographical
            ):
                rejected.append(item.context_ref)
                reasons.append("cross_ocs_autobiographical_context_rejected")
                identity_conflict = True
                continue

            if item.declared_actor is not None and item.declared_actor != active_ocs:
                if item.context_class is not ContextClass.HOST_METADATA:
                    rejected.append(item.context_ref)
                    reasons.append("institutional_actor_identity_conflict")
                    identity_conflict = True
                    continue

            accepted.append(item.context_ref)

        return ContextAssessment(
            accepted_refs=tuple(accepted),
            rejected_refs=tuple(rejected),
            identity_conflict=identity_conflict,
            reasons=tuple(reasons),
        )

    @staticmethod
    def classify(
        *,
        active_ocs: str,
        source_ocs: str | None,
        canonical: bool = False,
        recovered: bool = False,
        host_metadata: bool = False,
    ) -> ContextClass:
        if host_metadata:
            return ContextClass.HOST_METADATA
        if canonical:
            return ContextClass.CANONICAL_STATE
        if recovered:
            return ContextClass.RECOVERED_INSTITUTIONAL_STATE
        if source_ocs is not None and source_ocs != active_ocs:
            return ContextClass.FOREIGN_OCS_CONTEXT
        if source_ocs == active_ocs:
            return ContextClass.CURRENT_RUN_CONTEXT
        return ContextClass.NON_CANONICAL_CONVERSATIONAL_CONTEXT
