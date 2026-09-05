from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from time import time

import pytest

from app.command.instance_views import CommandInstanceViews, InstanceFilter
from app.ocs_instances.contracts import (
    BindingMaturity,
    InstanceBinding,
    InstanceStatus,
)
from app.ocs_instances.store import InstanceBindingStore


def binding(
    *,
    binding_id: str = "binding:1",
    generation: int = 1,
    status: InstanceStatus = InstanceStatus.PERSISTED,
    predecessor_binding_id: str | None = None,
) -> InstanceBinding:
    now = time()
    return InstanceBinding(
        binding_id=binding_id,
        mission_id="mission:ib6",
        run_id="run:ib6",
        organization_id="org:reis-os",
        ocs_id="ÍRIS",
        profile_version="r2-v0.1.0",
        profile_hash="profile-hash",
        identity_binding_hash="identity-hash",
        request_hash=f"request:{binding_id}",
        maturity=BindingMaturity.OPERATIONALLY_BOUND_L1,
        host="ChatGPT Work",
        capability="experience_contract",
        lease_id=f"lease:{binding_id}",
        authority_ref="authority:iris",
        scope=("mission:ib6",),
        state_namespace="state:iris",
        memory_namespace="memory:iris",
        generation=generation,
        platform_instance_id=None,
        challenge_hash="challenge",
        bootstrap_hash="bootstrap",
        status=status,
        version=1,
        predecessor_binding_id=predecessor_binding_id,
        checkpoint_version=0,
        checkpoint_hash=None,
        hazel_event_hash=None,
        idempotency_key=f"idem:{binding_id}",
        correlation_id="corr:ib6",
        causation_id=None,
        created_at=now,
        updated_at=now,
    )


def test_projection_preserves_canonical_status_and_derives_awaiting_phase(
    tmp_path: Path,
) -> None:
    database = tmp_path / "instances.sqlite3"
    store = InstanceBindingStore(database)
    store.create(binding())
    stored = store.transition(
        "binding:1",
        expected_version=1,
        target=InstanceStatus.PERSISTED,
        idempotency_key="idem:persist",
        event_type="OCS_INSTANCE_PERSISTED",
    )

    result = CommandInstanceViews(database).list_instances(
        filters=InstanceFilter(), cursor=None, limit=25, now=stored.updated_at
    )

    item = result["items"][0]
    assert item["canonical_status"] == "persisted"
    assert item["operational_phases"] == ["awaiting_platform_instance"]
    assert item["phase_derivations"][0]["derivation_version"] == "ib6-v1"
    assert "paused" not in item["operational_phases"]


def test_empty_snapshot_is_unknown_not_healthy(tmp_path: Path) -> None:
    database = tmp_path / "instances.sqlite3"
    result = CommandInstanceViews(database).list_instances(
        filters=InstanceFilter(), cursor=None, limit=25
    )
    assert result["items"] == []
    assert result["snapshot"]["freshness"] == "unknown"


def test_replacement_phase_requires_material_saga(tmp_path: Path) -> None:
    database = tmp_path / "instances.sqlite3"
    store = InstanceBindingStore(database)
    store.create(binding())
    persisted = store.transition(
        "binding:1",
        expected_version=1,
        target=InstanceStatus.PERSISTED,
        idempotency_key="idem:persist",
        event_type="OCS_INSTANCE_PERSISTED",
    )
    bound = store.transition(
        "binding:1",
        expected_version=persisted.version,
        target=InstanceStatus.BOUND,
        idempotency_key="idem:bound",
        event_type="OCS_INSTANCE_BOUND",
        platform_instance_id="work:iris:1",
    )
    active = store.transition(
        "binding:1",
        expected_version=bound.version,
        target=InstanceStatus.ACTIVE,
        idempotency_key="idem:active",
        event_type="OCS_INSTANCE_ACTIVE",
    )
    checkpointed = store.transition(
        "binding:1",
        expected_version=active.version,
        target=InstanceStatus.CHECKPOINTED,
        idempotency_key="idem:checkpoint",
        event_type="OCS_INSTANCE_CHECKPOINTED",
        checkpoint_version=1,
        checkpoint_hash="payload-hash",
        hazel_event_hash="event-hash",
    )
    views = CommandInstanceViews(database)
    before = views.get(checkpointed.binding_id, now=checkpointed.updated_at)
    assert "replacement_pending" not in before["operational_phases"]

    store.begin_action_saga(
        idempotency_key="idem:replace",
        binding_id=checkpointed.binding_id,
        operation="ocs_instance_replacement",
        request_fingerprint="request:replace",
        payload={"lease_id": "lease:replace"},
    )
    after = views.get(checkpointed.binding_id, now=checkpointed.updated_at)
    assert "replacement_pending" in after["operational_phases"]


def test_comparison_never_promotes_verified_to_assured(tmp_path: Path) -> None:
    database = tmp_path / "instances.sqlite3"
    store = InstanceBindingStore(database)
    predecessor = binding(status=InstanceStatus.PREPARED)
    store.create(predecessor)
    checkpointed = replace(
        predecessor,
        status=InstanceStatus.CHECKPOINTED,
        version=5,
        checkpoint_version=1,
        checkpoint_hash="payload-hash",
        hazel_event_hash="event-hash",
    )
    with store._connect() as connection:
        values = store._values(checkpointed)
        connection.execute(
            """
            UPDATE ocs_instance_bindings SET status=:status, version=:version,
              checkpoint_version=:checkpoint_version,
              checkpoint_hash=:checkpoint_hash, hazel_event_hash=:hazel_event_hash
            WHERE binding_id=:binding_id
            """,
            values,
        )
    successor = replace(
        binding(
            binding_id="binding:2",
            generation=2,
            predecessor_binding_id="binding:1",
        ),
        profile_hash=checkpointed.profile_hash,
        identity_binding_hash=checkpointed.identity_binding_hash,
        authority_ref=checkpointed.authority_ref,
        state_namespace=checkpointed.state_namespace,
        memory_namespace=checkpointed.memory_namespace,
    )
    store.create(successor)

    result = CommandInstanceViews(database).comparison(successor.binding_id)
    assert result["claim_state"] == "verified"
    assert result["boundary"] == "verified_is_not_assured"


def test_invalid_status_filter_and_cursor_fail_closed(tmp_path: Path) -> None:
    database = tmp_path / "instances.sqlite3"
    views = CommandInstanceViews(database)
    with pytest.raises(ValueError, match="command_instance_status_invalid"):
        views.list_instances(
            filters=InstanceFilter(canonical_status="paused"),
            cursor=None,
            limit=25,
        )
    with pytest.raises(ValueError, match="command_instance_cursor_invalid"):
        views.list_instances(filters=InstanceFilter(), cursor="invalid", limit=25)
