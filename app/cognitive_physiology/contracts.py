from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping


class EvidenceClass(str, Enum):
    ARCHITECTURAL = "ARCHITECTURAL"
    MATERIAL_IMPLEMENTATION = "MATERIAL_IMPLEMENTATION"
    RUNTIME_CAUSAL = "RUNTIME_CAUSAL"


class EpistemicGrade(str, Enum):
    FACT = "FACT"
    HYPOTHESIS = "HYPOTHESIS"
    PREDICTION = "PREDICTION"
    ACTION_PROPOSAL = "ACTION_PROPOSAL"


class MemoryLevel(str, Enum):
    M0 = "M0_TRANSIENT"
    M1 = "M1_WORKING"
    M2 = "M2_EPISODIC"
    M3 = "M3_SEMANTIC_PROCEDURAL"


@dataclass(frozen=True)
class BudgetEnvelope:
    max_cycles: int = 32
    max_model_calls: int = 8
    max_tool_calls: int = 8
    max_tokens: int = 32_000
    max_active_populations: int = 8
    max_recursive_depth: int = 4
    max_retrievals: int = 16
    max_simulations: int = 8
    max_wall_ms: int = 30_000

    def validate(self) -> None:
        for name, value in self.__dict__.items():
            if value <= 0:
                raise ValueError(f"budget_must_be_positive:{name}")


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    source_ocs: str
    content: str
    epistemic_grade: EpistemicGrade
    confidence: float
    uncertainty: float
    salience: float
    novelty: float
    risk: float
    evidence_refs: tuple[str, ...] = ()
    ttl_cycles: int = 1

    def validate(self) -> None:
        if not self.candidate_id or not self.source_ocs:
            raise ValueError("candidate_identity_required")
        if self.ttl_cycles <= 0:
            raise ValueError("candidate_ttl_required")
        for field_name in ("confidence", "uncertainty", "salience", "novelty", "risk"):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"candidate_field_out_of_range:{field_name}")


@dataclass(frozen=True)
class PredictionResidual:
    semantic: float = 0.0
    goal: float = 0.0
    causal: float = 0.0
    temporal: float = 0.0
    calibration: float = 0.0
    risk: float = 0.0
    tool_behavior: float = 0.0
    environment: float = 0.0

    def as_mapping(self) -> Mapping[str, float]:
        return {
            "semantic": self.semantic,
            "goal": self.goal,
            "causal": self.causal,
            "temporal": self.temporal,
            "calibration": self.calibration,
            "risk": self.risk,
            "tool_behavior": self.tool_behavior,
            "environment": self.environment,
        }


@dataclass(frozen=True)
class NMState:
    salience: float = 0.0
    novelty: float = 0.0
    uncertainty: float = 0.0
    confidence: float = 0.0
    risk: float = 0.0
    prediction_error: float = 0.0
    cognitive_load: float = 0.0
    exploration_drive: float = 0.0
    exploitation_drive: float = 0.0
    urgency: float = 0.0
    resource_pressure: float = 0.0

    def validate(self) -> None:
        for name, value in self.__dict__.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"nm_field_out_of_range:{name}")


@dataclass(frozen=True)
class OperationalCommitContext:
    r6_clear: bool
    authority_bound: bool
    capability_bound: bool
    execution_budget_available: bool
    state_generation_current: bool

    @property
    def allowed(self) -> bool:
        return all(
            (
                self.r6_clear,
                self.authority_bound,
                self.capability_bound,
                self.execution_budget_available,
                self.state_generation_current,
            )
        )


@dataclass(frozen=True)
class HandoffEnvelope:
    handoff_id: str
    contract_version: str
    mission_id: str
    source_ocs: str
    target_ocs: str
    source_identity_ref: str
    target_identity_ref: str
    source_generation: int
    target_expected_generation: int
    authority_ref: str
    authority_resolution_status: str
    capability_ref: str
    capability_resolution_status: str
    current_gate: str
    requested_action: str
    allowed_actions: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    assurance_context: str
    expected_output: str
    acceptance_contract: str
    state_hash: str
    expires_at: datetime
    ttl_seconds: int
    artifact_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    unresolved_findings: tuple[str, ...] = ()
    rollback_ref: str = ""

    def validate_for_target(self, *, target_generation: int, now: datetime | None = None) -> None:
        now = now or datetime.now(timezone.utc)
        if self.source_generation < 0 or self.target_expected_generation < 0:
            raise ValueError("generation_must_be_non_negative")
        if self.target_expected_generation != target_generation:
            raise PermissionError("generation_mismatch")
        if self.authority_resolution_status != "RESOLVED":
            raise PermissionError("authority_unresolved")
        if self.capability_resolution_status != "RESOLVED":
            raise PermissionError("capability_unresolved")
        if self.ttl_seconds <= 0:
            raise PermissionError("invalid_handoff_ttl")
        if self.expires_at.tzinfo is None:
            raise ValueError("handoff_expiry_must_be_timezone_aware")
        if now >= self.expires_at:
            raise PermissionError("stale_handoff")
        if not self.authority_ref or not self.capability_ref:
            raise PermissionError("authority_or_capability_reference_missing")


@dataclass(frozen=True)
class MemoryRecord:
    record_id: str
    ocs_id: str
    level: MemoryLevel
    generation: int
    provenance_ref: str
    mission_id: str
    payload: Mapping[str, object] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.record_id or not self.ocs_id or not self.provenance_ref or not self.mission_id:
            raise ValueError("memory_record_identity_and_provenance_required")
        if self.generation < 0:
            raise ValueError("memory_generation_must_be_non_negative")


def validate_memory_promotion(source: MemoryLevel, target: MemoryLevel, *, qualified: bool) -> None:
    if source == MemoryLevel.M2 and target == MemoryLevel.M3 and not qualified:
        raise PermissionError("m2_to_m3_direct_forbidden")
    if target not in MemoryLevel:
        raise ValueError("unknown_memory_level")
