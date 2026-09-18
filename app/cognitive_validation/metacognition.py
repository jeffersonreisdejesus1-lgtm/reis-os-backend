from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class RevisionDisposition(str, Enum):
    ACCEPT = "ACCEPT"
    REVERT = "REVERT"
    HOLD = "HOLD"


@dataclass(frozen=True)
class FailureEpisode:
    failure_signature: str
    attempted_policy: str
    outcome_score: float
    safety_violation: bool = False

    def validate(self) -> None:
        if not self.failure_signature:
            raise ValueError("failure_signature is required")
        if not self.attempted_policy:
            raise ValueError("attempted_policy is required")
        if not 0.0 <= self.outcome_score <= 1.0:
            raise ValueError("outcome_score must be between 0 and 1")


@dataclass(frozen=True)
class PolicyHypothesis:
    baseline_policy: str
    candidate_policy: str
    diagnosis: str
    expected_mechanism: str

    def validate(self) -> None:
        if not self.baseline_policy or not self.candidate_policy:
            raise ValueError("baseline_policy and candidate_policy are required")
        if self.baseline_policy == self.candidate_policy:
            raise ValueError("candidate policy must materially differ from baseline")
        if not self.diagnosis or not self.expected_mechanism:
            raise ValueError("diagnosis and expected_mechanism are required")


@dataclass(frozen=True)
class SandboxTrial:
    policy: str
    scores: tuple[float, ...]
    safety_violations: int = 0

    def validate(self) -> None:
        if not self.policy:
            raise ValueError("policy is required")
        if not self.scores:
            raise ValueError("at least one sandbox score is required")
        if any(score < 0.0 or score > 1.0 for score in self.scores):
            raise ValueError("sandbox scores must be between 0 and 1")
        if self.safety_violations < 0:
            raise ValueError("safety_violations cannot be negative")

    @property
    def mean_score(self) -> float:
        return sum(self.scores) / len(self.scores)


@dataclass(frozen=True)
class MetacognitiveRevisionResult:
    disposition: RevisionDisposition
    selected_policy: str
    diagnosis: str
    baseline_score: float
    candidate_score: float
    improvement: float
    causal_behavior_change: bool
    rationale: str


class MetacognitiveRevisionEngine:
    """Deterministic fail-closed AB6 metacognitive revision evaluator.

    A revision is accepted only when recurring failure produces a concrete
    diagnosis, a materially different policy is tested in a sandbox, and the
    candidate demonstrates a measurable causal behavioral improvement without
    safety regression. Textual self-critique without a changed policy cannot
    satisfy the gate.
    """

    MIN_RECURRING_FAILURES = 3
    MIN_TRIAL_SAMPLES = 5
    MIN_IMPROVEMENT = 0.20

    def diagnose(self, episodes: Iterable[FailureEpisode]) -> str:
        rows = tuple(episodes)
        if len(rows) < self.MIN_RECURRING_FAILURES:
            raise RuntimeError("RECURRING_FAILURE_NOT_ESTABLISHED")
        for row in rows:
            row.validate()
        signatures = {row.failure_signature for row in rows}
        if len(signatures) != 1:
            raise RuntimeError("FAILURE_PATTERN_NOT_STABLE")
        if any(row.safety_violation for row in rows):
            raise RuntimeError("SAFETY_VIOLATION_REQUIRES_HOLD")
        signature = rows[0].failure_signature
        return f"recurring_failure:{signature}:count={len(rows)}"

    def propose(
        self,
        *,
        baseline_policy: str,
        candidate_policy: str,
        diagnosis: str,
        expected_mechanism: str,
    ) -> PolicyHypothesis:
        hypothesis = PolicyHypothesis(
            baseline_policy=baseline_policy,
            candidate_policy=candidate_policy,
            diagnosis=diagnosis,
            expected_mechanism=expected_mechanism,
        )
        hypothesis.validate()
        return hypothesis

    def evaluate(
        self,
        hypothesis: PolicyHypothesis,
        *,
        baseline_trial: SandboxTrial,
        candidate_trial: SandboxTrial,
    ) -> MetacognitiveRevisionResult:
        hypothesis.validate()
        baseline_trial.validate()
        candidate_trial.validate()

        if baseline_trial.policy != hypothesis.baseline_policy:
            raise RuntimeError("BASELINE_POLICY_BINDING_MISMATCH")
        if candidate_trial.policy != hypothesis.candidate_policy:
            raise RuntimeError("CANDIDATE_POLICY_BINDING_MISMATCH")
        if len(baseline_trial.scores) < self.MIN_TRIAL_SAMPLES or len(candidate_trial.scores) < self.MIN_TRIAL_SAMPLES:
            return MetacognitiveRevisionResult(
                disposition=RevisionDisposition.HOLD,
                selected_policy=hypothesis.baseline_policy,
                diagnosis=hypothesis.diagnosis,
                baseline_score=baseline_trial.mean_score,
                candidate_score=candidate_trial.mean_score,
                improvement=candidate_trial.mean_score - baseline_trial.mean_score,
                causal_behavior_change=False,
                rationale="insufficient sandbox sample",
            )

        improvement = candidate_trial.mean_score - baseline_trial.mean_score
        causal_behavior_change = hypothesis.candidate_policy != hypothesis.baseline_policy and abs(improvement) > 0.0

        if candidate_trial.safety_violations > baseline_trial.safety_violations:
            return MetacognitiveRevisionResult(
                disposition=RevisionDisposition.REVERT,
                selected_policy=hypothesis.baseline_policy,
                diagnosis=hypothesis.diagnosis,
                baseline_score=baseline_trial.mean_score,
                candidate_score=candidate_trial.mean_score,
                improvement=improvement,
                causal_behavior_change=causal_behavior_change,
                rationale="candidate introduced a safety regression",
            )

        if causal_behavior_change and improvement >= self.MIN_IMPROVEMENT:
            return MetacognitiveRevisionResult(
                disposition=RevisionDisposition.ACCEPT,
                selected_policy=hypothesis.candidate_policy,
                diagnosis=hypothesis.diagnosis,
                baseline_score=baseline_trial.mean_score,
                candidate_score=candidate_trial.mean_score,
                improvement=improvement,
                causal_behavior_change=True,
                rationale="sandbox retest demonstrated material improvement",
            )

        return MetacognitiveRevisionResult(
            disposition=RevisionDisposition.REVERT,
            selected_policy=hypothesis.baseline_policy,
            diagnosis=hypothesis.diagnosis,
            baseline_score=baseline_trial.mean_score,
            candidate_score=candidate_trial.mean_score,
            improvement=improvement,
            causal_behavior_change=causal_behavior_change,
            rationale="candidate did not demonstrate sufficient causal improvement",
        )

    def revise(
        self,
        *,
        failures: Iterable[FailureEpisode],
        baseline_policy: str,
        candidate_policy: str,
        expected_mechanism: str,
        baseline_trial: SandboxTrial,
        candidate_trial: SandboxTrial,
    ) -> MetacognitiveRevisionResult:
        diagnosis = self.diagnose(failures)
        hypothesis = self.propose(
            baseline_policy=baseline_policy,
            candidate_policy=candidate_policy,
            diagnosis=diagnosis,
            expected_mechanism=expected_mechanism,
        )
        return self.evaluate(
            hypothesis,
            baseline_trial=baseline_trial,
            candidate_trial=candidate_trial,
        )
