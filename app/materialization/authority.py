from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Plane(StrEnum):
    DEVELOPMENT = "development"
    INSTITUTIONAL = "institutional"
    UNKNOWN = "unknown"


class MutationKind(StrEnum):
    CREATE_BRANCH = "create_branch"
    EDIT_FILE = "edit_file"
    COMMIT = "commit"
    RUN_TEST = "run_test"
    OPEN_PR = "open_pr"
    MERGE = "merge"
    GATE_PROMOTION = "gate_promotion"
    FOUNDER_ACTION = "founder_action"
    AUTHORITY_EXPANSION = "authority_expansion"
    SELF_PROMOTION = "self_promotion"
    SELF_ASSURANCE = "self_assurance"


@dataclass(frozen=True, slots=True)
class MutationDecision:
    allowed: bool
    reason: str
    plane: Plane
    kind: MutationKind

    @property
    def promotes(self) -> bool:
        return False


class AuthorityBoundary:
    """CODE_MUTATION != INSTITUTIONAL_PROMOTION.

    Unknown actor fails closed. Development writes do not require gate authority.
    """

    _DEV_ALLOW = frozenset(
        {
            MutationKind.CREATE_BRANCH,
            MutationKind.EDIT_FILE,
            MutationKind.COMMIT,
            MutationKind.RUN_TEST,
            MutationKind.OPEN_PR,
        }
    )
    _INST_DENY_WITHOUT_FOUNDER = frozenset(
        {
            MutationKind.MERGE,
            MutationKind.GATE_PROMOTION,
            MutationKind.FOUNDER_ACTION,
            MutationKind.AUTHORITY_EXPANSION,
            MutationKind.SELF_PROMOTION,
            MutationKind.SELF_ASSURANCE,
        }
    )

    def decide(self, *,
               actor: str,
               kind: MutationKind,
               founder_authorized: bool = False) -> MutationDecision:
        if not actor or actor.strip().upper() in {"UNKNOWN", ""}:
            return MutationDecision(False, "unknown_authority_fail_closed", Plane.UNKNOWN, kind)
        if kind in self._INST_DENY_WITHOUT_FOUNDER:
            if kind in {MutationKind.SELF_PROMOTION, MutationKind.SELF_ASSURANCE}:
                return MutationDecision(False, "self_effect_denied", Plane.INSTITUTIONAL, kind)
            if not founder_authorized:
                return MutationDecision(False, "institutional_mutation_denied", Plane.INSTITUTIONAL, kind)
            return MutationDecision(True, "founder_authorized_institutional", Plane.INSTITUTIONAL, kind)
        if kind in self._DEV_ALLOW:
            return MutationDecision(True, "authorized_development_mutation", Plane.DEVELOPMENT, kind)
        return MutationDecision(False, "unclassified_mutation_fail_closed", Plane.UNKNOWN, kind)


class DevelopmentPlane:
    def __init__(self, boundary: AuthorityBoundary | None = None) -> None:
        self._boundary = boundary or AuthorityBoundary()

    def authorize(self, actor: str, kind: MutationKind) -> MutationDecision:
        return self._boundary.decide(actor=actor, kind=kind, founder_authorized=False)


class InstitutionalControlPlane:
    def __init__(self, boundary: AuthorityBoundary | None = None) -> None:
        self._boundary = boundary or AuthorityBoundary()

    def authorize(self, actor: str, kind: MutationKind, *,
                  founder_authorized: bool = False) -> MutationDecision:
        return self._boundary.decide(
            actor=actor, kind=kind, founder_authorized=founder_authorized
        )
