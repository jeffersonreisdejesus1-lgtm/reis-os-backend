from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from time import time

import pytest

from app.command.instance_views import (
    CommandInstanceViews,
    InstanceFilter,
    encode_instance_sse,
)
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
    status: InstanceStatus = InstanceStatus.PREPARED,
    predecessor_binding_id: str | None = None,
    organization_id: str = "org:reis-os",
    mission_id: str = "mission:ib6",
) -> InstanceBinding:
    now = time()
    return InstanceBinding(
        binding_id=binding_id,
        mission_id=mission_id,
        run_id=f"run:{mission_id}",
        organization_id=organization_id,
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
        organization_id="org:reis-os",
        filters=InstanceFilter(),
        cursor=None,
        limit=25,
        now=stored.updated_at,
    )

    item = result["items"][0]
    assert item["canonical_status"] == "persisted"
    assert item["operational_phases"] == ["awaiting_platform_instance"]
    assert item["phase_derivations"][0]["derivation_version"] == "ib6-v1"
    assert "paused" not in item["operational_phases"]


def test_empty_snapshot_is_unknown_not_healthy(tmp_path: Path) -> None:
    database = tmp_path / "instances.sqlite3"
    result = CommandInstanceViews(database).list_instances(
        organization_id="org:reis-os",
        filters=InstanceFilter(),
        cursor=None,
        limit=25,
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
    before = views.get(
        checkpointed.binding_id,
        organization_id="org:reis-os",
        now=checkpointed.updated_at,
    )
    assert "replacement_pending" not in before["operational_phases"]

    store.begin_action_saga(
        idempotency_key="idem:replace",
        binding_id=checkpointed.binding_id,
        operation="ocs_instance_replacement",
        request_fingerprint="request:replace",
        payload={"lease_id": "lease:replace"},
    )
    after = views.get(
        checkpointed.binding_id,
        organization_id="org:reis-os",
        now=checkpointed.updated_at,
    )
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

    result = CommandInstanceViews(database).comparison(
        successor.binding_id, organization_id="org:reis-os"
    )
    assert result["claim_state"] == "observed"
    assert result["verified"] is False
    assert result["boundary"] == "verified_is_not_assured"


def test_invalid_status_filter_and_cursor_fail_closed(tmp_path: Path) -> None:
    database = tmp_path / "instances.sqlite3"
    views = CommandInstanceViews(database)
    with pytest.raises(ValueError, match="command_instance_status_invalid"):
        views.list_instances(
            organization_id="org:reis-os",
            filters=InstanceFilter(canonical_status="paused"),
            cursor=None,
            limit=25,
        )


def test_all_nine_canonical_statuses_are_projected_without_pause(
    tmp_path: Path,
) -> None:
    database = tmp_path / "instances.sqlite3"
    store = InstanceBindingStore(database)
    for index, status in enumerate(InstanceStatus, start=1):
        item = binding(
            binding_id=f"binding:{index}",
            generation=index,
            mission_id=f"mission:status:{index}",
        )
        store.create(item)
        with store._connect() as connection:
            connection.execute(
                """
                UPDATE ocs_instance_bindings
                SET status=?, updated_at=?
                WHERE binding_id=?
                """,
                (status.value, item.updated_at + index, item.binding_id),
            )
    result = CommandInstanceViews(database).list_instances(
        organization_id="org:reis-os",
        filters=InstanceFilter(),
        cursor=None,
        limit=25,
        now=time() + 20,
    )
    values = {item["canonical_status"] for item in result["items"]}
    assert values == {status.value for status in InstanceStatus}
    assert "paused" not in values


def test_cross_organization_reads_and_sse_are_isolated(tmp_path: Path) -> None:
    database = tmp_path / "instances.sqlite3"
    store = InstanceBindingStore(database)
    own = binding(binding_id="binding:own")
    foreign = binding(
        binding_id="binding:foreign",
        organization_id="org:foreign",
    )
    store.create(own)
    store.create(foreign)
    views = CommandInstanceViews(database)

    result = views.list_instances(
        organization_id="org:reis-os",
        filters=InstanceFilter(),
        cursor=None,
        limit=25,
        now=time(),
    )
    assert [item["binding_id"] for item in result["items"]] == ["binding:own"]
    with pytest.raises(Exception, match="instance_binding_not_found"):
        views.get("binding:foreign", organization_id="org:reis-os")
    feed = views.journal_feed(organization_id="org:reis-os", cursor=0, limit=100)
    assert len(feed["events"]) == 1
    assert feed["events"][0]["binding_id"] == "binding:own"


def test_keyset_cursor_is_snapshot_stable_and_scope_bound(tmp_path: Path) -> None:
    database = tmp_path / "instances.sqlite3"
    store = InstanceBindingStore(database)
    for index in range(3):
        item = binding(
            binding_id=f"binding:{index}",
            generation=index + 1,
            mission_id=f"mission:cursor:{index}",
        )
        store.create(item)
        with store._connect() as connection:
            connection.execute(
                "UPDATE ocs_instance_bindings SET updated_at=? WHERE binding_id=?",
                (100.0 + index, item.binding_id),
            )
    views = CommandInstanceViews(database)
    first = views.list_instances(
        organization_id="org:reis-os",
        filters=InstanceFilter(),
        cursor=None,
        limit=2,
        now=200.0,
    )
    assert first["next_cursor"] is not None
    store.create(
        binding(
            binding_id="binding:new",
            generation=4,
            mission_id="mission:cursor:new",
        )
    )
    second = views.list_instances(
        organization_id="org:reis-os",
        filters=InstanceFilter(),
        cursor=first["next_cursor"],
        limit=2,
        now=time(),
    )
    seen = [item["binding_id"] for item in first["items"] + second["items"]]
    assert len(seen) == len(set(seen)) == 3
    with pytest.raises(ValueError, match="command_instance_cursor_scope_mismatch"):
        views.list_instances(
            organization_id="org:foreign",
            filters=InstanceFilter(),
            cursor=first["next_cursor"],
            limit=2,
            now=time(),
        )


def test_future_clock_and_unavailable_source_remain_unknown(tmp_path: Path) -> None:
    missing = tmp_path / "missing.sqlite3"
    views = CommandInstanceViews(missing)
    unavailable = views.list_instances(
        organization_id="org:reis-os",
        filters=InstanceFilter(),
        cursor=None,
        limit=25,
    )
    assert missing.exists() is False
    assert unavailable["source"]["health"] == "unavailable"
    assert unavailable["snapshot"]["freshness"] == "unknown"
    assert unavailable["total"] is None

    database = tmp_path / "instances.sqlite3"
    store = InstanceBindingStore(database)
    item = binding()
    store.create(item)
    future = CommandInstanceViews(database).list_instances(
        organization_id="org:reis-os",
        filters=InstanceFilter(),
        cursor=None,
        limit=25,
        now=item.updated_at - 1,
    )
    assert future["items"] == []
    assert future["snapshot"]["freshness"] == "unknown"


def test_sse_cursor_resumes_without_duplicate_and_exposes_fallback(
    tmp_path: Path,
) -> None:
    database = tmp_path / "instances.sqlite3"
    store = InstanceBindingStore(database)
    store.create(binding())
    views = CommandInstanceViews(database)
    first = views.journal_feed(organization_id="org:reis-os", cursor=0, limit=1)
    second = views.journal_feed(
        organization_id="org:reis-os",
        cursor=first["next_cursor"],
        limit=1,
    )
    assert len(first["events"]) == 1
    assert second["events"] == []
    wire = "".join(encode_instance_sse(second))
    assert "/v1/command/instances" in wire
    assert '"next_cursor": 1' in wire
    with pytest.raises(ValueError, match="command_instance_cursor_invalid"):
        views.list_instances(
            organization_id="org:reis-os",
            filters=InstanceFilter(),
            cursor="invalid",
            limit=25,
        )
