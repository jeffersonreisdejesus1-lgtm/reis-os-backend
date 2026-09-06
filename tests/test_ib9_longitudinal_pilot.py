 # ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import pytest

from app.mission_runtime import (
    BindingStatus,
    MissionRuntime,
    MissionRuntimeStore,
    MissionStatus,
    RepositoryMaintenanceAdapter,
)



MISSION_ID = "mission:ib9:longitudinal-repository-maintenance"
ORG = "org:reis-os"
OCS = "SOFIA"
AUTHORITY_REF = "authority:sofia:ib9"
STATE_NAMESPACE = "state:reis-os:sofia"
MEMORY_NAMESPACE = "memory:reis-os:sofia"


def runtime(tmp_path: Path, validator=None) -> tuple[MissionRuntime, RepositoryMaintenanceAdapter]:
    repository = tmp_path / "repository"
    repository.mkdir()
    adapter = RepositoryMaintenanceAdapter(repository)
    return MissionRuntime(
        MissionRuntimeStore(tmp_path / "mission-runtime.sqlite3"),
        adapter,
        binding_validator=validator,
    ), adapter


def start(runtime_: MissionRuntime) -> MissionRuntime:
    runtime_.start(
        mission_id=MISSION_ID,
        organization_id=ORG,
        ocs_id=OCS,
        authority_ref=AUTHORITY_REF,
        state_namespace=STATE_NAMESPACE,
        memory_namespace=MEMORY_NAMESPACE,
        instance_id="work:sofia:ib9:n",
    )
    return runtime_


def effect(runtime_: MissionRuntime, key: str, path: str, content: str) -> None:
    runtime_.execute_repository_effect(
        mission_id=MISSION_ID,
        generation=1,
        instance_id="work:sofia:ib9:n",
        idempotency_key=key,
        relative_path=path,
        content=content,
    )


def test_ib9_happy_path_recovery_and_honest_binding_hold(tmp_path: Path) -> None:
    rt, adapter = runtime(tmp_path)
    started = start(rt)
    effect(rt, "ib9:effect:maintenance-note", "maintenance/IB9_PILOT.md", "phase N\n")
    checkpointed = rt.checkpoint(MISSION_ID, generation=1, instance_id="work:sofia:ib9:n")
    successor = rt.replace_instance(
        MISSION_ID, old_generation=1, old_instance_id="work:sofia:ib9:n", new_instance_id="work:sofia:ib9:n1"
    )
    recovered = rt.recover_without_transcript(MISSION_ID)
    assert started.transcript_ref is None
    assert checkpointed.checkpoint_hash is not None
    assert successor.status is MissionStatus.RECOVERED
    assert recovered.generation == 2
    replay = rt.execute_repository_effect(
        mission_id=MISSION_ID, generation=2, instance_id="work:sofia:ib9:n1",
        idempotency_key="ib9:effect:maintenance-note",
        relative_path="maintenance/IB9_PILOT.md", content="phase N\n",
    )
    assert replay.duplicate_effect is True
    assert adapter.effect_count == 1
    with pytest.raises(ValueError, match="mission_binding_validation_unknown"):
        rt.close(MISSION_ID, generation=2, instance_id="work:sofia:ib9:n1")
    assert rt.store.load(MISSION_ID).binding_status is BindingStatus.HOLD


@pytest.mark.parametrize("path", ["/tmp/escape", "../escape", "maintenance/../../escape"])
def test_h01_rejects_absolute_and_traversal(tmp_path: Path, path: str) -> None:
    rt, _ = runtime(tmp_path)
    start(rt)
    with pytest.raises(ValueError, match="repository_path_escape"):
        effect(rt, "escape:" + path, path, "blocked\n")


def test_h01_rejects_symlink(tmp_path: Path) -> None:
    rt, _ = runtime(tmp_path)
    start(rt)
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "repository" / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="repository_path_symlink"):
        effect(rt, "symlink", "link/escape.txt", "blocked\n")


def test_h03_rejects_key_content_or_path_conflict(tmp_path: Path) -> None:
    rt, _ = runtime(tmp_path)
    start(rt)
    effect(rt, "same-key", "a.txt", "one\n")
    with pytest.raises(ValueError, match="mission_effect_idempotency_conflict"):
        effect(rt, "same-key", "a.txt", "two\n")
    with pytest.raises(ValueError, match="mission_effect_idempotency_conflict"):
        effect(rt, "same-key", "b.txt", "one\n")


def test_h02_pending_claim_fails_closed_and_old_generation_is_fenced(tmp_path: Path) -> None:
    rt, _ = runtime(tmp_path)
    start(rt)
    rt.store.claim_effect("mission:ib9:longitudinal-repository-maintenance", "pending",
                          generation=1, path="pending.txt",
                          requested_hash="x" * 64)
    with pytest.raises(ValueError, match="mission_effect_pending"):
        effect(rt, "pending", "pending.txt", "content\n")
    rt.checkpoint(MISSION_ID, generation=1, instance_id="work:sofia:ib9:n")
    with pytest.raises(ValueError, match="mission_state_fenced"):
        effect(rt, "old", "old.txt", "blocked\n")


def test_h04_detects_checkpoint_material_drift(tmp_path: Path) -> None:
    rt, _ = runtime(tmp_path)
    start(rt)
    effect(rt, "state", "state.txt", "stable\n")
    checkpointed = rt.checkpoint(MISSION_ID, generation=1, instance_id="work:sofia:ib9:n")
    rt.store.path.write_bytes(rt.store.path.read_bytes().replace(
        checkpointed.checkpoint_hash.encode(), b"0" * 64
    ))
    with pytest.raises(ValueError, match="mission_checkpoint_hash_mismatch"):
        rt.recover_without_transcript(MISSION_ID)


def test_h06_validator_is_required_for_close(tmp_path: Path) -> None:
    rt, _ = runtime(tmp_path, validator=lambda _: BindingStatus.VERIFIED)
    start(rt)
    effect(rt, "state", "state.txt", "stable\n")
    rt.checkpoint(MISSION_ID, generation=1, instance_id="work:sofia:ib9:n")
    rt.replace_instance(
        MISSION_ID, old_generation=1, old_instance_id="work:sofia:ib9:n", new_instance_id="work:sofia:ib9:n1"
    )
    closed = rt.close(MISSION_ID, generation=2, instance_id="work:sofia:ib9:n1")
    assert closed.status is MissionStatus.CLOSED
    assert closed.binding_status is BindingStatus.VERIFIED
