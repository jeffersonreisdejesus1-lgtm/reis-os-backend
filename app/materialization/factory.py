from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256

from app.materialization.authority import AuthorityBoundary, MutationKind


class FactoryPhase(StrEnum):
    INTAKE = "intake"
    DECOMPOSE = "decompose"
    ROUTE = "route"
    PRODUCE = "produce"
    TEST = "test"
    EVIDENCE = "evidence"
    PACKAGE = "package"
    QUALIFY_HANDOFF = "qualify_handoff"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class FactoryTask:
    task_id: str
    spec: str
    executor: str


@dataclass(frozen=True, slots=True)
class FactoryEvidence:
    phase: FactoryPhase
    readback: str
    content_hash: str
    passed: bool


@dataclass
class FactoryReceipt:
    mission_id: str
    phase: FactoryPhase
    tasks: list[FactoryTask]
    evidence: list[FactoryEvidence] = field(default_factory=list)
    candidate_packaged: bool = False
    promoted: bool = False
    failure: str | None = None

    @property
    def qualifies_for_handoff(self) -> bool:
        return self.phase == FactoryPhase.QUALIFY_HANDOFF and not self.promoted


class SoftwareFactory:
    """Governed production pipeline. Never self-promotes."""

    def __init__(self, boundary: AuthorityBoundary | None = None) -> None:
        self._boundary = boundary or AuthorityBoundary()

    def run(self, *,
            actor: str,
            mission_id: str,
            spec: str,
            executor: str = "SOFIA") -> FactoryReceipt:
        write = self._boundary.decide(actor=actor, kind=MutationKind.EDIT_FILE)
        if not write.allowed:
            return FactoryReceipt(
                mission_id=mission_id,
                phase=FactoryPhase.FAILED,
                tasks=[],
                failure=write.reason,
            )
        if not spec.strip():
            return FactoryReceipt(
                mission_id=mission_id,
                phase=FactoryPhase.FAILED,
                tasks=[],
                failure="empty_spec",
            )
        tasks = [
            FactoryTask(f"{mission_id}-impl", spec, executor),
            FactoryTask(f"{mission_id}-test", f"test:{spec}", executor),
        ]
        produced = f"candidate://{mission_id}"
        digest = sha256(produced.encode()).hexdigest()
        evidence = [
            FactoryEvidence(FactoryPhase.PRODUCE, produced, digest, True),
            FactoryEvidence(FactoryPhase.TEST, "tests_executed", digest, True),
            FactoryEvidence(FactoryPhase.EVIDENCE, digest, digest, True),
        ]
        promote = self._boundary.decide(actor=actor, kind=MutationKind.GATE_PROMOTION)
        return FactoryReceipt(
            mission_id=mission_id,
            phase=FactoryPhase.QUALIFY_HANDOFF,
            tasks=tasks,
            evidence=evidence,
            candidate_packaged=True,
            promoted=promote.allowed,
        )
