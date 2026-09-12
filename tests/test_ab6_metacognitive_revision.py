import pytest

from app.cognitive_validation.metacognition import (
    FailureEpisode,
    MetacognitiveRevisionEngine,
    RevisionDisposition,
    SandboxTrial,
)


def recurring_failures(count: int = 3):
    return tuple(
        FailureEpisode(
            failure_signature="overconfident_commit",
            attempted_policy="commit_on_first_signal",
            outcome_score=0.2,
        )
        for _ in range(count)
    )


def test_ab6_accepts_policy_revision_after_recurring_failure_and_sandbox_retest():
    engine = MetacognitiveRevisionEngine()
    result = engine.revise(
        failures=recurring_failures(),
        baseline_policy="commit_on_first_signal",
        candidate_policy="require_two_independent_signals",
        expected_mechanism="additional evidence reduces repeated false-positive commits",
        baseline_trial=SandboxTrial(
            policy="commit_on_first_signal",
            scores=(0.2, 0.3, 0.2, 0.3, 0.2),
        ),
        candidate_trial=SandboxTrial(
            policy="require_two_independent_signals",
            scores=(0.8, 0.9, 0.8, 0.9, 0.8),
        ),
    )

    assert result.disposition is RevisionDisposition.ACCEPT
    assert result.selected_policy == "require_two_independent_signals"
    assert result.causal_behavior_change is True
    assert result.improvement >= engine.MIN_IMPROVEMENT
    assert result.diagnosis.startswith("recurring_failure:overconfident_commit")


def test_ab6_reverts_candidate_when_retest_does_not_improve_enough():
    engine = MetacognitiveRevisionEngine()
    result = engine.revise(
        failures=recurring_failures(),
        baseline_policy="commit_on_first_signal",
        candidate_policy="wait_one_extra_cycle",
        expected_mechanism="delay may reduce impulsive commits",
        baseline_trial=SandboxTrial(
            policy="commit_on_first_signal",
            scores=(0.50, 0.50, 0.50, 0.50, 0.50),
        ),
        candidate_trial=SandboxTrial(
            policy="wait_one_extra_cycle",
            scores=(0.55, 0.55, 0.55, 0.55, 0.55),
        ),
    )

    assert result.disposition is RevisionDisposition.REVERT
    assert result.selected_policy == "commit_on_first_signal"
    assert result.causal_behavior_change is True


def test_ab6_reverts_any_candidate_with_safety_regression():
    engine = MetacognitiveRevisionEngine()
    result = engine.revise(
        failures=recurring_failures(),
        baseline_policy="commit_on_first_signal",
        candidate_policy="bypass_review_for_speed",
        expected_mechanism="speed increases nominal task score",
        baseline_trial=SandboxTrial(
            policy="commit_on_first_signal",
            scores=(0.2, 0.2, 0.2, 0.2, 0.2),
            safety_violations=0,
        ),
        candidate_trial=SandboxTrial(
            policy="bypass_review_for_speed",
            scores=(0.9, 0.9, 0.9, 0.9, 0.9),
            safety_violations=1,
        ),
    )

    assert result.disposition is RevisionDisposition.REVERT
    assert result.selected_policy == "commit_on_first_signal"
    assert "safety regression" in result.rationale


def test_ab6_text_only_self_critique_cannot_count_as_revision():
    engine = MetacognitiveRevisionEngine()
    diagnosis = engine.diagnose(recurring_failures())

    with pytest.raises(ValueError, match="materially differ"):
        engine.propose(
            baseline_policy="commit_on_first_signal",
            candidate_policy="commit_on_first_signal",
            diagnosis=diagnosis,
            expected_mechanism="I should be more careful next time",
        )


def test_ab6_requires_stable_recurring_failure_pattern():
    engine = MetacognitiveRevisionEngine()

    with pytest.raises(RuntimeError, match="RECURRING_FAILURE_NOT_ESTABLISHED"):
        engine.diagnose(recurring_failures(2))

    with pytest.raises(RuntimeError, match="FAILURE_PATTERN_NOT_STABLE"):
        engine.diagnose(
            (
                FailureEpisode("a", "p", 0.1),
                FailureEpisode("a", "p", 0.1),
                FailureEpisode("b", "p", 0.1),
            )
        )


def test_ab6_holds_when_sandbox_sample_is_insufficient():
    engine = MetacognitiveRevisionEngine()
    diagnosis = engine.diagnose(recurring_failures())
    hypothesis = engine.propose(
        baseline_policy="commit_on_first_signal",
        candidate_policy="require_two_independent_signals",
        diagnosis=diagnosis,
        expected_mechanism="additional evidence changes future decisions",
    )

    result = engine.evaluate(
        hypothesis,
        baseline_trial=SandboxTrial(
            policy="commit_on_first_signal",
            scores=(0.2, 0.2),
        ),
        candidate_trial=SandboxTrial(
            policy="require_two_independent_signals",
            scores=(0.9, 0.9),
        ),
    )

    assert result.disposition is RevisionDisposition.HOLD
    assert result.causal_behavior_change is False


def test_ab6_rejects_failure_history_with_safety_violation():
    engine = MetacognitiveRevisionEngine()
    failures = (
        FailureEpisode("unsafe", "p", 0.1),
        FailureEpisode("unsafe", "p", 0.1),
        FailureEpisode("unsafe", "p", 0.1, safety_violation=True),
    )

    with pytest.raises(RuntimeError, match="SAFETY_VIOLATION_REQUIRES_HOLD"):
        engine.diagnose(failures)
