from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.cognitive_physiology.contracts import (
    Candidate,
    EpistemicGrade,
    HandoffEnvelope,
    OperationalCommitContext,
)
from app.cognitive_physiology.local_profiles import (
    LOCAL_PROFILES,
    validate_local_profiles,
)
from app.cognitive_physiology.runtime import CognitivePhysiologyRuntime
from app.profile_bindings.profiles import PROFILES, validate_profiles


def candidate(ocs: str = "NÓESIS") -> Candidate:
    return Candidate(
        candidate_id="c-1",
        source_ocs=ocs,
        content="hypothesis",
        epistemic_grade=EpistemicGrade.HYPOTHESIS,
        confidence=0.6,
        uncertainty=0.4,
        salience=0.7,
        novelty=0.5,
        risk=0.2,
        ttl_cycles=2,
    )


def runtime(ocs: str = "NÓESIS") -> CognitivePhysiologyRuntime:
    local = LOCAL_PROFILES[ocs]
    return CognitivePhysiologyRuntime(
        ocs_id=ocs,
        identity_ref=local.identity_ref,
        state_namespace=local.state_namespace,
        memory_namespace=local.memory_namespace,
    )


def valid_commit() -> OperationalCommitContext:
    return OperationalCommitContext(
        r6_clear=True,
        authority_bound=True,
        capability_bound=True,
        execution_budget_available=True,
        state_generation_current=True,
    )


def test_eleven_profiles_are_distinct_and_noesis_is_reference_only() -> None:
    validate_profiles()
    validate_local_profiles()
    assert len(PROFILES) == 11
    assert len(LOCAL_PROFILES) == 11
    assert set(PROFILES) == set(LOCAL_PROFILES)
    assert LOCAL_PROFILES["NÓESIS"].reference_role == "reference_pilot_only"
    assert (
        LOCAL_PROFILES["TÊMIS"].institutional_id
        == "REISOS::INST::ANDROID_PLAY::001"
    )


def test_local_profiles_preserve_registry_identity_and_namespaces() -> None:
    for ocs_id, local in LOCAL_PROFILES.items():
        registry = PROFILES[ocs_id]
        assert local.identity_ref == registry.identity
        assert local.state_namespace == registry.state_namespace
        assert local.memory_namespace == registry.memory_namespace
        assert local.specialty == registry.specialty


def test_workspace_broadcast_does_not_mutate_world() -> None:
    rt = runtime()
    rt.ingest_candidate(candidate(), generation=0)
    rt.cognitive_ignition("c-1", generation=0)
    assert rt.workspace.broadcast_ids == ["c-1"]
    assert rt.world.values == {}
    assert rt.world.generation == 0


@pytest.mark.parametrize(
    "context",
    [
        OperationalCommitContext(False, True, True, True, True),
        OperationalCommitContext(True, False, True, True, True),
        OperationalCommitContext(True, True, False, True, True),
        OperationalCommitContext(True, True, True, False, True),
        OperationalCommitContext(True, True, True, True, False),
    ],
)
def test_operational_commit_fails_closed_when_any_predicate_missing(
    context: OperationalCommitContext,
) -> None:
    rt = runtime()
    effects: list[str] = []
    with pytest.raises(PermissionError, match="operational_commit_denied"):
        rt.operational_commit(
            effect_id="e-1",
            context=context,
            generation=0,
            effect=lambda: effects.append("effect"),
        )
    assert effects == []


def test_operational_commit_is_idempotence_guarded() -> None:
    rt = runtime()
    effects: list[str] = []
    rt.operational_commit(
        effect_id="e-1",
        context=valid_commit(),
        generation=0,
        effect=lambda: effects.append("effect"),
    )
    with pytest.raises(PermissionError, match="duplicate_effect_denied"):
        rt.operational_commit(
            effect_id="e-1",
            context=valid_commit(),
            generation=0,
            effect=lambda: effects.append("duplicate"),
        )
    assert effects == ["effect"]


def test_institutional_commit_requires_authority_and_r6() -> None:
    rt = runtime()
    with pytest.raises(
        PermissionError,
        match="institutional_commit_authority_required",
    ):
        rt.institutional_commit(
            transition_id="t-1",
            expected_generation=0,
            changes={"status": "x"},
            authority_validated=False,
            r6_validated=True,
        )
    with pytest.raises(
        PermissionError,
        match="institutional_commit_r6_validation_required",
    ):
        rt.institutional_commit(
            transition_id="t-2",
            expected_generation=0,
            changes={"status": "x"},
            authority_validated=True,
            r6_validated=False,
        )


def test_institutional_commit_advances_generation_and_fences_old_writer() -> None:
    rt = runtime()
    new_generation = rt.institutional_commit(
        transition_id="t-1",
        expected_generation=0,
        changes={"status": "committed"},
        authority_validated=True,
        r6_validated=True,
    )
    assert new_generation == 1
    assert rt.world.values["status"] == "committed"
    with pytest.raises(PermissionError, match="stale_generation_writer"):
        rt.ingest_candidate(candidate(), generation=0)


def test_foreign_candidate_requires_handoff() -> None:
    rt = runtime("DÉDALA")
    with pytest.raises(
        PermissionError,
        match="foreign_candidate_requires_explicit_handoff",
    ):
        rt.ingest_candidate(candidate("NÓESIS"), generation=0)


def handoff(**overrides: object) -> HandoffEnvelope:
    values = dict(
        handoff_id="h-1",
        contract_version="ucp-01-v0.1",
        mission_id="m-1",
        source_ocs="NÓESIS",
        target_ocs="DÉDALA",
        source_identity_ref="identity://noesis",
        target_identity_ref="identity://dedala",
        source_generation=3,
        target_expected_generation=7,
        authority_ref="authority://dedala/current",
        authority_resolution_status="RESOLVED",
        capability_ref="capability://dedala/current",
        capability_resolution_status="RESOLVED",
        current_gate="G2",
        requested_action="architectural_review",
        allowed_actions=("architectural_review",),
        forbidden_actions=("authority_transfer",),
        assurance_context="pre-implementation",
        expected_output="review",
        acceptance_contract="no authority transfer",
        state_hash="sha256:abc",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        ttl_seconds=300,
    )
    values.update(overrides)
    return HandoffEnvelope(**values)


def test_handoff_accepts_current_generation() -> None:
    handoff().validate_for_target(target_generation=7)


def test_handoff_denies_generation_mismatch() -> None:
    with pytest.raises(PermissionError, match="generation_mismatch"):
        handoff().validate_for_target(target_generation=8)


def test_handoff_denies_unresolved_authority() -> None:
    envelope = handoff(authority_resolution_status="UNRESOLVED")
    with pytest.raises(PermissionError, match="authority_unresolved"):
        envelope.validate_for_target(target_generation=7)


def test_handoff_denies_unresolved_capability() -> None:
    envelope = handoff(capability_resolution_status="UNRESOLVED")
    with pytest.raises(PermissionError, match="capability_unresolved"):
        envelope.validate_for_target(target_generation=7)


def test_handoff_denies_stale_envelope() -> None:
    stale = handoff(
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    with pytest.raises(PermissionError, match="stale_handoff"):
        stale.validate_for_target(target_generation=7)


def test_recovery_advances_generation_and_clears_workspace() -> None:
    rt = runtime()
    rt.ingest_candidate(candidate(), generation=0)
    rt.recover_to_generation(restored_generation=0)
    assert rt.generation == 1
    assert rt.workspace.candidates == {}
    with pytest.raises(PermissionError, match="stale_generation_writer"):
        rt.ingest_candidate(candidate(), generation=0)
