from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, MutableMapping, Tuple


@dataclass(frozen=True)
class LearningCycle:
    index: int
    context: str
    action: str
    reward: int
    learned: bool


@dataclass(frozen=True)
class LongitudinalMetrics:
    cycles: int
    successes: int
    success_rate: float
    first_window_success_rate: float
    final_window_success_rate: float
    repeated_mistakes: int
    policy_updates: int


@dataclass(frozen=True)
class LongitudinalExperimentResult:
    treatment: LongitudinalMetrics
    frozen_baseline: LongitudinalMetrics
    treatment_cycles: Tuple[LearningCycle, ...]
    baseline_cycles: Tuple[LearningCycle, ...]

    @property
    def cognitive_gain(self) -> float:
        return self.treatment.final_window_success_rate - self.frozen_baseline.final_window_success_rate


class ContextualPolicy:
    """Deterministic contextual learner used only as the AB3 material proof harness.

    For every context, each action is explored once, then the action with the
    highest empirical mean reward is selected. Ties are resolved lexicographically
    to keep the experiment reproducible.
    """

    def __init__(self, actions: Iterable[str], *, learning_enabled: bool = True) -> None:
        normalized = tuple(sorted(set(actions)))
        if len(normalized) < 2:
            raise ValueError("at least two actions are required")
        self._actions = normalized
        self._learning_enabled = learning_enabled
        self._stats: MutableMapping[str, MutableMapping[str, List[int]]] = {}
        self._updates = 0

    @property
    def updates(self) -> int:
        return self._updates

    def select(self, context: str) -> str:
        if not self._learning_enabled:
            return self._actions[0]

        context_stats = self._stats.setdefault(
            context, {action: [0, 0] for action in self._actions}
        )

        for action in self._actions:
            if context_stats[action][1] == 0:
                return action

        def score(action: str) -> tuple[float, str]:
            reward_sum, count = context_stats[action]
            return (reward_sum / count, action)

        return max(self._actions, key=score)

    def observe(self, context: str, action: str, reward: int) -> bool:
        if reward not in (0, 1):
            raise ValueError("reward must be binary")
        if action not in self._actions:
            raise ValueError("unknown action")
        if not self._learning_enabled:
            return False

        context_stats = self._stats.setdefault(
            context, {candidate: [0, 0] for candidate in self._actions}
        )
        context_stats[action][0] += reward
        context_stats[action][1] += 1
        self._updates += 1
        return True

    def snapshot(self) -> Mapping[str, Mapping[str, tuple[int, int]]]:
        return {
            context: {
                action: (values[0], values[1])
                for action, values in action_stats.items()
            }
            for context, action_stats in self._stats.items()
        }


def _window_rate(cycles: List[LearningCycle], start: int, end: int) -> float:
    window = cycles[start:end]
    if not window:
        raise ValueError("window cannot be empty")
    return sum(item.reward for item in window) / len(window)


def _metrics(cycles: List[LearningCycle], policy_updates: int, window: int) -> LongitudinalMetrics:
    if len(cycles) < window * 2:
        raise ValueError("cycles must contain at least two measurement windows")
    successes = sum(item.reward for item in cycles)
    repeated_mistakes = sum(
        1
        for previous, current in zip(cycles, cycles[1:])
        if previous.context == current.context
        and previous.action == current.action
        and previous.reward == current.reward == 0
    )
    return LongitudinalMetrics(
        cycles=len(cycles),
        successes=successes,
        success_rate=successes / len(cycles),
        first_window_success_rate=_window_rate(cycles, 0, window),
        final_window_success_rate=_window_rate(cycles, len(cycles) - window, len(cycles)),
        repeated_mistakes=repeated_mistakes,
        policy_updates=policy_updates,
    )


def run_longitudinal_learning_experiment(
    *,
    cycles: int = 1000,
    window: int = 100,
) -> LongitudinalExperimentResult:
    """Run AB3 treatment vs frozen control over a deterministic 1000-cycle task stream.

    The task family alternates two contexts whose optimal actions differ. The frozen
    control always selects the same action. The learning treatment receives only the
    reward signal from each prior cycle and must improve its future decisions from
    that accumulated experience.
    """

    if cycles < 500:
        raise ValueError("AB3 requires at least 500 cycles")
    if window < 20 or window * 2 > cycles:
        raise ValueError("invalid measurement window")

    target_by_context: Dict[str, str] = {"context-a": "alpha", "context-b": "beta"}
    treatment_policy = ContextualPolicy(("alpha", "beta"), learning_enabled=True)
    baseline_policy = ContextualPolicy(("alpha", "beta"), learning_enabled=False)

    treatment_cycles: List[LearningCycle] = []
    baseline_cycles: List[LearningCycle] = []

    for index in range(cycles):
        context = "context-a" if index % 2 == 0 else "context-b"
        target = target_by_context[context]

        treatment_action = treatment_policy.select(context)
        treatment_reward = int(treatment_action == target)
        learned = treatment_policy.observe(context, treatment_action, treatment_reward)
        treatment_cycles.append(
            LearningCycle(index, context, treatment_action, treatment_reward, learned)
        )

        baseline_action = baseline_policy.select(context)
        baseline_reward = int(baseline_action == target)
        baseline_policy.observe(context, baseline_action, baseline_reward)
        baseline_cycles.append(
            LearningCycle(index, context, baseline_action, baseline_reward, False)
        )

    treatment = _metrics(treatment_cycles, treatment_policy.updates, window)
    baseline = _metrics(baseline_cycles, baseline_policy.updates, window)
    return LongitudinalExperimentResult(
        treatment=treatment,
        frozen_baseline=baseline,
        treatment_cycles=tuple(treatment_cycles),
        baseline_cycles=tuple(baseline_cycles),
    )
