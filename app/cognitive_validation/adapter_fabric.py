from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from json import dumps
from typing import Callable, Mapping

from .capability_fabric import CapabilityDiscoveryResult


class AdapterFabricError(RuntimeError):
    """Fail-closed denial raised by the COI7 adapter fabric."""


class AdapterHealth(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class AdapterRecord:
    adapter_id: str
    adapter_version: str
    capability_id: str
    capability_version: str
    endpoint: str
    input_schema_version: str
    output_schema_version: str
    health: AdapterHealth

    def validate(self) -> None:
        required = {
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "capability_id": self.capability_id,
            "capability_version": self.capability_version,
            "endpoint": self.endpoint,
            "input_schema_version": self.input_schema_version,
            "output_schema_version": self.output_schema_version,
        }
        for field, value in required.items():
            if not value.strip():
                raise AdapterFabricError(f"adapter_{field}_required")


@dataclass(frozen=True, slots=True)
class AdapterInvocationContext:
    mission_id: str
    action_receipt_id: str
    authority_receipt_id: str
    capability_discovery_receipt: str
    input_schema_version: str
    expected_output_schema_version: str

    def validate(self) -> None:
        for field in (
            "mission_id",
            "action_receipt_id",
            "authority_receipt_id",
            "capability_discovery_receipt",
            "input_schema_version",
            "expected_output_schema_version",
        ):
            if not getattr(self, field).strip():
                raise AdapterFabricError(f"adapter_context_{field}_required")


@dataclass(frozen=True, slots=True)
class AdapterExecutionReceipt:
    mission_id: str
    adapter_id: str
    adapter_version: str
    capability_id: str
    capability_version: str
    action_receipt_id: str
    authority_receipt_id: str
    discovery_receipt: str
    request_hash: str
    response_hash: str
    status: str
    execution_receipt: str


AdapterHandler = Callable[[Mapping[str, object]], Mapping[str, object]]


class InstitutionalAdapterFabric:
    """COI7 governed capability-to-adapter execution boundary.

    An adapter may run only when the exact COI6 discovery result, adapter and
    capability versions, endpoint, schemas, health, action receipt reference,
    and independent authority receipt reference are all present and coherent.
    COI7 does not mint authority and does not validate authority semantics;
    authority-aware discovery is reserved for COI8.
    """

    def __init__(self) -> None:
        self._records: dict[str, AdapterRecord] = {}
        self._handlers: dict[str, AdapterHandler] = {}

    def register(self, record: AdapterRecord, handler: AdapterHandler) -> None:
        record.validate()
        if record.adapter_id in self._records:
            raise AdapterFabricError("adapter_duplicate_registration")
        if not callable(handler):
            raise AdapterFabricError("adapter_handler_required")
        self._records[record.adapter_id] = record
        self._handlers[record.adapter_id] = handler

    def execute(
        self,
        discovery: CapabilityDiscoveryResult,
        context: AdapterInvocationContext,
        payload: Mapping[str, object],
    ) -> tuple[Mapping[str, object], AdapterExecutionReceipt]:
        context.validate()
        capability = discovery.selected_capability
        if discovery.mission_id != context.mission_id:
            raise AdapterFabricError("adapter_mission_mismatch")
        if discovery.discovery_receipt != context.capability_discovery_receipt:
            raise AdapterFabricError("adapter_discovery_receipt_mismatch")

        record = self._records.get(capability.adapter_id)
        if record is None:
            raise AdapterFabricError("adapter_not_registered")
        record.validate()
        if record.health is not AdapterHealth.HEALTHY:
            raise AdapterFabricError("adapter_not_healthy")
        if record.adapter_version != capability.adapter_version:
            raise AdapterFabricError("adapter_version_mismatch")
        if record.capability_id != capability.capability_id:
            raise AdapterFabricError("adapter_capability_mismatch")
        if record.capability_version != capability.capability_version:
            raise AdapterFabricError("adapter_capability_version_mismatch")
        if record.endpoint != capability.endpoint:
            raise AdapterFabricError("adapter_endpoint_mismatch")
        if record.input_schema_version != capability.schema_version:
            raise AdapterFabricError("adapter_capability_schema_mismatch")
        if context.input_schema_version != record.input_schema_version:
            raise AdapterFabricError("adapter_input_schema_incompatible")
        if context.expected_output_schema_version != record.output_schema_version:
            raise AdapterFabricError("adapter_output_schema_incompatible")

        handler = self._handlers[record.adapter_id]
        request_hash = self._digest(dict(payload))
        try:
            response = handler(payload)
        except Exception as exc:
            raise AdapterFabricError("adapter_execution_failed") from exc
        if not isinstance(response, Mapping):
            raise AdapterFabricError("adapter_invalid_response")
        response_hash = self._digest(dict(response))
        receipt = AdapterExecutionReceipt(
            mission_id=context.mission_id,
            adapter_id=record.adapter_id,
            adapter_version=record.adapter_version,
            capability_id=record.capability_id,
            capability_version=record.capability_version,
            action_receipt_id=context.action_receipt_id,
            authority_receipt_id=context.authority_receipt_id,
            discovery_receipt=discovery.discovery_receipt,
            request_hash=request_hash,
            response_hash=response_hash,
            status="EXECUTED_CONFIRMED",
            execution_receipt=self._digest({
                "mission_id": context.mission_id,
                "adapter_id": record.adapter_id,
                "adapter_version": record.adapter_version,
                "capability_id": record.capability_id,
                "capability_version": record.capability_version,
                "action_receipt_id": context.action_receipt_id,
                "authority_receipt_id": context.authority_receipt_id,
                "discovery_receipt": discovery.discovery_receipt,
                "request_hash": request_hash,
                "response_hash": response_hash,
                "status": "EXECUTED_CONFIRMED",
            }),
        )
        return response, receipt

    @staticmethod
    def _digest(payload: object) -> str:
        encoded = dumps(payload, sort_keys=True, separators=(",", ":"), default=list).encode()
        return sha256(encoded).hexdigest()
