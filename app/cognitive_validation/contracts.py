from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CognitiveClaim(str, Enum):
    EXPERIENCE = "experience"
    MEMORY = "memory"
    LEARNING = "learning"
    PLASTICITY = "plasticity"
    SELF_REGULATION = "self_regulation"
    METACOGNITION = "metacognition"
    IDENTITY = "identity"
    COGNITIVE_POLICY = "cognitive_policy"
    IMPROVEMENT = "improvement"
    REGRESSION = "regression"
    STALE_COGNITIVE_STATE = "stale_cognitive_state"


@dataclass(frozen=True)
class CognitiveValidationContract:
    learning_may_expand_authority: bool = False
    memory_write_creates_canonical_fact: bool = False
    adaptation_may_rewrite_constitution: bool = False
    model_output_is_verified_experience: bool = False
    unverified_feedback_quarantined: bool = True
    stale_generation_commit_denied: bool = True

    def validate(self) -> tuple[bool, tuple[str, ...]]:
        violations: list[str] = []
        if self.learning_may_expand_authority:
            violations.append("LEARNING != AUTHORITY_EXPANSION")
        if self.memory_write_creates_canonical_fact:
            violations.append("MEMORY_WRITE != CANONICAL_FACT_CREATION")
        if self.adaptation_may_rewrite_constitution:
            violations.append("ADAPTATION != CONSTITUTION_REWRITE")
        if self.model_output_is_verified_experience:
            violations.append("MODEL_OUTPUT != VERIFIED_EXPERIENCE")
        if not self.unverified_feedback_quarantined:
            violations.append("UNVERIFIED_FEEDBACK -> QUARANTINE")
        if not self.stale_generation_commit_denied:
            violations.append("STALE_GENERATION -> COGNITIVE_COMMIT_DENIED")
        return (not violations, tuple(violations))


AB0_REQUIRED_DEFINITIONS: tuple[CognitiveClaim, ...] = tuple(CognitiveClaim)


def canonical_ab0_contract() -> CognitiveValidationContract:
    return CognitiveValidationContract()
