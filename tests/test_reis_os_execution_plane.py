from __future__ import annotations

from pathlib import Path

import pytest

from app.chat_runtime import DispatchOutcome, DispatchRequest, InvocationKind, OCSBinding, ReisOSChatRuntime
from app.execution_plane import (
    ExecutionPlane,
    ExecutionPlaneHostAdapter,
    ExecutionPlaneStore,
    ExecutionRequest,
    InstanceRole,
    InstanceState,
    LocalEchoWorker,
)


def allow_all(source, target_ocs_id, role):
    return True


def plane(tmp_path: Path) -> ExecutionPlane:
    return ExecutionPlane(
        store=ExecutionPlaneStore(tmp_path / "execution-plane.sqlite3"),
        worker_factories={
            "GPT": lambda _: LocalEchoWorker(),
            "GROK": lambda _: LocalEchoWorker(),
            "CLAUDE": lambda _: LocalEchoWorker(),
        },
        authority_policy=allow_all,
    )


def materialize_core(p: ExecutionPlane):
    noesis_gpt = p.materialize(
        mission_id="mission:ep:1", ocs_id="NOESIS", host="GPT", provider="OpenAI",
        role=InstanceRole.PRIMARY, generation=1, authority_ref="auth:noesis",
        state_namespace="state:noesis", memory_namespace="memory:noesis", lease_id="lease:noesis:1",
    )
    iris_grok = p.materialize(
        mission_id="mission:ep:1", ocs_id="IRIS", host="GROK", provider="xAI",
        role=InstanceRole.CORRESPONDENT, generation=1, authority_ref="auth:iris",
        state_namespace="state:iris", memory_namespace="memory:iris", lease_id="lease:iris:1",
    )
    return noesis_gpt, iris_grok


def test_peer_ocs_executes_across_hosts(tmp_path):
    p = plane(tmp_path)
    noesis, iris = materialize_core(p)
    receipt = p.dispatch(ExecutionRequest(
        mission_id="mission:ep:1", source_instance_id=noesis.instance_id,
        target_ocs_id="IRIS", preferred_host="GROK", target_role=InstanceRole.CORRESPONDENT,
        payload={"task": "ux review"}, idempotency_key="peer-1",
    ))
    assert receipt.target_instance_id == iris.instance_id
    assert receipt.host == "GROK"
    assert receipt.output["executed"] is True
    assert receipt.output["ocs_id"] == "IRIS"


def test_same_ocs_can_have_federated_correspondents(tmp_path):
    p = plane(tmp_path)
    noesis_gpt = p.materialize(
        mission_id="mission:federated", ocs_id="NOESIS", host="GPT", provider="OpenAI",
        role=InstanceRole.PRIMARY, generation=1, authority_ref="auth:noesis",
        state_namespace="state:noesis", memory_namespace="memory:noesis", lease_id="lease:noesis:gpt",
    )
    noesis_grok = p.materialize(
        mission_id="mission:federated", ocs_id="NOESIS", host="GROK", provider="xAI",
        role=InstanceRole.CORRESPONDENT, generation=1, authority_ref="auth:noesis",
        state_namespace="state:noesis", memory_namespace="memory:noesis", lease_id="lease:noesis:grok",
    )
    receipt = p.dispatch(ExecutionRequest(
        mission_id="mission:federated", source_instance_id=noesis_gpt.instance_id,
        target_ocs_id="NOESIS", preferred_host="GROK", target_role=InstanceRole.CORRESPONDENT,
        payload={"task": "federated correspondence"}, idempotency_key="federated-1",
    ))
    assert receipt.target_instance_id == noesis_grok.instance_id
    assert receipt.output["provider"] == "xAI"


def test_multiple_auxiliaries_inherit_parent_identity_and_authority(tmp_path):
    p = plane(tmp_path)
    parent = p.materialize(
        mission_id="mission:aux", ocs_id="NOESIS", host="GPT", provider="OpenAI",
        role=InstanceRole.PRIMARY, generation=3, authority_ref="auth:noesis",
        state_namespace="state:noesis", memory_namespace="memory:noesis", lease_id="lease:noesis:3",
    )
    a1 = p.materialize_auxiliary(parent_instance_id=parent.instance_id, auxiliary_key="research")
    a2 = p.materialize_auxiliary(parent_instance_id=parent.instance_id, auxiliary_key="synthesis")
    assert a1.instance_id != a2.instance_id
    for aux in (a1, a2):
        assert aux.ocs_id == parent.ocs_id
        assert aux.authority_ref == parent.authority_ref
        assert aux.state_namespace == parent.state_namespace
        assert aux.memory_namespace == parent.memory_namespace
        assert aux.parent_instance_id == parent.instance_id


def test_auxiliary_cannot_impersonate_peer_ocs(tmp_path):
    p = plane(tmp_path)
    parent = p.materialize(
        mission_id="mission:aux-deny", ocs_id="NOESIS", host="GPT", provider="OpenAI",
        role=InstanceRole.PRIMARY, generation=1, authority_ref="auth:noesis",
        state_namespace="state:noesis", memory_namespace="memory:noesis", lease_id="lease:noesis",
    )
    p.materialize_auxiliary(parent_instance_id=parent.instance_id, auxiliary_key="bounded")
    with pytest.raises(ValueError, match="target_instance_unavailable"):
        p.dispatch(ExecutionRequest(
            mission_id="mission:aux-deny", source_instance_id=parent.instance_id,
            target_ocs_id="IRIS", preferred_host="GPT", target_role=InstanceRole.AUXILIARY,
            payload={"task": "impersonate"}, idempotency_key="aux-deny",
        ))


