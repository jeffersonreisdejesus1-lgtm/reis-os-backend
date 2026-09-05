from __future__ import annotations

from dataclasses import dataclass
from unicodedata import normalize

from app.ocs_instances.contracts import (
    BindingMaturity,
    BootstrapAck,
    InstanceBinding,
    InstanceBindingError,
    InstanceStatus,
    canonical_hash,
)
from app.ocs_instances.store import InstanceBindingStore


@dataclass(frozen=True, slots=True)
class WorkSpawnReceipt:
    platform_instance_id: str
    task_name: str


class WorkInstanceBridge:
    """Registers Work effects performed by the external Nóesis orchestrator.

    There is deliberately no direct Work SDK call here. The platform spawn is an
    external effect whose returned identifier must be attached and challenged.
    """

    def __init__(self, store: InstanceBindingStore) -> None:
        self._store = store

    def attach(
        self,
        binding_id: str,
        receipt: WorkSpawnReceipt,
        *,
        expected_version: int,
        idempotency_key: str,
    ) -> InstanceBinding:
        if not receipt.platform_instance_id or not receipt.task_name:
            raise InstanceBindingError("work_spawn_receipt_incomplete")
        binding = self._store.get(binding_id)
        expected_prefix = "".join(
            character
            for character in normalize("NFKD", binding.ocs_id.casefold())
            if character.isascii()
        )
        normalized_task = receipt.task_name.casefold()
        if not (
            normalized_task == expected_prefix
            or normalized_task.startswith(f"{expected_prefix}__")
        ):
            raise InstanceBindingError("work_task_name_ocs_mismatch")
        return self._store.transition(
            binding_id,
            expected_version=expected_version,
            target=InstanceStatus.BOUND,
            idempotency_key=idempotency_key,
            event_type="OCS_PLATFORM_INSTANCE_ATTACHED",
            platform_instance_id=receipt.platform_instance_id,
            payload={"task_name": receipt.task_name},
        )

    def acknowledge(
        self,
        ack: BootstrapAck,
        *,
        expected_version: int,
    ) -> InstanceBinding:
        binding = self._store.get(ack.binding_id)
        if binding.status is not InstanceStatus.BOUND:
            raise InstanceBindingError("instance_must_be_bound_before_ack")
        if binding.platform_instance_id != ack.platform_instance_id:
            raise InstanceBindingError("platform_instance_binding_mismatch")
        if binding.generation != ack.generation:
            raise InstanceBindingError("instance_generation_mismatch")
        if binding.bootstrap_hash != ack.bootstrap_hash:
            raise InstanceBindingError("bootstrap_hash_mismatch")
        if binding.identity_binding_hash != ack.identity_binding_hash:
            raise InstanceBindingError("identity_binding_hash_mismatch")
        if binding.challenge_hash != canonical_hash(
            {"nonce": ack.challenge_nonce}
        ):
            raise InstanceBindingError("bootstrap_challenge_failed")
        return self._store.transition(
            ack.binding_id,
            expected_version=expected_version,
            target=InstanceStatus.ACTIVE,
            idempotency_key=ack.idempotency_key,
            event_type="OCS_BOOTSTRAP_ACKNOWLEDGED",
            maturity=BindingMaturity.OPERATIONALLY_BOUND_L1,
            payload={
                "generation": ack.generation,
                "bootstrap_hash": ack.bootstrap_hash,
            },
        )
