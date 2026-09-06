from __future__ import annotations

from pathlib import Path

import pytest

from app.mission_runtime import (
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


def test_ib9_real_longitudinal_repository_maintenance_survives_tab_loss(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    db_path = tmp_path / "mission-runtime.sqlite3"

    store_n = MissionRuntimeStore(db_path)
    adapter_n = RepositoryMaintenanceAdapter(repository)
    runtime_n = MissionRuntime(store_n, adapter_n)

    started = runtime_n.start(
        mission_id=MISSION_ID,
        organization_id=ORG,
        ocs_id=OCS,
        authority_ref=AUTHORITY_REF,
        state_namespace=STATE_NAMESPACE,
        memory_namespace=MEMORY_NAMESPACE,
        instance_id="work:sofia:ib9:n",
    )
    assert started.generation == 1
    assert started.transcript_ref is None

    first_receipt = runtime_n.execute_repository_effect(
        mission_id=MISSION_ID,
        generation=1,
        instance_id="work:sofia:ib9:n",
        idempotency_key="ib9:effect:maintenance-note",
        relative_path="maintenance/IB9_PILOT.md",
        content="IB9 longitudinal maintenance phase N\n",
    )
    assert first_receipt.after_hash == first_receipt.readback_hash
    assert adapter_n.effect_count == 1
    assert (repository / first_receipt.path).read_text() == (
        "IB9 longitudinal maintenance phase N\n"
    )

    checkpointed = runtime_n.checkpoint(
        MISSION_ID,
        generation=1,
        instance_id="work:sofia:ib9:n",
    )
    assert checkpointed.status is MissionStatus.CHECKPOINTED
    assert checkpointed.checkpoint_version == 1
    assert checkpointed.checkpoint_hash is not None

    successor = runtime_n.replace_instance(
        MISSION_ID,
        old_generation=1,
        old_instance_id="work:sofia:ib9:n",
        new_instance_id="work:sofia:ib9:n1",
    )
    assert successor.generation == 2
    assert successor.status is MissionStatus.RECOVERED
    assert successor.mission_id == started.mission_id
    assert successor.transcript_ref is None

    effects_before_fenced_attempt = adapter_n.effect_count
    with pytest.raises(ValueError, match="mission_generation_fenced"):
        runtime_n.execute_repository_effect(
            mission_id=MISSION_ID,
            generation=1,
            instance_id="work:sofia:ib9:n",
            idempotency_key="ib9:effect:forbidden-old-generation",
            relative_path="maintenance/FORBIDDEN.md",
            content="must never be written\n",
        )
    assert adapter_n.effect_count == effects_before_fenced_attempt
    assert not (repository / "maintenance/FORBIDDEN.md").exists()

    # Simulate complete loss of the chat/tab and in-memory runtime objects.
    del runtime_n
    del adapter_n
    del store_n

    store_n1 = MissionRuntimeStore(db_path)
    adapter_n1 = RepositoryMaintenanceAdapter(repository)
    runtime_n1 = MissionRuntime(store_n1, adapter_n1)

    recovered = runtime_n1.recover_without_transcript(MISSION_ID)
    assert recovered.mission_id == MISSION_ID
    assert recovered.generation == 2
    assert recovered.instance_id == "work:sofia:ib9:n1"
    assert recovered.checkpoint_hash == checkpointed.checkpoint_hash
    assert recovered.transcript_ref is None

    replay = runtime_n1.execute_repository_effect(
        mission_id=MISSION_ID,
        generation=2,
        instance_id="work:sofia:ib9:n1",
        idempotency_key="ib9:effect:maintenance-note",
        relative_path="maintenance/IB9_PILOT.md",
        content="IB9 longitudinal maintenance phase N\n",
    )
    assert replay.after_hash == first_receipt.after_hash
    assert adapter_n1.effect_count == 0

    continuation = runtime_n1.execute_repository_effect(
        mission_id=MISSION_ID,
        generation=2,
        instance_id="work:sofia:ib9:n1",
        idempotency_key="ib9:effect:continuation",
        relative_path="maintenance/IB9_CONTINUATION.md",
        content="same mission continued after replacement without transcript\n",
    )
    assert continuation.after_hash == continuation.readback_hash
    assert adapter_n1.effect_count == 1

    final_readback = adapter_n1.readback_hash(continuation.path)
    assert final_readback == continuation.after_hash

    closed = runtime_n1.close(
        MISSION_ID,
        generation=2,
        instance_id="work:sofia:ib9:n1",
    )
    assert closed.status is MissionStatus.CLOSED
    assert closed.mission_id == started.mission_id

    del runtime_n1
    del adapter_n1
    del store_n1

    cold_store = MissionRuntimeStore(db_path)
    cold_snapshot = cold_store.load(MISSION_ID)
    assert cold_snapshot.status is MissionStatus.CLOSED
    assert cold_snapshot.generation == 2
    assert cold_snapshot.transcript_ref is None
    assert cold_snapshot.mission_id == MISSION_ID

    events = cold_store.event_types(MISSION_ID)
    assert "MATERIAL_EFFECT_APPLIED" in events
    assert "MISSION_CHECKPOINTED" in events
    assert "MISSION_REPLACEMENT_PENDING" in events
    assert "MISSION_RECOVERED_WITHOUT_TRANSCRIPT" in events
    assert events[-1] == "MISSION_CLOSED"
