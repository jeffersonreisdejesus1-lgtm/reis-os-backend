from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

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
    material: bool = False
    recursive_replayed: bool = False
    recursive_reason: str = ""


class CognitiveOperationalIntegration:
    def __init__(self, *,
                 boundary: AuthorityBoundary | None = None,
                 factory: SoftwareFactory | None = None,
                 engine: RecursiveEngine | None = None,
                 available_executors: frozenset[str] | None = None) -> None:
        self._boundary = boundary or AuthorityBoundary()
        self._factory = factory or SoftwareFactory(self._boundary)
        self._engine_injected = engine is not None
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
                force_readback_mismatch: bool = False,
                workdir: Path | None = None) -> CoiReceipt:
        def done(**kwargs) -> CoiReceipt:
            base = dict(
                intent=intent,
                identity=identity,
                bound_object=bound_object,
                executor=executor,
                plane_cognitive="intent",
                plane_control="authority",
                plane_material="factory+engine+plane",
                readback="",
                evidence_hash="",
                disposition=CoiDisposition.DENIED,
                promoted=False,
                failure=None,
                material=False,
                recursive_replayed=False,
                recursive_reason="",
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

        engine = self._engine
        if workdir is not None and not self._engine_injected:
            engine = RecursiveEngine(
                boundary=self._boundary, store_path=Path(workdir) / "recursive-runs.db"
            )

        factory = self._factory.run(
            actor=actor,
            mission_id=mission_id,
            spec=intent,
            executor=executor,
            workdir=workdir,
            bound_object=bound_object,
        )
        loop = engine.run(
            actor=actor, mission_id=mission_id, initial_state=bound_object, goal=intent[:12]
        )
        if factory.failure or loop.failure:
            return done(
                disposition=CoiDisposition.FAILED,
                failure=factory.failure or loop.failure,
                readback=factory.failure or loop.failure or "failed",
                material=factory.material,
                recursive_replayed=loop.replayed,
                recursive_reason=loop.termination_reason,
            )
        evidence = factory.evidence[-1].content_hash if factory.evidence else ""
        readback = (
            f"factory={factory.phase.value};loop={loop.termination_reason};"
            f"object={bound_object};artifact={factory.artifact_ref}"
        )
        if force_readback_mismatch:
            return done(
                disposition=CoiDisposition.HOLD,
                failure="readback_mismatch",
                readback=readback,
                evidence_hash=evidence,
                material=factory.material,
                recursive_replayed=loop.replayed,
                recursive_reason=loop.termination_reason,
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
            material=factory.material,
            recursive_replayed=loop.replayed,
            recursive_reason=loop.termination_reason,
        )
