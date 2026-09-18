from app.cognitive_validation import (
    DriftAdaptivePolicy,
    run_plasticity_experiment,
)


def test_ab4_runs_explicit_environment_a_to_b_shift():
    result = run_plasticity_experiment(
        pre_drift_cycles=300,
        post_drift_cycles=300,
        failure_threshold=3,
        final_window=100,
    )
    assert result.treatment.cycles == 600
    assert result.treatment.pre_drift_success_rate == 1.0
    assert result.frozen_baseline.pre_drift_success_rate == 1.0


def test_ab4_treatment_adapts_without_manual_reprogramming():
    result = run_plasticity_experiment()
    assert result.treatment.switches == 1
    assert result.treatment.adaptation_latency == 4
    assert result.treatment.final_window_success_rate == 1.0


def test_ab4_frozen_baseline_fails_after_environment_drift():
    result = run_plasticity_experiment()
    assert result.frozen_baseline.post_drift_success_rate == 0.0
    assert result.frozen_baseline.final_window_success_rate == 0.0


def test_ab4_treatment_materially_outperforms_frozen_baseline_post_drift():
    result = run_plasticity_experiment()
    assert result.treatment.post_drift_success_rate >= 0.99
    assert result.treatment.final_window_success_rate - result.frozen_baseline.final_window_success_rate == 1.0


def test_ab4_is_deterministically_reproducible():
    first = run_plasticity_experiment()
    second = run_plasticity_experiment()
    assert first == second


def test_ab4_fail_closed_on_inadequate_experiment_length():
    try:
        run_plasticity_experiment(pre_drift_cycles=99, post_drift_cycles=300)
    except ValueError as exc:
        assert "at least 100 cycles" in str(exc)
    else:
        raise AssertionError("AB4 must reject undersized environment phases")


def test_drift_policy_requires_sustained_error_before_switching():
    policy = DriftAdaptivePolicy(("alpha", "beta"), failure_threshold=3)
    assert policy.current_action == "alpha"
    assert policy.observe(0) is False
    assert policy.observe(0) is False
    assert policy.current_action == "alpha"
    assert policy.observe(0) is True
    assert policy.current_action == "beta"
    assert policy.switches == 1
