from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.noesis_r7.contracts import R7InvariantError

DERIVATION_REF = "NOESIS-R7-GOVERNOR-ROSTER-DERIVATION-001"


class GovernorDomain(str, Enum):
    INTERNAL = "R7-I"
    OUTER = "R7-O"


@dataclass(frozen=True, slots=True)
class DerivedGovernorSpec:
    ordinal: str
    governor_id: str
    name: str
    domain: GovernorDomain
    requirement_refs: tuple[str, ...]
    boundaries: tuple[str, ...] = ()


DERIVED_GOVERNOR_ROSTER: tuple[DerivedGovernorSpec, ...] = (
    DerivedGovernorSpec("G-I01", "A-CTX", "CONTEXT_AND_PERCEPTION_GOVERNOR", GovernorDomain.INTERNAL, ("NGR-01",), ("A-CTX != OG-INTAKE",)),
    DerivedGovernorSpec("G-I02", "A-CG", "COGNITIVE_COMPOSITION_GOVERNOR", GovernorDomain.INTERNAL, ("NGR-02",), ("A-CG != NOESIS", "A-CG != AUTHORITY")),
    DerivedGovernorSpec("G-I03", "A-MEM-WORKING", "WORKING_MEMORY_GOVERNOR", GovernorDomain.INTERNAL, ("NGR-03",)),
    DerivedGovernorSpec("G-I04", "A-MEM-DURABLE", "DURABLE_MEMORY_GOVERNOR", GovernorDomain.INTERNAL, ("NGR-03",)),
    DerivedGovernorSpec("G-I05", "A-DTRUST", "DECISION_TRUST_GOVERNOR", GovernorDomain.INTERNAL, ("NGR-04",), ("TRUST != AUTHORITY",)),
    DerivedGovernorSpec("G-I06", "A-EVID", "EVIDENCE_EPISTEMIC_GOVERNOR", GovernorDomain.INTERNAL, ("NGR-05",), ("A-EVID != INDEPENDENT_ASSURANCE",)),
    DerivedGovernorSpec("G-I07", "A-LEARN", "LEARNING_PLASTICITY_GOVERNOR", GovernorDomain.INTERNAL, ("NGR-06",), ("LEARNING != PROMOTION",)),
    DerivedGovernorSpec("G-I08", "A-HOME", "HOMEOSTASIS_RESOURCE_GOVERNOR", GovernorDomain.INTERNAL, ("NGR-07",)),
    DerivedGovernorSpec("G-I09", "A-RECOVERY", "RECOVERY_CONTINUITY_GOVERNOR", GovernorDomain.INTERNAL, ("NGR-08",)),
    DerivedGovernorSpec("G-I10", "A-PI-ORCH", "INTERNAL_GOVERNOR_COORDINATION_GOVERNOR", GovernorDomain.INTERNAL, ("NGR-15",), ("R4 > A-PI-ORCH", "A-PI-ORCH != R4_AGENT", "A-PI-ORCH != NOESIS")),
    DerivedGovernorSpec("G-O01", "OG-INTAKE", "INSTITUTIONAL_INTAKE_GOVERNOR", GovernorDomain.OUTER, ("NGR-09",)),
    DerivedGovernorSpec("G-O02", "OG-ORCH-ROUTE", "INSTITUTIONAL_ORCHESTRATION_AND_ROUTING_GOVERNOR", GovernorDomain.OUTER, ("NGR-10",), ("OG-ORCH-ROUTE != NOESIS", "OG-ORCH-ROUTE != R4", "OG-ORCH-ROUTE != AUTHORITY_SOURCE")),
    DerivedGovernorSpec("G-O03", "OG-HANDOFF", "HANDOFF_GOVERNOR", GovernorDomain.OUTER, ("NGR-11",), ("HANDOFF != IDENTITY_TRANSFER", "HANDOFF != AUTHORITY_TRANSFER")),
    DerivedGovernorSpec("G-O04", "OG-PROGRAM-STATE", "PROGRAM_STATE_GOVERNOR", GovernorDomain.OUTER, ("NGR-12",), ("PROGRAM_STATE != COGNITIVE_MEMORY",)),
    DerivedGovernorSpec("G-O05", "OG-EVOLUTION", "EVOLUTION_GOVERNANCE_GOVERNOR", GovernorDomain.OUTER, ("NGR-13",), ("EVOLUTION_GOVERNANCE != CANONICAL_PROMOTION",)),
    DerivedGovernorSpec("G-O06", "OG-AUTH", "AUTHORITY_AND_SCOPE_GOVERNOR", GovernorDomain.OUTER, ("NGR-14A",), ("OG-AUTH != AUTHORITY_SOURCE", "OG-AUTH != AUTHORITY_CREATION")),
    DerivedGovernorSpec("G-O07", "OG-RUNTIME", "RUNTIME_GOVERNANCE_GOVERNOR", GovernorDomain.OUTER, ("NGR-14B",)),
)

DERIVED_GOVERNOR_IDS = frozenset(spec.governor_id for spec in DERIVED_GOVERNOR_ROSTER)


def assert_derived_governor(governor_id: str, *, derivation_ref: str) -> None:
    if derivation_ref != DERIVATION_REF:
        raise R7InvariantError("R7_GOVERNOR_DERIVATION_REF_MISMATCH")
    if governor_id not in DERIVED_GOVERNOR_IDS:
        raise R7InvariantError("R7_GOVERNOR_NOT_IN_DERIVED_ROSTER")
