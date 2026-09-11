from __future__ import annotations

import os

import pytest

from app.distributed_runtime.worker import (
    NoesisMaterialWorker,
    WorkerLifecycle,
)
from app.ocs_instances.contracts import (
    BindingMaturity,
    InstanceBinding,
    InstanceStatus,
)
from app.profile_bindings.profiles import get_profile


def active_binding(ocs_id: str = "NÓESIS") -> InstanceBinding:
    profile = get_profile(ocs_id)
    return InstanceBinding(
        binding_id=f"binding:dr1:{ocs_id}",
        mission_id="mission:dr1-single-worker",
        run_id=f"run:dr1:{ocs_id}",
        organization_id="org:reis-os",
        ocs_id=ocs_id,
        profile_version=profile.version,
        profile_hash=f"profile-hash:{ocs_id}",
        identity_binding_hash=f"identity-hash:{ocs_id}",
        request_hash=f"request-hash:{ocs_id}",
        maturity=BindingMaturity.OPERATIONALLY_BOUND_L1,
        host="dr1-local-process",
        capability="cognitive-physiology",
        lease_id=f"lease:dr1:{ocs_id}",
        authority_ref=profile.authority_envelope_ref,
        scope=("cognition", "runtime-health", "runtime-checkpoint"),
        state_namespace=profile.state_namespace,
        memory_namespace=profile.memory_namespace,
        generation=7,
        platform_instance_id=None,
        challenge_hash=f"challenge:dr1:{ocs_id}",
        bootstrap_hash=f"bootstrap:dr1:{ocs_id}",
        status=InstanceStatus.ACTIVE,
        version=1,
        predecessor_binding_id=None,
        checkpoint_version=0,
        checkpoint_hash=None,
        hazel_event_hash=None,
        idempotency_key=f"idem:dr1:{ocs_id}",
        correlation_id=f"corr:dr1:{ocs_id}",
        causation_id=None,
        created_at=1.0,
        updated_at=1.0,
    )


def test_dr1_noesis_worker_runs_in_distinct_process() -> None:
    worker = NoesisMaterialWorker(active_binding())
    started = worker.start()
    try:
        assert started.ocs_id == "NÓESIS"
        assert started.logical_runtime_id == "noesis-primary"
        assert started.instance_id == worker.instance_id
        assert started.generation == 7
        assert started.pid != os.getpid()
        assert started.execution_context_id == f"process:{started.pid}"
        assert started.failure_domain_id == f"process:{started.pid}"
        assert started.lifecycle_state is WorkerLifecycle.ACTIVE
        assert worker.is_alive
    finally:
        if worker.lifecycle_state is WorkerLifecycle.ACTIVE:
            worker.stop()


def test_dr1_worker_preserves_bound_namespaces_and_authority_reference() -> None:
    binding = active_binding()
    worker = NoesisMaterialWorker(binding)
    worker.start()
    try:
        health = worker.health()
        assert health.state_namespace == binding.state_namespace
        assert health.memory_namespace == binding.memory_namespace
        assert health.authority_ref == binding.authority_ref
        assert health.profile_hash == binding.profile_hash
        assert health.monotonic_sequence >= 2
    finally:
        worker.stop()


def test_dr1_checkpoint_is_local_and_hashed() -> None:
    worker = NoesisMaterialWorker(active_binding())
    worker.start()
    try:
        checkpoint = worker.checkpoint()
        assert checkpoint.checkpoint_hash
        assert len(checkpoint.checkpoint_hash) == 64
        assert checkpoint.ocs_id == "NÓESIS"
        assert checkpoint.lifecycle_state is WorkerLifecycle.ACTIVE
    finally:
        worker.stop()


def test_dr1_stop_terminates_material_execution_context() -> None:
    worker = NoesisMaterialWorker(active_binding())
    worker.start()
    stopped = worker.stop()
    assert stopped.lifecycle_state is WorkerLifecycle.STOPPED
    assert worker.lifecycle_state is WorkerLifecycle.STOPPED
    assert not worker.is_alive


def test_dr1_rejects_non_noesis_binding() -> None:
    with pytest.raises(
        PermissionError,
        match="dr1_reference_worker_requires_noesis",
    ):
        NoesisMaterialWorker(active_binding("DÉDALA"))
