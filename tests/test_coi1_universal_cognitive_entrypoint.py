from __future__ import annotations

import pytest

from app.cognitive_validation.universal_entrypoint import (
    CognitiveEntrypointError,
    CognitiveMissionContext,
    UniversalCognitiveEntrypoint,
)


class FakeBrain:
    version = "test-brain/1"

    def __init__(self, score: float = 1.0) -> None:
        self.score = score
        self.seen: list[CognitiveMissionContext] = []

    def evaluate(self, context: CognitiveMissionContext) -> float:
        self.seen.append(context)
        return self.score


class ExplodingBrain:
    version = "test-brain/exploding"

    def evaluate(self, context: CognitiveMissionContext) -> float:
        del context
        raise RuntimeError("backend unavailable")


class InvalidBrain:
    version = "test-brain/invalid"

    def evaluate(self, context: CognitiveMissionContext) -> float:
        del context
        return "not-a-score"  # type: ignore[return-value]


def mission() -> CognitiveMissionContext:
    return CognitiveMissionContext(
        mission_id="mission-001",
        ocs_id="NOESIS",
        ocs_instance_id="noesis-runtime-001",
        generation=7,
        intent="resolve governed mission",
        state_revision="state-r42",
    )


def test_canonical_default_brain_accepts_mission_through_universal_entrypoint() -> None:
    proposal = UniversalCognitiveEntrypoint().enter(mission())
    assert proposal.cognitive_path_used is True
    assert proposal.integrated_score == 1.0
    assert proposal.brain_version == "AB0-AB13/canonical"


def test_entrypoint_preserves_mission_ocs_generation_and_state_context() -> None:
    brain = FakeBrain()
    context = mission()
    proposal = UniversalCognitiveEntrypoint(brain).enter(context)
    assert brain.seen == [context]
    assert proposal.mission_id == context.mission_id
    assert proposal.ocs_id == context.ocs_id
    assert proposal.ocs_instance_id == context.ocs_instance_id
    assert proposal.generation == context.generation
    assert proposal.brain_state_revision == context.state_revision


def test_cognitive_output_never_self_authorizes_or_permits_effects() -> None:
    proposal = UniversalCognitiveEntrypoint(FakeBrain()).enter(mission())
    assert proposal.authority_granted is False
    assert proposal.effects_permitted is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mission_id", ""),
        ("ocs_id", ""),
        ("ocs_instance_id", ""),
        ("intent", ""),
    ],
)
def test_missing_required_context_fails_closed(field: str, value: str) -> None:
    data = {
        "mission_id": "mission-001",
        "ocs_id": "NOESIS",
        "ocs_instance_id": "noesis-runtime-001",
        "generation": 7,
        "intent": "resolve governed mission",
        "state_revision": "state-r42",
    }
    data[field] = value
    with pytest.raises(CognitiveEntrypointError, match="cognitive_entry_context_invalid"):
        UniversalCognitiveEntrypoint(FakeBrain()).enter(CognitiveMissionContext(**data))


def test_negative_generation_fails_closed() -> None:
    context = CognitiveMissionContext(
        mission_id="mission-001",
        ocs_id="NOESIS",
        ocs_instance_id="noesis-runtime-001",
        generation=-1,
        intent="resolve governed mission",
    )
    with pytest.raises(CognitiveEntrypointError, match="generation"):
        UniversalCognitiveEntrypoint(FakeBrain()).enter(context)


def test_unavailable_brain_fails_closed() -> None:
    with pytest.raises(CognitiveEntrypointError, match="brain_unavailable"):
        UniversalCognitiveEntrypoint(ExplodingBrain()).enter(mission())


def test_invalid_cognitive_result_fails_closed() -> None:
    with pytest.raises(CognitiveEntrypointError, match="invalid_cognitive_result"):
        UniversalCognitiveEntrypoint(InvalidBrain()).enter(mission())


def test_degraded_cognitive_path_is_denied() -> None:
    with pytest.raises(CognitiveEntrypointError, match="cognitive_path_not_intact"):
        UniversalCognitiveEntrypoint(FakeBrain(score=0.92)).enter(mission())
