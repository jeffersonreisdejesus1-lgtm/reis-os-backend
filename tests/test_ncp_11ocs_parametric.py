from __future__ import annotations

import pytest

from app.cognitive_physiology.contracts import Candidate, EpistemicGrade, OperationalCommitContext
from app.cognitive_physiology.local_profiles import LOCAL_PROFILES
from app.cognitive_physiology.runtime import CognitivePhysiologyRuntime


OCS_IDS = tuple(LOCAL_PROFILES)


def make_runtime(ocs_id: str) -> CognitivePhysiologyRuntime:
    profile = LOCAL_PROFILES[ocs_id]
    return CognitivePhysiologyRuntime(
        ocs_id=ocs_id,
        identity_ref=profile.identity_ref,
        state_namespace=profile.state_namespace,
        memory_namespace=profile.memory_namespace,
    )


def make_candidate(ocs_id: str, suffix: str = "1") -> Candidate:
    return Candidate(
        candidate_id=f"{ocs_id}-{suffix}",
        source_ocs=ocs_id,
        content="local hypothesis",
        epistemic_grade=EpistemicGrade.HYPOTHESIS,
        confidence=0.5,
        uncertainty=0.5,
        salience=0.5,
        novelty=0.5,
        risk=0.1,
        ttl_cycles=2,
    )


@pytest.mark.parametrize("ocs_id", OCS_IDS)
def test_each_ocs_has_locally_owned_workspace_and_world(ocs_id: str) -> None:
    rt = make_runtime(ocs_id)
    rt.ingest_candidate(make_candidate(ocs_id), generation=0)
    rt.cognitive_ignition(f"{ocs_id}-1", generation=0)
    assert rt.workspace.broadcast_ids == [f"{ocs_id}-1"]
    assert rt.world.values == {}


@pytest.mark.parametrize("ocs_id", OCS_IDS)
def test_each_ocs_denies_operational_effect_without_full_commit(ocs_id: str) -> None:
    rt = make_runtime(ocs_id)
    effects: list[str] = []
    context = OperationalCommitContext(
        r6_clear=True,
        authority_bound=False,
        capability_bound=True,
        execution_budget_available=True,
        state_generation_current=True,
    )
    with pytest.raises(PermissionError, match="operational_commit_denied"):
        rt.operational_commit(
            effect_id=f"effect-{ocs_id}",
            context=context,
            generation=0,
            effect=lambda: effects.append(ocs_id),
        )
    assert effects == []


@pytest.mark.parametrize("ocs_id", OCS_IDS)
def test_each_ocs_recovery_fences_prior_generation(ocs_id: str) -> None:
    rt = make_runtime(ocs_id)
    rt.recover_to_generation(restored_generation=0)
    with pytest.raises(PermissionError, match="stale_generation_writer"):
        rt.ingest_candidate(make_candidate(ocs_id), generation=0)


@pytest.mark.parametrize("source_ocs", OCS_IDS)
@pytest.mark.parametrize("target_ocs", OCS_IDS)
def test_cross_ocs_candidate_write_is_denied_without_handoff(source_ocs: str, target_ocs: str) -> None:
    if source_ocs == target_ocs:
        pytest.skip("local candidate is allowed")
    target = make_runtime(target_ocs)
    with pytest.raises(PermissionError, match="foreign_candidate_requires_explicit_handoff"):
        target.ingest_candidate(make_candidate(source_ocs), generation=0)


def test_all_eleven_state_and_memory_roots_are_distinct() -> None:
    states = {p.state_namespace for p in LOCAL_PROFILES.values()}
    memories = {p.memory_namespace for p in LOCAL_PROFILES.values()}
    identities = {p.identity_ref for p in LOCAL_PROFILES.values()}
    assert len(states) == len(memories) == len(identities) == 11
