from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from hashlib import sha256
from typing import Any, Protocol

from .contracts import ExecutionInstance, ExecutionReceipt, ExecutionRequest, InstanceRole, InstanceState
from .store import ExecutionPlaneStore


class Worker(Protocol):
    def execute(self, instance: ExecutionInstance, payload: dict[str, Any], correlation_id: str) -> dict[str, Any]: ...


WorkerFactory = Callable[[ExecutionInstance], Worker]
AuthorityPolicy = Callable[[ExecutionInstance, str, InstanceRole], bool]


class ExecutionPlane:
    def __init__(
        self,
        *,
        store: ExecutionPlaneStore,
        worker_factories: Mapping[str, WorkerFactory],
        authority_policy: AuthorityPolicy,
    ) -> None:
        self.store = store
        self.worker_factories = dict(worker_factories)
        self.authority_policy = authority_policy
        self._workers: dict[str, Worker] = {}

    @staticmethod
    def _instance_id(mission_id: str, ocs_id: str, host: str, role: InstanceRole, generation: int) -> str:
        raw = f"{mission_id}:{ocs_id}:{host}:{role.value}:{generation}"
        return "instance:" + sha256(raw.encode()).hexdigest()[:24]

    def materialize(
        self,
        *,
        mission_id: str,
        ocs_id: str,
        host: str,
        provider: str,
        role: InstanceRole,
        generation: int,
        authority_ref: str,
        state_namespace: str,
        memory_namespace: str,
        lease_id: str,
        parent_instance_id: str | None = None,
    ) -> ExecutionInstance:
        if host not in self.worker_factories:
            raise ValueError("host_worker_factory_unavailable")

        if role in {InstanceRole.AUXILIARY, InstanceRole.TASK_SPECIALIST}:
            if not parent_instance_id:
                raise ValueError("auxiliary_parent_required")
            parent = self.store.load_instance(parent_instance_id)
            if parent.state is not InstanceState.ACTIVE:
                raise ValueError("parent_not_active")
            inherited_identity = (
                mission_id == parent.mission_id
                and ocs_id == parent.ocs_id
                and host == parent.host
                and provider == parent.provider
                and authority_ref == parent.authority_ref
                and state_namespace == parent.state_namespace
                and memory_namespace == parent.memory_namespace
                and lease_id == parent.lease_id
            )
            if not inherited_identity:
                raise ValueError("auxiliary_parent_identity_mismatch")

        instance = ExecutionInstance(
            instance_id=self._instance_id(mission_id, ocs_id, host, role, generation),
            mission_id=mission_id,
            ocs_id=ocs_id,
            host=host,
            provider=provider,
            role=role,
            generation=generation,
            authority_ref=authority_ref,
            state_namespace=state_namespace,
            memory_namespace=memory_namespace,
            parent_instance_id=parent_instance_id,
            lease_id=lease_id,
        )
        self.store.save_instance(instance)
        self._workers[instance.instance_id] = self.worker_factories[host](instance)
        return instance

    def materialize_auxiliary(
        self,
        *,
        parent_instance_id: str,
        auxiliary_key: str,
        role: InstanceRole = InstanceRole.AUXILIARY,
    ) -> ExecutionInstance:
        if role not in {InstanceRole.AUXILIARY, InstanceRole.TASK_SPECIALIST}:
            raise ValueError("invalid_auxiliary_role")
        if not auxiliary_key:
            raise ValueError("auxiliary_key_required")
        parent = self.store.load_instance(parent_instance_id)
        if parent.state is not InstanceState.ACTIVE:
            raise ValueError("parent_not_active")
        generation = parent.generation
        suffix = sha256(f"{parent.instance_id}:{role.value}:{auxiliary_key}".encode()).hexdigest()[:16]
        instance = ExecutionInstance(
            instance_id=f"aux:{suffix}:{generation}",
            mission_id=parent.mission_id,
            ocs_id=parent.ocs_id,
            host=parent.host,
            provider=parent.provider,
            role=role,
            generation=generation,
            authority_ref=parent.authority_ref,
            state_namespace=parent.state_namespace,
            memory_namespace=parent.memory_namespace,
            parent_instance_id=parent.instance_id,
            lease_id=parent.lease_id,
        )
        self.store.save_instance(instance)
        self._workers[instance.instance_id] = self.worker_factories[parent.host](instance)
        return instance

    def replace(self, instance_id: str) -> ExecutionInstance:
        old = self.store.load_instance(instance_id)
        if old.state is not InstanceState.ACTIVE:
            raise ValueError("instance_not_active")
        self.store.fence(old.instance_id)
        return self.materialize(
            mission_id=old.mission_id,
            ocs_id=old.ocs_id,
            host=old.host,
            provider=old.provider,
            role=old.role,
            generation=old.generation + 1,
            authority_ref=old.authority_ref,
            state_namespace=old.state_namespace,
            memory_namespace=old.memory_namespace,
            lease_id=old.lease_id,
            parent_instance_id=old.parent_instance_id,
        )

    @staticmethod
    def _request_hash(request: ExecutionRequest) -> str:
        raw = json.dumps({
            "mission_id": request.mission_id,
            "source_instance_id": request.source_instance_id,
            "target_ocs_id": request.target_ocs_id,
            "payload": request.payload,
            "preferred_host": request.preferred_host,
            "target_role": request.target_role.value,
        }, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return sha256(raw.encode()).hexdigest()

    def dispatch(self, request: ExecutionRequest) -> ExecutionReceipt:
        request_hash = self._request_hash(request)
        prior = self.store.receipt(request.mission_id, request.idempotency_key)
        if prior is not None:
            prior_hash, receipt = prior
            if prior_hash != request_hash:
                raise ValueError("execution_plane_idempotency_conflict")
            return receipt

        source = self.store.load_instance(request.source_instance_id)
        if source.state is not InstanceState.ACTIVE:
            raise ValueError("source_instance_fenced")
        if source.mission_id != request.mission_id:
            raise ValueError("source_mission_mismatch")
        if not self.authority_policy(source, request.target_ocs_id, request.target_role):
            raise ValueError("authority_policy_denied")

        host = request.preferred_host or source.host
        target = self.store.active(request.mission_id, request.target_ocs_id, host, request.target_role)
        if target is None:
            raise ValueError("target_instance_unavailable")
        if target.state is not InstanceState.ACTIVE:
            raise ValueError("target_instance_fenced")
        if request.target_role in {InstanceRole.AUXILIARY, InstanceRole.TASK_SPECIALIST} and target.ocs_id != source.ocs_id:
            raise ValueError("auxiliary_cannot_impersonate_peer_ocs")

        worker = self._workers.get(target.instance_id)
        if worker is None:
            factory = self.worker_factories.get(target.host)
            if factory is None:
                raise ValueError("host_worker_factory_unavailable")
            worker = factory(target)
            self._workers[target.instance_id] = worker
        correlation_id = "exec:" + sha256(f"{request.mission_id}:{request.idempotency_key}:{request_hash}".encode()).hexdigest()[:24]
        output = worker.execute(target, request.payload, correlation_id)
        receipt = ExecutionReceipt(
            mission_id=request.mission_id,
            source_instance_id=source.instance_id,
            target_instance_id=target.instance_id,
            target_ocs_id=target.ocs_id,
            host=target.host,
            generation=target.generation,
            idempotency_key=request.idempotency_key,
            correlation_id=correlation_id,
            output=output,
        )
        self.store.save_receipt(request_hash, receipt)
        return receipt
