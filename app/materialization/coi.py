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
    bound_object: str
    executor: str
    plane_cognitive: str
    plane_control: str
    plane_material: str
    readback: str
    evidence_hash: str
    disposition: CoiDisposition
    promoted: bool
    failure: str | None = None


class CognitiveOperationalIntegration:
    def __init__(self, *,
                 boundary: AuthorityBoundary | None = None,
                 factory: SoftwareFactory | None = None,
                 engine: RecursiveEngine | None = None,
                 available_executors: frozenset[str] | None = None) -> None:
        self._boundary = boundary or AuthorityBoundary()
        self._factory = factory or SoftwareFactory(self._boundary)
        self._engine = engine or RecursiveEngine(boundary=self._boundary)
        self._executors = available_executors or frozenset({"SOFIA"})

    def realize(self, *,
                actor: str,
                identity: str,
                intent: str,
                mission_id: str,
                bound_object: str = "",
                executor: str = "SOFIA",
                founder_authorized: bool = False,
                force_material_failure: bool = False,
                force_readback_mismatch: bool = False) -> CoiReceipt:
        def done(**kwargs) -> CoiReceipt:
            base = dict(
                intent=intent,
                identity=identity,
                bound_object=bound_object,
                executor=executor,
                plane_cognitive="intent",
                plane_control="authority",
                plane_material="factory+engine",
                readback="",
                evidence_hash="",
                disposition=CoiDisposition.DENIED,
                promoted=False,
                failure=None,
            )
            base.update(kwargs)
            return CoiReceipt(**base)

        if not identity.strip():
            return done(disposition=CoiDisposition.DENIED, failure="identity_binding_required")
        if not bound_object.strip():
            return done(disposition=CoiDisposition.HOLD, failure="missing_bound_object")
        if executor not in self._executors:
            return done(disposition=CoiDisposition.HOLD, failure="executor_unavailable")

        check = self._boundary.decide(
            actor=actor, kind=MutationKind.EDIT_FILE, founder_authorized=founder_authorized
        )
        if not check.allowed:
            return done(disposition=CoiDisposition.DENIED, failure=check.reason)

        if force_material_failure:
            return done(
                disposition=CoiDisposition.FAILED,
                failure="material_write_failed",
                readback="NO_CLAIM_OF_EXECUTION",
            )

        factory = self._factory.run(actor=actor, mission_id=mission_id, spec=intent, executor=executor)
        loop = self._engine.run(
            actor=actor, mission_id=mission_id, initial_state=bound_object, goal=intent[:12]
        )
        if factory.failure or loop.failure:
            return done(
                disposition=CoiDisposition.FAILED,
                failure=factory.failure or loop.failure,
                readback=factory.failure or loop.failure or "failed",
            )
        evidence = factory.evidence[-1].content_hash if factory.evidence else ""
        readback = f"factory={factory.phase.value};loop={loop.termination_reason};object={bound_object}"
        if force_readback_mismatch:
            return done(
                disposition=CoiDisposition.HOLD,
                failure="readback_mismatch",
                readback=readback,
                evidence_hash=evidence,
            )
        inst = self._boundary.decide(
            actor=actor, kind=MutationKind.GATE_PROMOTION, founder_authorized=founder_authorized
        )
        return done(
            disposition=CoiDisposition.CANDIDATE,
            promoted=inst.allowed,
            readback=readback,
            evidence_hash=evidence,
            failure=None,
        )
