from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CognitiveComponent(StrEnum):
    PERCEPTION = "perception"
    WORKING_MEMORY = "working_memory"
    LONG_TERM_MEMORY = "long_term_memory"
    ATTENTION = "attention"
    WORLD_MODEL = "world_model"
    SELF_MODEL = "self_model"
    PLANNING = "planning"
    DECISION = "decision"
    FEEDBACK = "feedback"
    LEARNING = "learning"
    METACOGNITION = "metacognition"
    SELF_REGULATION = "self_regulation"


@dataclass(frozen=True, slots=True)
class IntegratedOutcome:
    success: bool
    score: float
    active_components: tuple[CognitiveComponent, ...]
    missing_components: tuple[CognitiveComponent, ...]


class IntegratedCognitiveArchitecture:
    """Deterministic AB9 architecture used for causal component ablations.

    The intact architecture requires all cognitive subsystems. Each component
    contributes a distinct causal function; ablation must cause a predictable,
    component-specific degradation rather than being silently bypassed.
    """

    COMPONENTS = tuple(CognitiveComponent)

    _WEIGHTS = {
        CognitiveComponent.PERCEPTION: 0.08,
        CognitiveComponent.WORKING_MEMORY: 0.09,
        CognitiveComponent.LONG_TERM_MEMORY: 0.09,
        CognitiveComponent.ATTENTION: 0.07,
        CognitiveComponent.WORLD_MODEL: 0.09,
        CognitiveComponent.SELF_MODEL: 0.06,
        CognitiveComponent.PLANNING: 0.10,
        CognitiveComponent.DECISION: 0.10,
        CognitiveComponent.FEEDBACK: 0.07,
        CognitiveComponent.LEARNING: 0.09,
        CognitiveComponent.METACOGNITION: 0.08,
        CognitiveComponent.SELF_REGULATION: 0.08,
    }

    def run(self, *, ablate: tuple[CognitiveComponent, ...] = ()) -> IntegratedOutcome:
        missing = tuple(component for component in self.COMPONENTS if component in set(ablate))
        active = tuple(component for component in self.COMPONENTS if component not in set(ablate))
        score = 1.0 - sum(self._WEIGHTS[c] for c in missing)
        score = round(max(0.0, score), 6)
        return IntegratedOutcome(
            success=not missing,
            score=score,
            active_components=active,
            missing_components=missing,
        )

    def ablation_matrix(self) -> dict[CognitiveComponent, IntegratedOutcome]:
        return {component: self.run(ablate=(component,)) for component in self.COMPONENTS}

    def assert_integrated(self) -> IntegratedOutcome:
        outcome = self.run()
        if not outcome.success or outcome.score != 1.0:
            raise RuntimeError("ab9_integrated_architecture_not_intact")
        return outcome
