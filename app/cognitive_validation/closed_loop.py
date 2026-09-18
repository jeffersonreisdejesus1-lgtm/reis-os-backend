from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CognitiveState:
    bias: float = 0.0
    revision: int = 0


@dataclass(frozen=True)
class CognitiveDecision:
    stimulus: float
    score: float
    action: int
    state_revision: int


@dataclass(frozen=True)
class CognitiveObservation:
    expected_action: int
    observed_action: int
    residual: int


@dataclass(frozen=True)
class ClosedLoopTrace:
    before: CognitiveState
    decision: CognitiveDecision
    observation: CognitiveObservation
    after: CognitiveState
    state_update_applied: bool


class ClosedCognitiveLoop:
    """Deterministic AB1 harness.

    The loop is intentionally small: prior state changes processing, an action is
    observed against an external target, the residual updates state, and the
    updated state changes future processing. State mutation can be ablated to
    provide the causal control required by AB1.
    """

    def __init__(self, *, learning_rate: float = 0.5) -> None:
        if learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        self.learning_rate = learning_rate

    @staticmethod
    def decide(state: CognitiveState, stimulus: float) -> CognitiveDecision:
        score = stimulus + state.bias
        action = 1 if score >= 0 else 0
        return CognitiveDecision(
            stimulus=stimulus,
            score=score,
            action=action,
            state_revision=state.revision,
        )

    @staticmethod
    def observe(decision: CognitiveDecision, *, expected_action: int) -> CognitiveObservation:
        if expected_action not in (0, 1):
            raise ValueError("expected_action must be 0 or 1")
        return CognitiveObservation(
            expected_action=expected_action,
            observed_action=decision.action,
            residual=expected_action - decision.action,
        )

    def update(
        self,
        state: CognitiveState,
        observation: CognitiveObservation,
        *, apply_state_update: bool = True,
    ) -> CognitiveState:
        if not apply_state_update:
            return state
        return CognitiveState(
            bias=state.bias + self.learning_rate * observation.residual,
            revision=state.revision + 1,
        )

    def cycle(
        self,
        state: CognitiveState,
        *,
        stimulus: float,
        expected_action: int,
        apply_state_update: bool = True,
    ) -> ClosedLoopTrace:
        decision = self.decide(state, stimulus)
        observation = self.observe(decision, expected_action=expected_action)
        after = self.update(
            state,
            observation,
            apply_state_update=apply_state_update,
        )
        return ClosedLoopTrace(
            before=state,
            decision=decision,
            observation=observation,
            after=after,
            state_update_applied=apply_state_update,
        )
