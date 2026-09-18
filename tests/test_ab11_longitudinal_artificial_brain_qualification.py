from app.cognitive_validation.longitudinal_brain_qualification import (
    LongitudinalArtificialBrainQualification,
)


def test_ab11_longitudinal_qualification_requires_1000_cycles():
    harness = LongitudinalArtificialBrainQualification()
    try:
        harness.run(999)
    except ValueError as exc:
        assert str(exc) == "AB11_REQUIRES_AT_LEAST_1000_CYCLES"
    else:
        raise AssertionError("AB11 accepted an under-length experiment")


def test_ab11_full_treatment_beats_frozen_memory_ablated_and_reduced_actor_baselines():
    result = LongitudinalArtificialBrainQualification().run(1200)
    assert result.cycles == 1200
    assert len(result.task_families) >= 3
    assert result.full_success_rate > 0.98
    assert result.full_success_rate > result.frozen_success_rate + 0.40
    assert result.full_success_rate > result.memory_ablated_success_rate + 0.30
    assert result.full_success_rate > result.reduced_actor_success_rate + 0.20


def test_ab11_crosses_restarts_generation_changes_drift_and_fault_injection():
    result = LongitudinalArtificialBrainQualification().run(1200)
    assert result.environment_drifts == 1
    assert result.model_restarts >= 5
    assert result.ocs_restarts >= 3
    assert result.generation_changes == result.ocs_restarts
    assert result.injected_faults >= 8
    assert result.safely_contained_faults == result.injected_faults
    assert result.identity_preserved is True


def test_ab11_preserves_required_cognitive_properties_longitudinally():
    result = LongitudinalArtificialBrainQualification().run(1200)
    assert result.causal_memory_preserved is True
    assert result.plasticity_observed is True
    assert result.self_regulation_observed is True
    assert result.metacognitive_revision_observed is True
