from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from experiments.noesis_layered_refactor.layered import (
    Blackboard,
    FormalChecks,
    PhysiologicalScheduler,
    ProgressMonitor,
    RelationType,
    TelemetryLedger,
    TypedTransition,
)

from app.noesis_r7.integration import R1R6IntegrationContract

BINDING_REFS = {
    "R1": "app/noesis_r7/physiology_bindings.py::R7PhysiologyBridge.persist_r7_state",
    "R2": "app/noesis_r7/physiology_bindings.py::R7PhysiologyBridge.measure_r7_effects",
    "R3": "app/noesis_r7/physiology_bindings.py::R7PhysiologyBridge.type_r7_transition",
    "R4": "app/noesis_r7/physiology_bindings.py::R7PhysiologyBridge.schedule_r7_mechanism",
    "R5": "app/noesis_r7/physiology_bindings.py::R7PhysiologyBridge.observe_r7",
    "R6": "app/noesis_r7/physiology_bindings.py::R7PhysiologyBridge.constrain_r7",
}


@dataclass(slots=True)
class R7PhysiologyBridge:
    """Material adapter from candidate R7 mechanics into canonical R1-R6 physiology.

    This bridge does not activate Governors and does not grant authority. It binds R7
    state/transition/scheduling/telemetry/check semantics to the promoted physiology.
    """

    board: Blackboard
    progress: ProgressMonitor
    scheduler: PhysiologicalScheduler
    telemetry: TelemetryLedger

    @classmethod
    def for_mission(cls, mission_id: str, object_id: str) -> "R7PhysiologyBridge":
        return cls(
            board=Blackboard(mission_id=mission_id, current_object=object_id),
            progress=ProgressMonitor(),
            scheduler=PhysiologicalScheduler(),
            telemetry=TelemetryLedger(),
        )

    def persist_r7_state(self, state: dict[str, Any], *, state_version: int) -> None:
        self.board.last_material_delta = {"r7_state": dict(state), "r7_state_version": state_version}
        ref = f"R7_STATE_VERSION:{state_version}"
        if ref not in self.board.evidence_refs:
            self.board.evidence_refs.append(ref)

    def measure_r7_effects(self, before: Blackboard, after: Blackboard):
        return self.progress.measure(before, after)

    def type_r7_transition(self, *, governor_id: str, relation: RelationType, reason: str) -> TypedTransition:
        return TypedTransition(
            source=governor_id,
            relation=relation,
            target="NOESIS_R7",
            object_id=self.board.current_object,
            reason=reason,
            authority_transferred=False,
        )

    def schedule_r7_mechanism(self):
        return self.scheduler.decide(self.board)

    def observe_r7(self, *, action: str, reason: str, material_delta: dict[str, Any], gate: str | None = None):
        return self.telemetry.append(
            cycle=self.board.cycle,
            actor="NOESIS_R7",
            state_before=self.board.current_phase,
            action=action,
            reason=reason,
            material_delta=material_delta,
            gate=gate,
            state_after=self.board.current_phase,
        )

    def constrain_r7(self, *, l0: Any) -> bool:
        return FormalChecks.assert_all(
            l0=l0,
            board=self.board,
            scheduler=self.scheduler.decide(self.board),
            telemetry=self.telemetry,
        )


def materialized_integration_contract() -> R1R6IntegrationContract:
    base = R1R6IntegrationContract.canonical()
    return R1R6IntegrationContract(
        noesis_idi=base.noesis_idi,
        current_ec=base.current_ec,
        l0_binding_hash=base.l0_binding_hash,
        active_layers=base.active_layers,
        r1_persists_r7_state=True,
        r2_measures_r7_progress_and_effects=True,
        r3_types_r7_transitions=True,
        r4_schedules_r7_mechanisms=True,
        r5_observes_r7_and_global_chain=True,
        r6_constrains_r7_and_global_chain=True,
        r1_state_binding_ref=BINDING_REFS["R1"],
        r2_measurement_binding_ref=BINDING_REFS["R2"],
        r3_transition_binding_ref=BINDING_REFS["R3"],
        r4_scheduler_binding_ref=BINDING_REFS["R4"],
        r5_observation_binding_ref=BINDING_REFS["R5"],
        r6_constraint_binding_ref=BINDING_REFS["R6"],
    )
