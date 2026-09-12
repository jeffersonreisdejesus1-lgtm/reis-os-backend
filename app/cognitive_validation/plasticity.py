from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple


@dataclass(frozen=True)
class PlasticityCycle:
    index: int
    phase: str
    target: str
    action: str
    reward: int
    switched: bool


@dataclass(frozen=True)
class PlasticityMetrics:
    cycles: int
    pre_drift_success_rate: float
    post_drift_success_rate: float
    final_window_success_rate: float
    adaptation_latency: int
    switches: int


@dataclass(frozen=True)
class PlasticityExperimentResult:
    treatment: PlasticityMetrics
    frozen_baseline: PlasticityMetrics
    treatment_cycles: Tuple[PlasticityCycle, ...]
    baseline_cycles: Tuple[PlasticityCycle, ...]


class DriftAdaptivePolicy:
    """Small deterministic policy that revises its action after sustained error."""

    def __init__(self, actions: Iterable[str], *, failure_threshold: int = 3) -> None:
        normalized = tuple(sorted(set(actions)))
        if len(normalized) != 2:
            raise ValueError("AB4 harness requires exactly two actions")
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be positive")
        self._actions = normalized
        self._current = normalized[0]
        self._failure_threshold = failure_threshold
        self._consecutive_failures = 0
        self._switches = 0

    @property
    def switches(self) -> int:
        return self._switches

    @property
    def current_action(self) -> str:
        return self._current

    def select(self) -> str:
        return self._current

    def observe(self, reward: int) -> bool:
        if reward not in (0, 1):
            raise ValueError("reward must be binary")
        if reward == 1:
            self._consecutive_failures = 0
            return False

        self._consecutive_failures += 1
        if self._consecutive_failures < self._failure_threshold:
            return False

        self._current = self._actions[1] if self._current == self._actions[0] else self._actions[0]
        self._consecutive_failures = 0
        self._switches += 1
        return True


class FrozenPolicy:
    def __init__(self, action: str = "alpha") -> None:
        self._action = action

    def select(self) -> str:
        return self._action

    def observe(self, reward: int) -> bool:
        if reward not in (0, 1):
            raise ValueError("reward must be binary")
        return False


def _rate(cycles: List[PlasticityCycle]) -> float:
    if not cycles:
        raise ValueError("cycle window cannot be empty")
    return sum(item.reward for item in cycles) / len(cycles)


def _metrics(
    cycles: List[PlasticityCycle],
    *,
    pre_drift_cycles: int,
    window: int,
    switches: int,
) -> PlasticityMetrics:
    before = cycles[:pre_drift_cycles]
    after = cycles[pre_drift_cycles:]
    final = cycles[-window:]

    latency = len(after)
    for offset, item in enumerate(after, start=1):
        if item.reward == 1 and all(next_item.reward == 1 for next_item in after[offset - 1 :]):
            latency = offset
            break

    return PlasticityMetrics(
        cycles=len(cycles),
        pre_drift_success_rate=_rate(before),
        post_drift_success_rate=_rate(after),
        final_window_success_rate=_rate(final),
        adaptation_latency=latency,
        switches=switches,
    )


def run_plasticity_experiment(
    *,
    pre_drift_cycles: int = 300,
    post_drift_cycles: int = 300,
    failure_threshold: int = 3,
    final_window: int = 100,
) -> PlasticityExperimentResult:
    """Run an explicit environment A->B shift and measure autonomous adaptation."""

    if pre_drift_cycles < 100 or post_drift_cycles < 100:
        raise ValueError("AB4 requires at least 100 cycles per environment phase")
    if final_window < 20 or final_window > post_drift_cycles:
        raise ValueError("invalid final window")

    learner = DriftAdaptivePolicy(("alpha", "beta"), failure_threshold=failure_threshold)
    baseline = FrozenPolicy("alpha")
    treatment_cycles: List[PlasticityCycle] = []
    baseline_cycles: List[PlasticityCycle] = []

    total = pre_drift_cycles + post_drift_cycles
    for index in range(total):
        phase = "A" if index < pre_drift_cycles else "B"
        target = "alpha" if phase == "A" else "beta"

        action = learner.select()
        reward = int(action == target)
        switched = learner.observe(reward)
        treatment_cycles.append(
            PlasticityCycle(index, phase, target, action, reward, switched)
        )

        baseline_action = baseline.select()
        baseline_reward = int(baseline_action == target)
        baseline.observe(baseline_reward)
        baseline_cycles.append(
            PlasticityCycle(index, phase, target, baseline_action, baseline_reward, False)
        )

    return PlasticityExperimentResult(
        treatment=_metrics(
            treatment_cycles,
            pre_drift_cycles=pre_drift_cycles,
            window=final_window,
            switches=learner.switches,
        ),
        frozen_baseline=_metrics(
            baseline_cycles,
            pre_drift_cycles=pre_drift_cycles,
            window=final_window,
            switches=0,
        ),
        treatment_cycles=tuple(treatment_cycles),
        baseline_cycles=tuple(baseline_cycles),
    )
