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
    """Architectural gate for material Governor activation."""

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
    """Base physiology identity plus explicit evidence refs for R7 wiring.

    `canonical()` proves only that the promoted R1-R6 physiology identity is the
    expected one. It intentionally does NOT claim the R1-R6 <-> R7 causal wiring is
    complete. Each relation must later be backed by a concrete implementation/evidence
    reference after Governor derivation defines the R7 state and transition surfaces.
    """

    noesis_idi: str
    current_ec: str
    l0_binding_hash: str
    active_layers: tuple[str, ...]
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
            raise R7InvariantError("R7_REQUIRES_COMPLETE_R1_R6_CAUSAL_CONTAINMENT")

    # Compatibility alias for callers whose intent is only base physiology validation.
    def assert_compatible(self) -> None:
        self.assert_base_compatible()

    @property
    def scheduler_is_authority(self) -> bool:
        return False

    @property
    def governance_may_mutate_l0(self) -> bool:
        return False
