from __future__ import annotations

from dataclasses import dataclass

from app.noesis_r7.contracts import R7InvariantError

CANONICAL_NOESIS_IDI = "REISOS::INST::NOESIS::001"
CANONICAL_NOESIS_EC = "EC-NOESIS-007"
CANONICAL_L0_BINDING_HASH = "650ce1748e368055d79cf97db887f71976141f434afa589ae924e07fb7dc605f"
CANONICAL_R7_DERIVATION_REF = "NOESIS-R7-GOVERNOR-ROSTER-DERIVATION-001"
REQUIRED_LAYERS = (
    "R1_EXPLICIT_STATE_BLACKBOARD",
    "R2_PROGRESS_MONITOR",
    "R3_TYPED_TRANSITIONS",
    "R4_SCHEDULER",
    "R5_TELEMETRY",
    "R6_FORMAL_CHECKS",
)


@dataclass(frozen=True, slots=True)
class R7ArchitecturalReadiness:
    """Architectural gate for material Governor activation."""

    r7_i_taxonomy_frozen: bool = False
    r7_o_taxonomy_frozen: bool = False
    cross_taxonomy_complete: bool = False
    normalized_requirements_available: bool = False
    governor_derivation_valid: bool = False
    derivation_ref: str | None = None

    @property
    def governor_activation_allowed(self) -> bool:
        return all((
            self.r7_i_taxonomy_frozen,
            self.r7_o_taxonomy_frozen,
            self.cross_taxonomy_complete,
            self.normalized_requirements_available,
            self.governor_derivation_valid,
            self.derivation_ref == CANONICAL_R7_DERIVATION_REF,
        ))

    def assert_governor_activation_allowed(self) -> None:
        if not self.governor_activation_allowed:
            raise R7InvariantError("R7_GOVERNOR_ACTIVATION_BLOCKED_PENDING_DERIVATION")


@dataclass(frozen=True, slots=True)
class R1R6IntegrationContract:
    """R7 containment requirements plus separately tracked wiring evidence."""

    noesis_idi: str
    current_ec: str
    l0_binding_hash: str
    active_layers: tuple[str, ...]
    r1_persists_r7_state: bool
    r2_measures_r7_progress_and_effects: bool
    r3_types_r7_transitions: bool
    r4_schedules_r7_mechanisms: bool
    r5_observes_r7_and_global_chain: bool
    r6_constrains_r7_and_global_chain: bool
    r1_state_binding_ref: str | None = None
    r2_measurement_binding_ref: str | None = None
    r3_transition_binding_ref: str | None = None
    r4_scheduler_binding_ref: str | None = None
    r5_observation_binding_ref: str | None = None
    r6_constraint_binding_ref: str | None = None

    @classmethod
    def canonical(cls) -> "R1R6IntegrationContract":
        return cls(
            noesis_idi=CANONICAL_NOESIS_IDI,
            current_ec=CANONICAL_NOESIS_EC,
            l0_binding_hash=CANONICAL_L0_BINDING_HASH,
            active_layers=REQUIRED_LAYERS,
            r1_persists_r7_state=True,
            r2_measures_r7_progress_and_effects=True,
            r3_types_r7_transitions=True,
            r4_schedules_r7_mechanisms=True,
            r5_observes_r7_and_global_chain=True,
            r6_constrains_r7_and_global_chain=True,
        )

    def assert_base_compatible(self) -> None:
        if self.noesis_idi != CANONICAL_NOESIS_IDI:
            raise R7InvariantError("R7_NOESIS_IDENTITY_DRIFT")
        if self.current_ec != CANONICAL_NOESIS_EC:
            raise R7InvariantError("R7_EVOLUTION_CORE_DRIFT")
        if self.l0_binding_hash != CANONICAL_L0_BINDING_HASH:
            raise R7InvariantError("R7_L0_BINDING_DRIFT")
        if self.active_layers != REQUIRED_LAYERS:
            raise R7InvariantError("R7_REQUIRES_EXACT_CANONICAL_R1_R6")
        required_relations = (
            self.r1_persists_r7_state,
            self.r2_measures_r7_progress_and_effects,
            self.r3_types_r7_transitions,
            self.r4_schedules_r7_mechanisms,
            self.r5_observes_r7_and_global_chain,
            self.r6_constrains_r7_and_global_chain,
        )
        if not all(required_relations):
            raise R7InvariantError("R7_REQUIRES_COMPLETE_R1_R6_CAUSAL_CONTAINMENT")

    @property
    def full_r7_integration_proven(self) -> bool:
        refs = (
            self.r1_state_binding_ref,
            self.r2_measurement_binding_ref,
            self.r3_transition_binding_ref,
            self.r4_scheduler_binding_ref,
            self.r5_observation_binding_ref,
            self.r6_constraint_binding_ref,
        )
        return all(bool(ref) for ref in refs)

    def assert_complete_r7_integration(self) -> None:
        self.assert_base_compatible()
        if not self.full_r7_integration_proven:
            raise R7InvariantError("R7_R1_R6_WIRING_EVIDENCE_INCOMPLETE")

    def assert_compatible(self) -> None:
        # Runtime compatibility is intentionally stricter than architectural presence:
        # R7 must fail closed unless all six material R1-R6 binding refs are present.
        self.assert_complete_r7_integration()

    @property
    def scheduler_is_authority(self) -> bool:
        return False

    @property
    def governance_may_mutate_l0(self) -> bool:
        return False
