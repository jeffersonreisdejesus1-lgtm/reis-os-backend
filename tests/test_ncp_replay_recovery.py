from __future__ import annotations

import pytest

from app.cognitive_physiology.local_profiles import LOCAL_PROFILES
from app.cognitive_physiology.runtime import CognitivePhysiologyRuntime


def runtime() -> CognitivePhysiologyRuntime:
    profile = LOCAL_PROFILES["NÓESIS"]
    return CognitivePhysiologyRuntime(
        ocs_id="NÓESIS",
        identity_ref=profile.identity_ref,
        state_namespace=profile.state_namespace,
        memory_namespace=profile.memory_namespace,
    )


def test_same_institutional_transition_replay_is_idempotent() -> None:
    rt = runtime()
    first_generation = rt.institutional_commit(
        transition_id="transition-1",
        expected_generation=0,
        changes={"status": "committed"},
        authority_validated=True,
        r6_validated=True,
    )
    second_generation = rt.institutional_commit(
        transition_id="transition-1",
        expected_generation=0,
        changes={"status": "must-not-reapply"},
        authority_validated=True,
        r6_validated=True,
    )
    assert first_generation == 1
    assert second_generation == 1
    assert rt.generation == 1
    assert rt.world.values == {"status": "committed"}


def test_different_transition_with_stale_generation_is_denied() -> None:
    rt = runtime()
    rt.institutional_commit(
        transition_id="transition-1",
        expected_generation=0,
        changes={"status": "committed"},
        authority_validated=True,
        r6_validated=True,
    )
    with pytest.raises(PermissionError, match="institutional_generation_mismatch"):
        rt.institutional_commit(
            transition_id="transition-2",
            expected_generation=0,
            changes={"status": "stale"},
            authority_validated=True,
            r6_validated=True,
        )


def test_recovery_fences_pre_recovery_generation() -> None:
    rt = runtime()
    rt.institutional_commit(
        transition_id="transition-1",
        expected_generation=0,
        changes={"status": "committed"},
        authority_validated=True,
        r6_validated=True,
    )
    old_generation = rt.generation
    rt.recover_to_generation(restored_generation=old_generation)
    assert rt.generation == old_generation + 1
    with pytest.raises(PermissionError, match="stale_generation_writer"):
        rt.assert_generation(old_generation)
