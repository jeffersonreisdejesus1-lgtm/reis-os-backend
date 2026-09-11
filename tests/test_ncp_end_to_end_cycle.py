from __future__ import annotations

import pytest

from app.cognitive_physiology.contracts import (
    BudgetEnvelope,
    Candidate,
    EpistemicGrade,
    MemoryLevel,
    OperationalCommitContext,
)
from app.cognitive_physiology.engine import (
    ExpectedOutcome,
    ObservedOutcome,
    UniversalCognitiveEngine,
)
from app.cognitive_physiology.local_profiles import LOCAL_PROFILES
from app.cognitive_physiology.runtime import CognitivePhysiologyRuntime


def runtime(
    ocs_id: str = "NÓESIS",
    *,
    budget: BudgetEnvelope | None = None,
) -> CognitivePhysiologyRuntime:
    profile = LOCAL_PROFILES[ocs_id]
    return CognitivePhysiologyRuntime(
        ocs_id=ocs_id,
        identity_ref=profile.identity_ref,
        state_namespace=profile.state_namespace,
        memory_namespace=profile.memory_namespace,
        budget=budget,
    )


def candidate(
    candidate_id: str,
    *,
    salience: float,
    risk: float = 0.1,
) -> Candidate:
    return Candidate(
        candidate_id=candidate_id,
        source_ocs="NÓESIS",
        content=candidate_id,
        epistemic_grade=EpistemicGrade.HYPOTHESIS,
        confidence=0.7,
        uncertainty=0.3,
        salience=salience,
        novelty=0.5,
        risk=risk,
        evidence_refs=("evidence://test",),
        ttl_cycles=2,
    )


def full_commit() -> OperationalCommitContext:
    return OperationalCommitContext(True, True, True, True, True)


def test_cycle_competes_broadcasts_observes_and_records_episode_without_world_commit() -> None:
    rt = runtime()
    engine = UniversalCognitiveEngine(rt)
    result = engine.run_cycle(
        mission_id="mission-1",
        candidates=(
            candidate("low", salience=0.2),
            candidate("high", salience=0.9),
        ),
        expected=ExpectedOutcome(expected_observation={"status": "ok"}),
        observe=lambda: ObservedOutcome(observation={"status": "ok"}),
        generation=0,
        provenance_ref="evidence://mission-1",
    )
    assert result.winner.candidate_id == "high"
    assert rt.workspace.broadcast_ids == ["high"]
    assert rt.world.values == {}
    assert result.residual.semantic == 0.0
    assert result.episodic_record.level == MemoryLevel.M2
    stored = engine.memory.get(
        MemoryLevel.M2,
        result.episodic_record.record_id,
    )
    assert stored == result.episodic_record


def test_material_action_requires_explicit_operational_commit() -> None:
    engine = UniversalCognitiveEngine(runtime())
    with pytest.raises(
        PermissionError,
        match="material_action_requires_explicit_operational_commit",
    ):
        engine.run_cycle(
            mission_id="mission-2",
            candidates=(candidate("action", salience=1.0),),
            expected=ExpectedOutcome(),
            observe=lambda: ObservedOutcome(),
            generation=0,
            action=lambda: "effect",
            provenance_ref="evidence://mission-2",
        )


def test_full_operational_commit_executes_effect_without_world_commit() -> None:
    rt = runtime()
    engine = UniversalCognitiveEngine(rt)
    effects: list[str] = []
    result = engine.run_cycle(
        mission_id="mission-3",
        candidates=(candidate("action", salience=1.0),),
        expected=ExpectedOutcome(expected_effect={"done": True}),
        observe=lambda: ObservedOutcome(effect={"done": True}),
        generation=0,
        action_effect_id="effect-1",
        action=lambda: effects.append("done"),
        commit_context=full_commit(),
        provenance_ref="evidence://mission-3",
    )
    assert effects == ["done"]
    assert result.effect_result is None
    assert rt.world.values == {}


def test_prediction_residual_updates_nm_without_granting_authority() -> None:
    engine = UniversalCognitiveEngine(runtime())
    result = engine.run_cycle(
        mission_id="mission-4",
        candidates=(candidate("prediction", salience=0.8),),
        expected=ExpectedOutcome(
            expected_observation={"value": 1},
            expected_effect={"done": True},
        ),
        observe=lambda: ObservedOutcome(
            observation={"value": 2},
            effect={"done": False},
        ),
        generation=0,
        provenance_ref="evidence://mission-4",
    )
    assert result.residual.semantic == 1.0
    assert result.residual.goal == 1.0
    assert result.nm_state.prediction_error > 0


def test_m2_to_m3_requires_qualification_and_persistence_authority() -> None:
    engine = UniversalCognitiveEngine(runtime())
    result = engine.run_cycle(
        mission_id="mission-5",
        candidates=(candidate("learn", salience=0.8),),
        expected=ExpectedOutcome(),
        observe=lambda: ObservedOutcome(),
        generation=0,
        provenance_ref="evidence://mission-5",
    )
    source_id = result.episodic_record.record_id
    with pytest.raises(PermissionError, match="m2_to_m3_direct_forbidden"):
        engine.memory.consolidate(
            source_record_id=source_id,
            target_record_id="semantic-1",
            qualified=False,
            persistence_authorized=True,
            generation=0,
        )
    with pytest.raises(
        PermissionError,
        match="m3_persistence_authority_required",
    ):
        engine.memory.consolidate(
            source_record_id=source_id,
            target_record_id="semantic-1",
            qualified=True,
            persistence_authorized=False,
            generation=0,
        )
    record = engine.memory.consolidate(
        source_record_id=source_id,
        target_record_id="semantic-1",
        qualified=True,
        persistence_authorized=True,
        generation=0,
    )
    assert record.level == MemoryLevel.M3
    assert record.payload["derived_from"] == source_id


def test_cycle_budget_counts_cycles_not_candidates() -> None:
    rt = runtime(budget=BudgetEnvelope(max_cycles=1))
    engine = UniversalCognitiveEngine(rt)
    engine.run_cycle(
        mission_id="budget-1",
        candidates=(
            candidate("a", salience=0.8),
            candidate("b", salience=0.7),
        ),
        expected=ExpectedOutcome(),
        observe=lambda: ObservedOutcome(),
        generation=0,
        provenance_ref="evidence://budget-1",
    )
    with pytest.raises(
        RuntimeError,
        match="cognitive_cycle_budget_exhausted",
    ):
        engine.run_cycle(
            mission_id="budget-2",
            candidates=(candidate("c", salience=0.9),),
            expected=ExpectedOutcome(),
            observe=lambda: ObservedOutcome(),
            generation=0,
            provenance_ref="evidence://budget-2",
        )
    assert "c" not in rt.workspace.candidates


def test_candidate_budget_fails_before_workspace_mutation() -> None:
    rt = runtime(budget=BudgetEnvelope(max_candidates_per_cycle=1))
    engine = UniversalCognitiveEngine(rt)
    with pytest.raises(RuntimeError, match="candidate_budget_exhausted"):
        engine.run_cycle(
            mission_id="candidate-budget",
            candidates=(
                candidate("a", salience=0.8),
                candidate("b", salience=0.7),
            ),
            expected=ExpectedOutcome(),
            observe=lambda: ObservedOutcome(),
            generation=0,
            provenance_ref="evidence://candidate-budget",
        )
    assert rt.workspace.candidates == {}
    assert rt.workspace.broadcast_ids == []
