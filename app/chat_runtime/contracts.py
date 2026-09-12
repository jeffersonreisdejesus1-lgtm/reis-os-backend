from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class InvocationKind(StrEnum):
    PEER_OCS = "PEER_OCS"
    AUXILIARY = "AUXILIARY"


class DispatchOutcome(StrEnum):
    EXECUTED = "EXECUTED"
    HOLD = "HOLD"


@dataclass(frozen=True, slots=True)
class OCSBinding:
    ocs_id: str
    instance_id: str
    generation: int
    authority_ref: str
    state_namespace: str
    memory_namespace: str
    host: str


@dataclass(frozen=True, slots=True)
class DispatchRequest:
    mission_id: str
    parent: OCSBinding
    target_ocs_id: str
    invocation_kind: InvocationKind
    payload: dict[str, Any]
    idempotency_key: str
    requested_host: str | None = None


@dataclass(frozen=True, slots=True)
class HostExecutionReceipt:
    mission_id: str
    target_ocs_id: str
    target_instance_id: str
    generation: int
    host: str
    correlation_id: str
    output: dict[str, Any]


@dataclass(frozen=True, slots=True)
class DispatchReceipt:
    mission_id: str
    parent_ocs_id: str
    target_ocs_id: str
    target_instance_id: str | None
    invocation_kind: InvocationKind
    host: str | None
    outcome: DispatchOutcome
    idempotency_key: str
    correlation_id: str
    output: dict[str, Any] | None = None
    hold_reason: str | None = None
