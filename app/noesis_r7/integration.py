from __future__ import annotations

from dataclasses import dataclass

from app.noesis_r7.contracts import R7InvariantError


CANONICAL_NOESIS_IDI = "REISOS::INST::NOESIS::001"
CANONICAL_NOESIS_EC = "EC-NOESIS-007"
CANONICAL_L0_BINDING_HASH = (
    "650ce1748e368055d79cf97db887f71976141f434afa589ae924e07fb7dc605f"
)
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
    """Architectural gate for material Governor activation.

    The generic runtime may exist before these facts are true, but no Governor may be
    registered into an effective runtime until Nóesis supplies a valid derivation chain.
    """

    r7_i_taxonomy_frozen: bool = False
    r7_o_taxonomy_frozen: bool = False
    cross_taxonomy_complete: bool = False
    normalized_requirements_available: bool = False
    governor_derivation_valid: bool = False
    derivation_ref: str | None = None

    @property
    def governor_activation_allowed(self) -> bool:
        return all(
            (
                self.r7_i_taxonomy_frozen,
                self.r7_o_taxonomy_frozen,
                self.cross_taxonomy_complete,
                self.normalized_requirements_available,
                self.governor_derivation_valid,
                bool(self.derivation_ref),
            )
        )

    def assert_governor_activation_allowed(self) -> None:
        if not self.governor_activation_allowed:
            raise R7InvariantError("R7_GOVERNOR_ACTIVATION_BLOCKED_PENDING_DERIVATION")


@dataclass(frozen=True, slots=True)
class R1R6IntegrationContract:
    """Fail-closed physiological containment contract for R7."""

    noesis_idi: str
    current_ec: str
    l0_binding_hash: str
    active_layers: tuple[str, ...]

    # These are required semantic relations, not evidence that deployment is complete.
    r1_persists_r7_state: bool
    r2_measures_r7_progress_and_effects: bool
    r3_types_r7_transitions: bool
    r4_schedules_r7_mechanisms: bool
    r5_observes_r7_and_global_chain: bool
    r6_constrains_r7_and_global_chain: bool

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

    def assert_compatible(self) -> None:
        if self.noesis_idi != CANONICAL_NOESIS_IDI:
            raise R7InvariantError("R7_NOESIS_IDENTITY_DRIFT")
        if self.current_ec != CANONICAL_NOESIS_EC:
            raise R7InvariantError("R7_EVOLUTION_CORE_DRIFT")
        if self.l0_binding_hash != CANONICAL_L0_BINDING_HASH:
            raise R7InvariantError("R7_L0_BINDING_DRIFT")
        if self.active_layers != REQUIRED_LAYERS:
            raise R7InvariantError("R7_REQUIRES_EXACT_CANONICAL_R1_R6")

        relations = (
            self.r1_persists_r7_state,
            self.r2_measures_r7_progress_and_effects,
            self.r3_types_r7_transitions,
            self.r4_schedules_r7_mechanisms,
            self.r5_observes_r7_and_global_chain,
            self.r6_constrains_r7_and_global_chain,
        )
        if not all(relations):
            raise R7InvariantError("R7_REQUIRES_COMPLETE_R1_R6_CAUSAL_CONTAINMENT")

    @property
    def scheduler_is_authority(self) -> bool:
        return False

    @property
    def governance_may_mutate_l0(self) -> bool:
        return False
