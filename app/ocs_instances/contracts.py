from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class InstanceBindingError(RuntimeError):
    pass


class BindingMaturity(StrEnum):
    PREPARED_UNVERIFIED = "prepared_unverified"
    OPERATIONALLY_BOUND_L1 = "operationally_bound_l1"


class InstanceStatus(StrEnum):
    PREPARED = "prepared"
    PERSISTED = "persisted"
    BOUND = "bound"
    ACTIVE = "active"
    CHECKPOINTED = "checkpointed"
    REPLACED = "replaced"
    CLOSED = "closed"
    REVOKED = "revoked"
    HOLD = "hold"


ALLOWED_TRANSITIONS: dict[InstanceStatus, frozenset[InstanceStatus]] = {
    InstanceStatus.PREPARED: frozenset(
        {InstanceStatus.PERSISTED, InstanceStatus.REVOKED, InstanceStatus.HOLD}
    ),
    InstanceStatus.PERSISTED: frozenset(
        {InstanceStatus.BOUND, InstanceStatus.REVOKED, InstanceStatus.HOLD}
    ),
    InstanceStatus.BOUND: frozenset(
        {InstanceStatus.ACTIVE, InstanceStatus.REVOKED, InstanceStatus.HOLD}
    ),
    InstanceStatus.ACTIVE: frozenset(
        {
            InstanceStatus.CHECKPOINTED,
            InstanceStatus.REPLACED,
            InstanceStatus.CLOSED,
            InstanceStatus.REVOKED,
            InstanceStatus.HOLD,
        }
    ),
    InstanceStatus.CHECKPOINTED: frozenset(
        {
            InstanceStatus.ACTIVE,
            InstanceStatus.CHECKPOINTED,
            InstanceStatus.REPLACED,
            InstanceStatus.CLOSED,
            InstanceStatus.REVOKED,
            InstanceStatus.HOLD,
        }
    ),
    InstanceStatus.REPLACED: frozenset(),
    InstanceStatus.CLOSED: frozenset(),
    InstanceStatus.REVOKED: frozenset(),
    InstanceStatus.HOLD: frozenset(),
}


def stable_run_id(
    institution_id: str,
    organization_id: str,
    mission_id: str,
    ocs_id: str,
) -> str:
    if not all((institution_id, organization_id, mission_id, ocs_id)):
        raise ValueError("institution_organization_mission_and_ocs_required")
    return f"run:{canonical_hash({
        "institution_id": institution_id,
        "organization_id": organization_id,
        "mission_id": mission_id,
        "ocs_id": ocs_id,
    })}"


def canonical_hash(value: dict[str, Any]) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class PrepareInstanceRequest:
    mission_id: str
    organization_id: str
    ocs_id: str
    capability: str
    lease_id: str
    host: str
    scope: tuple[str, ...]
    idempotency_key: str
    correlation_id: str
    actor: str
    context_ref: str
    policy_snapshot: str
    trace_ref: str
    causation_id: str | None = None


@dataclass(frozen=True, slots=True)
class InstanceBinding:
    binding_id: str
    mission_id: str
    run_id: str
    organization_id: str
    ocs_id: str
    profile_version: str
    profile_hash: str
    identity_binding_hash: str
    request_hash: str
    maturity: BindingMaturity
    host: str
    capability: str
    lease_id: str
    authority_ref: str
    scope: tuple[str, ...]
    state_namespace: str
    memory_namespace: str
    generation: int
    platform_instance_id: str | None
    challenge_hash: str
    bootstrap_hash: str
    status: InstanceStatus
    version: int
    predecessor_binding_id: str | None
    checkpoint_version: int
    checkpoint_hash: str | None
    hazel_event_hash: str | None
    idempotency_key: str
    correlation_id: str
    causation_id: str | None
    created_at: float
    updated_at: float


@dataclass(frozen=True, slots=True)
class InstanceBootstrapEnvelope:
    schema_version: str
    binding_id: str
    mission_id: str
    run_id: str
    ocs_id: str
    canonical_name: str
    identity_ref: str
    ancestry_ref: str
    constitution_ref: str
    csp_ref: str
    profile_version: str
    profile_hash: str
    identity_binding_hash: str
    maturity: BindingMaturity
    host: str
    capability: str
    lease_id: str
    authority_ref: str
    scope: tuple[str, ...]
    allowed_action_classes: tuple[str, ...]
    denied_action_classes: tuple[str, ...]
    tool_permissions: tuple[str, ...]
    state_namespace: str
    memory_namespace: str
    stop_policy: str
    handoff_policy: str
    recovery_policy: str
    generation: int
    predecessor_binding_id: str | None
    checkpoint_version: int
    checkpoint_hash: str | None
    challenge_nonce: str
    issued_at: float
    expires_at: float

    def unsigned_payload(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self) -> str:
        return canonical_hash(self.unsigned_payload())


@dataclass(frozen=True, slots=True)
class BootstrapAck:
    binding_id: str
    platform_instance_id: str
    generation: int
    bootstrap_hash: str
    identity_binding_hash: str
    challenge_nonce: str
    idempotency_key: str


def require_transition(current: InstanceStatus, target: InstanceStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InstanceBindingError(
            f"instance_transition_forbidden:{current.value}->{target.value}"
        )
