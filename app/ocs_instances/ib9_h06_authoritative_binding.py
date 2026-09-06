from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.command.instance_views import CommandInstanceViews
from app.ocs_instances.contracts import (
    BootstrapAck,
    InstanceBinding,
    InstanceStatus,
    PrepareInstanceRequest,
)
from app.ocs_instances.recovery import OCSInstanceRecovery, RecoveryResult
from app.ocs_instances.service import OCSInstanceBinder
from app.ocs_instances.work_bridge import WorkInstanceBridge, WorkSpawnReceipt


class IB9H06ReconciliationStep(StrEnum):
    VALIDATE_BINDING = "validate_binding"
    ATTACH_WORK_RECEIPT = "attach_work_receipt"
    ACKNOWLEDGE_BOOTSTRAP = "acknowledge_bootstrap"
    CHECKPOINT = "checkpoint"
    REPLACE = "replace"
    RECOVER = "recover"
    READBACK = "readback"
    HOLD = "hold"


class IB9H06StopCondition(StrEnum):
    AUTHORITY_UNKNOWN = "authority_unknown"
    BINDING_DRIFT = "binding_drift"
    LEASE_INVALID = "lease_invalid"
    CHECKPOINT_REQUIRED = "checkpoint_required"
    EXTERNAL_EFFECT_UNPROVEN = "external_effect_unproven"
    COMMAND_MUTATION_REQUESTED = "command_mutation_requested"
    PREDECESSOR_MISMATCH = "predecessor_mismatch"


@dataclass(frozen=True, slots=True)
class IB9H06ReconciliationReceipt:
    mission_id: str
    run_id: str
    binding_id: str
    step: IB9H06ReconciliationStep
    outcome: str
    idempotency_key: str
    correlation_id: str
    causation_id: str | None
    predecessor_binding_id: str | None
    generation: int
    authority_ref: str
    checkpoint_version: int
    checkpoint_hash: str | None
    hazel_event_hash: str | None
    command_projection_read: bool
    stop_condition: IB9H06StopCondition | None = None


class IB9H06AuthoritativeBindingRuntime:
    """IB9 H-06 authoritative binding/reconciliation facade over existing services."""

    def __init__(
        self,
        *,
        binder: OCSInstanceBinder,
        recovery: OCSInstanceRecovery,
        work_bridge: WorkInstanceBridge,
        command_views: CommandInstanceViews,
    ) -> None:
        self._binder = binder
        self._recovery = recovery
        self._work_bridge = work_bridge
        self._command = command_views

    @staticmethod
    def next_valid_step(binding: InstanceBinding) -> IB9H06ReconciliationStep:
        if binding.status in {InstanceStatus.PREPARED, InstanceStatus.PERSISTED}:
            return IB9H06ReconciliationStep.ATTACH_WORK_RECEIPT
        if binding.status is InstanceStatus.BOUND:
            return IB9H06ReconciliationStep.ACKNOWLEDGE_BOOTSTRAP
        if binding.status is InstanceStatus.ACTIVE:
            return IB9H06ReconciliationStep.CHECKPOINT
        if binding.status is InstanceStatus.CHECKPOINTED:
            return IB9H06ReconciliationStep.REPLACE
        if binding.status is InstanceStatus.REPLACED:
            return IB9H06ReconciliationStep.RECOVER
        return IB9H06ReconciliationStep.HOLD

    def reconcile(
        self, *, organization_id: str, mission_id: str, ocs_id: str
    ) -> tuple[RecoveryResult, dict[str, Any]]:
        result = self._recovery.recover_instance(organization_id, mission_id, ocs_id)
        projection = self._command.get(
            result.binding.binding_id, organization_id=organization_id
        )
        return result, projection

    def attach_work_receipt(
        self,
        binding_id: str,
        receipt: WorkSpawnReceipt,
        *,
        expected_version: int,
        idempotency_key: str,
    ) -> IB9H06ReconciliationReceipt:
        binding = self._work_bridge.attach(
            binding_id, receipt, expected_version=expected_version,
            idempotency_key=idempotency_key,
        )
        return self._receipt(
            binding, IB9H06ReconciliationStep.ATTACH_WORK_RECEIPT, idempotency_key
        )

    def acknowledge_bootstrap(
        self, ack: BootstrapAck, *, expected_version: int
    ) -> IB9H06ReconciliationReceipt:
        binding = self._work_bridge.acknowledge(ack, expected_version=expected_version)
        return self._receipt(
            binding, IB9H06ReconciliationStep.ACKNOWLEDGE_BOOTSTRAP,
            ack.idempotency_key,
        )

    def checkpoint(
        self,
        binding_id: str,
        *,
        authority: PrepareInstanceRequest,
        platform_instance_id: str,
        generation: int,
        expected_version: int,
        state: dict[str, object],
        idempotency_key: str,
    ) -> IB9H06ReconciliationReceipt:
        binding = self._binder.checkpoint(
            binding_id, authority=authority, platform_instance_id=platform_instance_id,
            generation=generation, expected_version=expected_version, state=state,
            idempotency_key=idempotency_key,
        )
        return self._receipt(
            binding, IB9H06ReconciliationStep.CHECKPOINT, idempotency_key
        )

    def replace(
        self,
        binding_id: str,
        request: PrepareInstanceRequest,
        *,
        platform_instance_id: str,
        generation: int,
        expected_version: int,
        replacement_idempotency_key: str,
    ) -> IB9H06ReconciliationReceipt:
        binding, _ = self._binder.replace_instance(
            binding_id, request, platform_instance_id=platform_instance_id,
            generation=generation, expected_version=expected_version,
            replacement_idempotency_key=replacement_idempotency_key,
        )
        return self._receipt(
            binding, IB9H06ReconciliationStep.REPLACE, replacement_idempotency_key
        )

    def readback(
        self, *, binding_id: str, organization_id: str
    ) -> dict[str, Any]:
        return self._command.get(binding_id, organization_id=organization_id)

    @staticmethod
    def _receipt(
        binding: InstanceBinding, step: IB9H06ReconciliationStep, idempotency_key: str
    ) -> IB9H06ReconciliationReceipt:
        return IB9H06ReconciliationReceipt(
            mission_id=binding.mission_id, run_id=binding.run_id,
            binding_id=binding.binding_id, step=step, outcome="EXECUTED",
            idempotency_key=idempotency_key, correlation_id=binding.correlation_id,
            causation_id=binding.causation_id,
            predecessor_binding_id=binding.predecessor_binding_id,
            generation=binding.generation, authority_ref=binding.authority_ref,
            checkpoint_version=binding.checkpoint_version,
            checkpoint_hash=binding.checkpoint_hash,
            hazel_event_hash=binding.hazel_event_hash,
            command_projection_read=False,
        )

    @staticmethod
    def stop_conditions() -> tuple[IB9H06StopCondition, ...]:
        return tuple(IB9H06StopCondition)
