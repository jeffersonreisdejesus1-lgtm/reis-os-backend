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
class R1R6IntegrationContract:
    """Fail-closed compatibility binding for R7 over canonical R1-R6."""

    noesis_idi: str
    current_ec: str
    l0_binding_hash: str
    active_layers: tuple[str, ...]

    @classmethod
    def canonical(cls) -> "R1R6IntegrationContract":
        return cls(
            noesis_idi=CANONICAL_NOESIS_IDI,
            current_ec=CANONICAL_NOESIS_EC,
            l0_binding_hash=CANONICAL_L0_BINDING_HASH,
            active_layers=REQUIRED_LAYERS,
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

    @property
    def scheduler_is_authority(self) -> bool:
        return False

    @property
    def governance_may_mutate_l0(self) -> bool:
        return False
