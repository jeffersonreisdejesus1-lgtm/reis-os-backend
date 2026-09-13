from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.materialization.authority import AuthorityBoundary, MutationKind
from app.materialization.factory import SoftwareFactory
from app.materialization.recursive_engine import RecursiveEngine


class CoiDisposition(StrEnum):
    HOLD = "hold"
    CANDIDATE = "candidate"
    DENIED = "denied"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class CoiReceipt:
    intent: str
    identity: str
    executor: str
    readback: str
    evidence_hash: str
    disposition: CoiDisposition
    promoted: bool
    failure: str | None = None


class CognitiveOperationalIntegration:
    """COGNITIVE INTENT → bind → check → execute → readback → HOLD not promote."""

    def __init__(self, *,
                 boundary: AuthorityBoundary | None = None,
                 factory: SoftwareFactory | None = None,
                 engine: RecursiveEngine | None = None) -> None:
        self._boundary = boundary or AuthorityBoundary()
        self._factory = factory or SoftwareFactory(self._boundary)
        self._engine = engine or RecursiveEngine(boundary=self._boundary)

    def realize(self, *,
                actor: str,
                identity: str,
                intent: str,
                mission_id: str,
                founder_authorized: bool = False) -> CoiReceipt:
        if not identity.strip():
            return CoiReceipt(
                intent=intent,
                identity=identity,
                executor="",
                readback="",
                evidence_hash="",
                disposition=CoiDisposition.DENIED,
                promoted=False,
                failure="identity_binding_required",
            )
        check = self._boundary.decide(
            actor=actor,
            kind=MutationKind.EDIT_FILE,
            founder_authorized=founder_authorized,
        )
        if not check.allowed:
            return CoiReceipt(
                intent=intent,
                identity=identity,
                executor="",
                readback="",
                evidence_hash="",
                disposition=CoiDisposition.DENIED,
                promoted=False,
                failure=check.reason,
            )
        factory = self._factory.run(actor=actor, mission_id=mission_id, spec=intent)
        loop = self._engine.run(
            actor=actor, mission_id=mission_id, initial_state="idle", goal=intent[:12]
        )
        if factory.failure or loop.failure:
            return CoiReceipt(
                intent=intent,
                identity=identity,
                executor="SOFIA",
                readback=factory.failure or loop.failure or "failed",
                evidence_hash="",
                disposition=CoiDisposition.FAILED,
                promoted=False,
                failure=factory.failure or loop.failure,
            )
        evidence = factory.evidence[-1].content_hash if factory.evidence else ""
        inst = self._boundary.decide(
            actor=actor,
            kind=MutationKind.GATE_PROMOTION,
            founder_authorized=founder_authorized,
        )
        return CoiReceipt(
            intent=intent,
            identity=identity,
            executor="SOFIA",
            readback=f"factory={factory.phase.value};loop={loop.termination_reason}",
            evidence_hash=evidence,
            disposition=CoiDisposition.CANDIDATE,
            promoted=inst.allowed,
        )
