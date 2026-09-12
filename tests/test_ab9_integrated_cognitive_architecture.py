from app.cognitive_validation.integrated_architecture import (
    CognitiveComponent,
    IntegratedCognitiveArchitecture,
)


def test_intact_architecture_succeeds() -> None:
    architecture = IntegratedCognitiveArchitecture()
    outcome = architecture.assert_integrated()
    assert outcome.success is True
    assert outcome.score == 1.0
    assert outcome.missing_components == ()
    assert len(outcome.active_components) == 12


def test_ablation_matrix_covers_every_required_component() -> None:
    matrix = IntegratedCognitiveArchitecture().ablation_matrix()
    assert set(matrix) == set(CognitiveComponent)
    assert len(matrix) == 12


def test_each_single_component_ablation_degrades_predictably() -> None:
    architecture = IntegratedCognitiveArchitecture()
    matrix = architecture.ablation_matrix()
    for component, outcome in matrix.items():
        assert outcome.success is False
        assert outcome.score < 1.0
        assert outcome.missing_components == (component,)
        assert component not in outcome.active_components


def test_no_component_is_bypassable() -> None:
    architecture = IntegratedCognitiveArchitecture()
    for component in CognitiveComponent:
        ablated = architecture.run(ablate=(component,))
        intact = architecture.run()
        assert ablated.score < intact.score
        assert ablated != intact


def test_multi_component_ablation_degrades_more_than_single() -> None:
    architecture = IntegratedCognitiveArchitecture()
    single = architecture.run(ablate=(CognitiveComponent.PLANNING,))
    combined = architecture.run(
        ablate=(CognitiveComponent.PLANNING, CognitiveComponent.METACOGNITION)
    )
    assert combined.score < single.score
    assert combined.success is False


def test_required_cognitive_components_are_exact() -> None:
    assert set(CognitiveComponent) == {
        CognitiveComponent.PERCEPTION,
        CognitiveComponent.WORKING_MEMORY,
        CognitiveComponent.LONG_TERM_MEMORY,
        CognitiveComponent.ATTENTION,
        CognitiveComponent.WORLD_MODEL,
        CognitiveComponent.SELF_MODEL,
        CognitiveComponent.PLANNING,
        CognitiveComponent.DECISION,
        CognitiveComponent.FEEDBACK,
        CognitiveComponent.LEARNING,
        CognitiveComponent.METACOGNITION,
        CognitiveComponent.SELF_REGULATION,
    }
