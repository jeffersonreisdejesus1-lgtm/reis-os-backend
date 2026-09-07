from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class InstanceRole(StrEnum):
    PRIMARY = "PRIMARY"
    CORRESPONDENT = "CORRESPONDENT"
    ASSURANCE = "ASSURANCE"
    STANDBY = "STANDBY"
    AUXILIARY = "AUXILIARY"
    TASK_SPECIALIST = "TASK_SPECIALIST"


class InstanceState(StrEnum):
    ACTIVE = "ACTIVE"
    FENCED = "FENCED"
    CLOSED = "CLOSED"


@dataclass(frozen=True, slots=True)
class ExecutionInstance:
    instance_id: str
    mission_id: str
    ocs_id: str
    host: str
    provider: str
    role: InstanceRole
    generation: int
    authority_ref: str
    state_namespace: str
    memory_namespace: str
    parent_instance_id: str | None
    lease_id: str
    state: InstanceState = InstanceState.ACTIVE


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    mission_id: str
    source_instance_id: str
    target_ocs_id: str
    payload: dict[str, Any]
    idempotency_key: str
    preferred_host: str | None = None
    target_role: InstanceRole = InstanceRole.CORRESPONDENT


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    mission_id: str
    source_instance_id: str
    target_instance_id: str
    target_ocs_id: str
    host: str
    generation: int
    idempotency_key: str
    correlation_id: str
    output: dict[str, Any]
