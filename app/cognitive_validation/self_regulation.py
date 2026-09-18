from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RegulatoryAction(str, Enum):
    PROCEED = "PROCEED"
    DEFER = "DEFER"
    SEEK_EVIDENCE = "SEEK_EVIDENCE"
    INCREASE_REVIEW_DEPTH = "INCREASE_REVIEW_DEPTH"
    REDUCE_ACTION_SCOPE = "REDUCE_ACTION_SCOPE"
    ENTER_HOLD = "ENTER_HOLD"
    REQUEST_SPECIALIST_OCS = "REQUEST_SPECIALIST_OCS"


@dataclass(frozen=True)
class CognitiveControlState:
    confidence: float = 1.0
    uncertainty: float = 0.0
    contradiction_count: int = 0
    repeated_failures: int = 0
    resource_pressure: float = 0.0
    evidence_sufficiency: float = 1.0

    def validate(self) -> None:
        for field_name in (
            "confidence",
            "uncertainty",
            "resource_pressure",
            "evidence_sufficiency",
        ):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0 and 1")
        if self.contradiction_count < 0 or self.repeated_failures < 0:
            raise ValueError("counts cannot be negative")


@dataclass(frozen=True)
class RegulatoryDecision:
    action: RegulatoryAction
    risk_level: str
    review_depth: int
    rationale: str


class SelfRegulationEngine:
    """Fail-closed deterministic controller for AB5.

    The ordering is intentional: critical contradiction dominates every other
    signal, followed by resource containment, recurrent failure escalation,
    evidence/uncertainty handling, and finally normal operation.
    """

    def decide(self, state: CognitiveControlState) -> RegulatoryDecision:
        state.validate()

        if state.contradiction_count >= 2:
            return RegulatoryDecision(
                RegulatoryAction.ENTER_HOLD,
                "critical",
                3,
                "unresolved critical contradiction",
            )
        if state.resource_pressure >= 0.90:
            return RegulatoryDecision(
                RegulatoryAction.REDUCE_ACTION_SCOPE,
                "high",
                2,
                "resource pressure exceeds safe operating range",
            )
        if state.repeated_failures >= 3:
            return RegulatoryDecision(
                RegulatoryAction.REQUEST_SPECIALIST_OCS,
                "high",
                3,
                "repeated failure requires specialist review",
            )
        if state.evidence_sufficiency <= 0.30:
            return RegulatoryDecision(
                RegulatoryAction.SEEK_EVIDENCE,
                "medium",
                2,
                "evidence is insufficient for a reliable decision",
            )
        if state.uncertainty >= 0.85 or state.confidence <= 0.20:
            return RegulatoryDecision(
                RegulatoryAction.DEFER,
                "medium",
                2,
                "uncertainty or low confidence exceeds decision threshold",
            )
        if state.uncertainty >= 0.55 or state.confidence <= 0.55:
            return RegulatoryDecision(
                RegulatoryAction.INCREASE_REVIEW_DEPTH,
                "guarded",
                2,
                "internal state requires deeper review",
            )
        return RegulatoryDecision(
            RegulatoryAction.PROCEED,
            "normal",
            1,
            "internal control state is within normal bounds",
        )
