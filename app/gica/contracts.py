from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


CANONICAL_OCS_ROSTER = (
    "NÓESIS",
    "DÉDALA",
    "SÝNESIS",
    "ÍRIS",
    "LYRA",
    "SOFIA",
    "MÊTIS",
    "ÁGORA",
    "AURI",
    "SYNERGEIA",
    "TÊMIS",
)


class GicaGate(str, Enum):
    GA0 = "GA0_BOOTSTRAP"
    GA1 = "GA1_SPECIFICATION_CONSISTENCY"
    GA2 = "GA2_INDEPENDENT_ARCHITECTURAL_ASSURANCE"
    GA3 = "GA3_IMPLEMENTATION_CONTRACT"
    GA4 = "GA4_REFERENCE_IMPLEMENTATION"
    GA5 = "GA5_DETERMINISTIC_QUALIFICATION"
    GA6 = "GA6_CONCURRENCY_FAULT_QUALIFICATION"
    GA7 = "GA7_DISCOVERY_PILOT"
    GA8 = "GA8_EXPERIMENTAL_FREEZE"
    GA9 = "GA9_PAIRED_RANDOMIZED_QUALIFICATION"
    GA10 = "GA10_ADVERSARIAL_DISTRIBUTION_SHIFT"
    GA11 = "GA11_FINAL_INDEPENDENT_ASSURANCE"
    GA12 = "GA12_FINAL_FOUNDER_GATE"


class GicaProgramState(str, Enum):
    ACTIVE = "ACTIVE"
    HOLD = "HOLD"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    ABORTED_CANDIDATE = "ABORTED_CANDIDATE"
    EMERGENCY_CONTAINMENT = "EMERGENCY_CONTAINMENT"
    READY_FOR_FOUNDER = "READY_FOR_FOUNDER"
    COMPLETE = "COMPLETE"


class ProgramTransitionError(RuntimeError):
    pass


_NEXT_GATE = {
    GicaGate.GA0: GicaGate.GA1,
    GicaGate.GA1: GicaGate.GA2,
    GicaGate.GA2: GicaGate.GA3,
    GicaGate.GA3: GicaGate.GA4,
    GicaGate.GA4: GicaGate.GA5,
    GicaGate.GA5: GicaGate.GA6,
    GicaGate.GA6: GicaGate.GA7,
    GicaGate.GA7: GicaGate.GA8,
    GicaGate.GA8: GicaGate.GA9,
    GicaGate.GA9: GicaGate.GA10,
    GicaGate.GA10: GicaGate.GA11,
    GicaGate.GA11: GicaGate.GA12,
}


@dataclass(frozen=True)
class GicaProgramContract:
    program_id: str
    gate: GicaGate
    state: GicaProgramState = GicaProgramState.ACTIVE
    authority_bound: bool = False
    evidence_complete: bool = False
    independent_assurance_pass: bool = False
    founder_authorized: bool = False

    def validate_roster(self) -> None:
        if len(CANONICAL_OCS_ROSTER) != 11:
            raise ProgramTransitionError("canonical_11_ocs_roster_required")
        if len(set(CANONICAL_OCS_ROSTER)) != 11:
            raise ProgramTransitionError("ocs_identity_uniqueness_required")

    def transition_to(self, target: GicaGate) -> "GicaProgramContract":
        self.validate_roster()
        if self.state is not GicaProgramState.ACTIVE:
            raise ProgramTransitionError("program_not_in_active_state")
        expected = _NEXT_GATE.get(self.gate)
        if expected is None or target is not expected:
            raise ProgramTransitionError("non_sequential_gate_transition_denied")
        if not self.authority_bound:
            raise ProgramTransitionError("valid_authority_required")
        if not self.evidence_complete:
            raise ProgramTransitionError("gate_evidence_required")
        if target is GicaGate.GA12 and not self.independent_assurance_pass:
            raise ProgramTransitionError("independent_assurance_pass_required")
        return GicaProgramContract(
            program_id=self.program_id,
            gate=target,
            state=(
                GicaProgramState.READY_FOR_FOUNDER
                if target is GicaGate.GA12
                else GicaProgramState.ACTIVE
            ),
            authority_bound=self.authority_bound,
            evidence_complete=False,
            independent_assurance_pass=self.independent_assurance_pass,
            founder_authorized=False,
        )

    def founder_promote(self) -> "GicaProgramContract":
        if self.gate is not GicaGate.GA12:
            raise ProgramTransitionError("founder_promotion_outside_ga12_denied")
        if self.state is not GicaProgramState.READY_FOR_FOUNDER:
            raise ProgramTransitionError("program_not_ready_for_founder")
        if not self.independent_assurance_pass:
            raise ProgramTransitionError("independent_assurance_pass_required")
        if not self.founder_authorized:
            raise ProgramTransitionError("explicit_founder_authorization_required")
        return GicaProgramContract(
            program_id=self.program_id,
            gate=self.gate,
            state=GicaProgramState.COMPLETE,
            authority_bound=self.authority_bound,
            evidence_complete=self.evidence_complete,
            independent_assurance_pass=True,
            founder_authorized=True,
        )
