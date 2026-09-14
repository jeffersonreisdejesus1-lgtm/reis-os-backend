from __future__ import annotations

from typing import Any

from app.chat_runtime.contracts import DispatchRequest, HostExecutionReceipt, OCSBinding

from .contracts import ExecutionInstance, ExecutionRequest, InstanceRole
from .runtime import ExecutionPlane


class LocalEchoWorker:
    def execute(self, instance: ExecutionInstance, payload: dict[str, Any], correlation_id: str) -> dict[str, Any]:
        return {
            "executed": True,
            "instance_id": instance.instance_id,
            "ocs_id": instance.ocs_id,
            "host": instance.host,
            "provider": instance.provider,
            "role": instance.role.value,
            "correlation_id": correlation_id,
            "payload": payload,
        }


class ExecutionPlaneHostAdapter:
    def __init__(self, plane: ExecutionPlane, source_instance_id: str, target_role: InstanceRole = InstanceRole.CORRESPONDENT) -> None:
        self.plane = plane
        self.source_instance_id = source_instance_id
        self.target_role = target_role

    def invoke(self, request: DispatchRequest, target: OCSBinding, correlation_id: str) -> HostExecutionReceipt:
        receipt = self.plane.dispatch(
            ExecutionRequest(
                mission_id=request.mission_id,
                source_instance_id=self.source_instance_id,
                target_ocs_id=target.ocs_id,
                payload=request.payload,
                idempotency_key=request.idempotency_key,
                preferred_host=target.host,
                target_role=self.target_role,
            )
        )
        return HostExecutionReceipt(
            mission_id=receipt.mission_id,
            target_ocs_id=receipt.target_ocs_id,
            target_instance_id=target.instance_id,
            generation=target.generation,
            host=target.host,
            correlation_id=correlation_id,
            output={**receipt.output, "execution_plane_receipt": receipt.correlation_id},
        )
