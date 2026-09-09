from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class R7InvariantError(RuntimeError):
    pass


class GovernorFunction(str, Enum):
    """Functional governance interfaces, not a frozen identity roster."""

    STATE = "STATE"
    PROGRESS = "PROGRESS"
    TRANSITION = "TRANSITION"
    SCHEDULING = "SCHEDULING"
    COMMUNICATION = "COMMUNICATION"
    LEASE = "LEASE"
    RECOVERY = "RECOVERY"
    EVIDENCE = "EVIDENCE"


class LeaseStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FENCED = "FENCED"
    EXPIRED = "EXPIRED"
    RELEASED = "RELEASED"


class CommandStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    REPLAYED = "REPLAYED"
    DENIED = "DENIED"
    HOLD = "HOLD"


class FailurePoint(str, Enum):
    NONE = "NONE"
    AFTER_VALIDATION = "AFTER_VALIDATION"
    BEFORE_COMMIT = "BEFORE_COMMIT"
    AFTER_COMMIT = "AFTER_COMMIT"


@dataclass(frozen=True, slots=True)
class GovernorContract:
    governor_id: str
    function: GovernorFunction
    owned_state_keys: tuple[str, ...]
    readable_state_keys: tuple[str, ...]
    allowed_commands: tuple[str, ...]
    authority_ceiling_ref: str
    lease_required: bool = True
    recovery_policy: str = "GENERATIONAL"

    def __post_init__(self) -> None:
        if not self.governor_id or not self.authority_ceiling_ref:
            raise ValueError("governor_identity_and_authority_ceiling_required")
        if len(set(self.owned_state_keys)) != len(self.owned_state_keys):
            raise ValueError("duplicate_owned_state_key")
        if not set(self.owned_state_keys).issubset(set(self.readable_state_keys)):
            raise ValueError("owned_state_must_be_readable")


@dataclass(frozen=True, slots=True)
class GovernorLease:
    """Externally authorized lease bound into R7; R7 does not mint authority."""

    lease_id: str
    governor_id: str
    mission_id: str
    authority_ref: str
    authority_source_ref: str
    scope: tuple[str, ...]
    generation: int
    issued_at: float
    not_before: float
    expires_at: float
    max_uses: int = 1
    uses: int = 0
    status: LeaseStatus = LeaseStatus.ACTIVE

    def __post_init__(self) -> None:
        if not self.authority_source_ref:
            raise ValueError("lease_authority_source_required")
        if self.generation < 1:
            raise ValueError("lease_generation_must_be_positive")
        if self.not_before < self.issued_at or self.expires_at <= self.not_before:
            raise ValueError("invalid_lease_time_window")
        if self.max_uses < 1 or self.uses < 0 or self.uses > self.max_uses:
            raise ValueError("invalid_lease_use_count")


@dataclass(frozen=True, slots=True)
class GovernanceCommand:
    command_id: str
    mission_id: str
    governor_id: str
    generation: int
    lease_id: str
    authority_ref: str
    command_type: str
    write_set: dict[str, Any]
    idempotency_key: str
    expected_state_version: int
    scope: tuple[str, ...] = ()
    material_effect_requested: bool = False


@dataclass(frozen=True, slots=True)
class GovernanceTask:
    task_id: str
    mission_id: str
    governor_id: str
    command_type: str
    priority: int
    created_seq: int


@dataclass(frozen=True, slots=True)
class CommunicationEnvelope:
    message_id: str
    mission_id: str
    source_governor_id: str
    target_governor_id: str
    relation: str
    payload_ref: str
    authority_transferred: bool = False

    def __post_init__(self) -> None:
        if self.authority_transferred:
            raise R7InvariantError(
                "GOVERNOR_COMMUNICATION_MUST_NOT_TRANSFER_AUTHORITY"
            )


@dataclass(frozen=True, slots=True)
class GovernanceReceipt:
    receipt_id: str
    command_id: str
    governor_id: str
    idempotency_key: str
    status: CommandStatus
    reason: str
    generation: int
    state_version_before: int
    state_version_after: int
    mutation_count: int
    material_effect_performed: bool
    previous_hash: str
    receipt_hash: str
    readback: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RecoveryCheckpoint:
    checkpoint_id: str
    mission_id: str
    generation_snapshot: dict[str, int]
    state_version: int
    state: dict[str, Any]
    predecessor_receipt_hash: str
    receipt_count: int
    created_at: float