def test_replacement_fences_old_generation(tmp_path):
    p = plane(tmp_path)
    old = p.materialize(
        mission_id="mission:replace", ocs_id="NOESIS", host="GPT", provider="OpenAI",
        role=InstanceRole.PRIMARY, generation=1, authority_ref="auth:noesis",
        state_namespace="state:noesis", memory_namespace="memory:noesis", lease_id="lease:noesis",
    )
    new = p.replace(old.instance_id)
    assert p.store.load_instance(old.instance_id).state is InstanceState.FENCED
    assert new.generation == 2
    with pytest.raises(ValueError, match="source_instance_fenced"):
        p.dispatch(ExecutionRequest(
            mission_id="mission:replace", source_instance_id=old.instance_id,
            target_ocs_id="NOESIS", preferred_host="GPT", target_role=InstanceRole.PRIMARY,
            payload={"task": "stale"}, idempotency_key="stale",
        ))


def test_idempotent_replay_and_divergent_retry(tmp_path):
    p = plane(tmp_path)
    noesis, _ = materialize_core(p)
    req = ExecutionRequest(
        mission_id="mission:ep:1", source_instance_id=noesis.instance_id,
        target_ocs_id="IRIS", preferred_host="GROK", target_role=InstanceRole.CORRESPONDENT,
        payload={"task": "same"}, idempotency_key="idem",
    )
    first = p.dispatch(req)
    assert p.dispatch(req) == first
    with pytest.raises(ValueError, match="execution_plane_idempotency_conflict"):
        p.dispatch(ExecutionRequest(
            mission_id=req.mission_id, source_instance_id=req.source_instance_id,
            target_ocs_id=req.target_ocs_id, preferred_host=req.preferred_host,
            target_role=req.target_role, payload={"task": "different"}, idempotency_key=req.idempotency_key,
        ))


def test_durable_restart_rehydrates_worker_from_store(tmp_path):
    db = tmp_path / "durable.sqlite3"
    p1 = ExecutionPlane(store=ExecutionPlaneStore(db), worker_factories={"GPT": lambda _: LocalEchoWorker()}, authority_policy=allow_all)
    source = p1.materialize(
        mission_id="mission:restart", ocs_id="NOESIS", host="GPT", provider="OpenAI",
        role=InstanceRole.PRIMARY, generation=1, authority_ref="auth:noesis",
        state_namespace="state:noesis", memory_namespace="memory:noesis", lease_id="lease:noesis",
    )
    target = p1.materialize(
        mission_id="mission:restart", ocs_id="IRIS", host="GPT", provider="OpenAI",
        role=InstanceRole.CORRESPONDENT, generation=1, authority_ref="auth:iris",
        state_namespace="state:iris", memory_namespace="memory:iris", lease_id="lease:iris",
    )
    p2 = ExecutionPlane(store=ExecutionPlaneStore(db), worker_factories={"GPT": lambda _: LocalEchoWorker()}, authority_policy=allow_all)
    receipt = p2.dispatch(ExecutionRequest(
        mission_id="mission:restart", source_instance_id=source.instance_id,
        target_ocs_id="IRIS", preferred_host="GPT", target_role=InstanceRole.CORRESPONDENT,
        payload={"task": "after restart"}, idempotency_key="restart",
    ))
    assert receipt.target_instance_id == target.instance_id
    assert receipt.output["executed"] is True


def test_chat_runtime_to_execution_plane_bridge(tmp_path):
    p = plane(tmp_path)
    noesis, iris = materialize_core(p)
    parent_binding = OCSBinding(
        ocs_id="NOESIS", instance_id=noesis.instance_id, generation=noesis.generation,
        authority_ref=noesis.authority_ref, state_namespace=noesis.state_namespace,
        memory_namespace=noesis.memory_namespace, host="GPT",
    )
    target_binding = OCSBinding(
        ocs_id="IRIS", instance_id=iris.instance_id, generation=iris.generation,
        authority_ref=iris.authority_ref, state_namespace=iris.state_namespace,
        memory_namespace=iris.memory_namespace, host="GROK",
    )
    chat = ReisOSChatRuntime(
        bindings={"NOESIS": parent_binding, "IRIS": target_binding},
        host_adapters={"GROK": ExecutionPlaneHostAdapter(p, noesis.instance_id)},
        authority_policy=lambda parent, target, kind: True,
    )
    receipt = chat.dispatch(DispatchRequest(
        mission_id="mission:ep:1", parent=parent_binding, target_ocs_id="IRIS",
        invocation_kind=InvocationKind.PEER_OCS, payload={"task": "same surface"}, idempotency_key="bridge",
    ))
    assert receipt.outcome is DispatchOutcome.EXECUTED
    assert receipt.target_instance_id == iris.instance_id
    assert receipt.output["executed"] is True
    assert "execution_plane_receipt" in receipt.output


def test_missing_worker_factory_fails_closed(tmp_path):
    p = ExecutionPlane(store=ExecutionPlaneStore(tmp_path / "missing.sqlite3"), worker_factories={"GPT": lambda _: LocalEchoWorker()}, authority_policy=allow_all)
    with pytest.raises(ValueError, match="host_worker_factory_unavailable"):
        p.materialize(
            mission_id="mission:missing", ocs_id="IRIS", host="GROK", provider="xAI",
            role=InstanceRole.CORRESPONDENT, generation=1, authority_ref="auth:iris",
            state_namespace="state:iris", memory_namespace="memory:iris", lease_id="lease:iris",
        )
