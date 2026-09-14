from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

from app.materialization.authority import AuthorityBoundary, MutationKind
from app.materialization.material_plane import (
    DurableEffectStore,
    FilesystemMaterialProvider,
    MaterialExecutionRequest,
    MaterialPlane,
    Outcome,
)


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
    HOLD = "hold"


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
    material: bool = False
    artifact_ref: str = ""

    @property
    def qualifies_for_handoff(self) -> bool:
        return self.phase == FactoryPhase.QUALIFY_HANDOFF and not self.promoted


class SoftwareFactory:
    def __init__(self, boundary: AuthorityBoundary | None = None) -> None:
        self._boundary = boundary or AuthorityBoundary()

    def run(self, *,
            actor: str,
            mission_id: str,
            spec: str,
            executor: str = "SOFIA",
            workdir: Path | None = None) -> FactoryReceipt:
        write = self._boundary.decide(actor=actor, kind=MutationKind.EDIT_FILE)
        if not write.allowed:
            return FactoryReceipt(mission_id, FactoryPhase.FAILED, [], failure=write.reason)
        if not spec.strip():
            return FactoryReceipt(mission_id, FactoryPhase.FAILED, [], failure="empty_spec")
        tasks = [
            FactoryTask(f"{mission_id}-impl", spec, executor),
            FactoryTask(f"{mission_id}-test", f"test:{spec}", executor),
        ]
        if workdir is None:
            # NON_MATERIAL compatibility path. candidate:// is not a material artifact.
            produced = f"candidate://{mission_id}"
            digest = sha256(produced.encode()).hexdigest()
            evidence = [
                FactoryEvidence(FactoryPhase.PRODUCE, produced, digest, False),
                FactoryEvidence(FactoryPhase.TEST, "tests_not_executed", digest, False),
                FactoryEvidence(FactoryPhase.EVIDENCE, digest, digest, False),
            ]
            return FactoryReceipt(
                mission_id, FactoryPhase.QUALIFY_HANDOFF, tasks, evidence,
                candidate_packaged=True, promoted=False, material=False,
            )
        plane = MaterialPlane(
            store=DurableEffectStore(Path(workdir) / "factory-effects.db"),
            provider=FilesystemMaterialProvider(Path(workdir) / "factory-fx"),
            boundary=self._boundary,
        )
        request = MaterialExecutionRequest(
            mission_id=mission_id,
            logical_operation_id=f"{mission_id}-factory",
            effect_id=f"factory-{mission_id}",
            program_id="REIS-OS-AUTONOMOUS-MATERIALIZATION-CLOSURE-001",
            actor=actor,
            bound_object=f"object://factory/{mission_id}",
            expected_object_version="v0",
            capability="fixture_write",
            authorized_intent_hash=sha256(spec.encode()).hexdigest(),
            payload=spec,
            authority_ref="authority://dev",
        )
        executed = plane.execute(request)
        if executed.outcome is Outcome.SUCCEEDED and executed.material:
            evidence = [
                FactoryEvidence(FactoryPhase.PRODUCE, executed.material_artifact_ref, executed.execution_hash, True),
                FactoryEvidence(FactoryPhase.TEST, executed.test_execution_ref, executed.execution_hash, True),
                FactoryEvidence(FactoryPhase.EVIDENCE, executed.execution_hash, executed.execution_hash, True),
            ]
            return FactoryReceipt(
                mission_id, FactoryPhase.QUALIFY_HANDOFF, tasks, evidence,
                candidate_packaged=False, promoted=False, material=True,
                artifact_ref=executed.material_artifact_ref,
            )
        phase = FactoryPhase.HOLD if executed.state.value == "HOLD" else FactoryPhase.FAILED
        return FactoryReceipt(
            mission_id, phase, tasks, failure=executed.failure or executed.outcome.value,
            material=executed.material, artifact_ref=executed.material_artifact_ref,
        )
