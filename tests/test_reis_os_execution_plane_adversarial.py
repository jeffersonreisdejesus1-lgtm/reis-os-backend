from __future__ import annotations

from pathlib import Path

import pytest

from app.execution_plane import ExecutionPlane, ExecutionPlaneStore, InstanceRole, LocalEchoWorker


def allow_all(source, target_ocs_id, role):
    return True


def plane(tmp_path: Path) -> ExecutionPlane:
    return ExecutionPlane(
        store=ExecutionPlaneStore(tmp_path / "execution-plane-adversarial.sqlite3"),
        worker_factories={"GPT": lambda _: LocalEchoWorker()},
        authority_policy=allow_all,
    )


def test_direct_auxiliary_materialization_cannot_change_parent_ocs_identity(tmp_path):
    p = plane(tmp_path)
    parent = p.materialize(
        mission_id="mission:aux-hardening",
        ocs_id="NOESIS",
        host="GPT",
        provider="OpenAI",
        role=InstanceRole.PRIMARY,
        generation=1,
        authority_ref="auth:noesis",
        state_namespace="state:noesis",
        memory_namespace="memory:noesis",
        lease_id="lease:noesis",
    )

    with pytest.raises(ValueError, match="auxiliary_parent_identity_mismatch"):
        p.materialize(
            mission_id=parent.mission_id,
            ocs_id="IRIS",
            host=parent.host,
            provider=parent.provider,
            role=InstanceRole.AUXILIARY,
            generation=parent.generation,
            authority_ref=parent.authority_ref,
            state_namespace=parent.state_namespace,
            memory_namespace=parent.memory_namespace,
            lease_id=parent.lease_id,
            parent_instance_id=parent.instance_id,
        )


def test_direct_auxiliary_materialization_cannot_change_authority_or_namespaces(tmp_path):
    p = plane(tmp_path)
    parent = p.materialize(
        mission_id="mission:aux-authority",
        ocs_id="NOESIS",
        host="GPT",
        provider="OpenAI",
        role=InstanceRole.PRIMARY,
        generation=1,
        authority_ref="auth:noesis",
        state_namespace="state:noesis",
        memory_namespace="memory:noesis",
        lease_id="lease:noesis",
    )

    with pytest.raises(ValueError, match="auxiliary_parent_identity_mismatch"):
        p.materialize(
            mission_id=parent.mission_id,
            ocs_id=parent.ocs_id,
            host=parent.host,
            provider=parent.provider,
            role=InstanceRole.TASK_SPECIALIST,
            generation=parent.generation,
            authority_ref="auth:foreign",
            state_namespace="state:foreign",
            memory_namespace="memory:foreign",
            lease_id=parent.lease_id,
            parent_instance_id=parent.instance_id,
        )
