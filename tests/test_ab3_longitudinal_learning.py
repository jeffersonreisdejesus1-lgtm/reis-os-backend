from app.cognitive_validation import (
    ContextualPolicy,
    run_longitudinal_learning_experiment,
)


def test_ab3_runs_required_1000_cycle_longitudinal_experiment():
    result = run_longitudinal_learning_experiment(cycles=1000, window=100)
    assert result.treatment.cycles == 1000
    assert result.frozen_baseline.cycles == 1000
    assert result.treatment.policy_updates == 1000
    assert result.frozen_baseline.policy_updates == 0


def test_ab3_treatment_improves_over_its_early_window():
    result = run_longitudinal_learning_experiment(cycles=1000, window=100)
    assert result.treatment.final_window_success_rate > result.treatment.first_window_success_rate
    assert result.treatment.final_window_success_rate >= 0.99


def test_ab3_treatment_beats_frozen_non_learning_baseline():
    result = run_longitudinal_learning_experiment(cycles=1000, window=100)
    assert result.frozen_baseline.final_window_success_rate == 0.5
    assert result.cognitive_gain >= 0.49


def test_ab3_learning_reduces_repeated_mistakes_relative_to_frozen_baseline():
    result = run_longitudinal_learning_experiment(cycles=1000, window=100)
    treatment_errors = sum(1 for cycle in result.treatment_cycles[-100:] if cycle.reward == 0)
    baseline_errors = sum(1 for cycle in result.baseline_cycles[-100:] if cycle.reward == 0)
    assert treatment_errors == 0
    assert baseline_errors == 50


def test_ab3_experiment_is_deterministically_reproducible():
    first = run_longitudinal_learning_experiment(cycles=1000, window=100)
    second = run_longitudinal_learning_experiment(cycles=1000, window=100)
    assert first.treatment == second.treatment
    assert first.frozen_baseline == second.frozen_baseline
    assert first.treatment_cycles == second.treatment_cycles


def test_ab3_rejects_experiment_below_minimum_cycle_threshold():
    try:
        run_longitudinal_learning_experiment(cycles=499, window=100)
    except ValueError as exc:
        assert "at least 500 cycles" in str(exc)
    else:
        raise AssertionError("AB3 must fail closed below the minimum cycle count")


def test_frozen_policy_cannot_mutate_learning_state():
    policy = ContextualPolicy(("alpha", "beta"), learning_enabled=False)
    action = policy.select("context-a")
    assert policy.observe("context-a", action, 1) is False
    assert policy.updates == 0
    assert policy.snapshot() == {}
