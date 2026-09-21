from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .distributed_storage import (
    DistributedOperationRecord,
    DistributedOperationState,
)


@dataclass(frozen=True)
class Lease:
    owner_id: str
    operation_id: str
    fencing_token: int
    expires_at: datetime

    def is_expired(self, *, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        return current >= self.expires_at


class LeaseConflict(RuntimeError):
    """Raised when ownership cannot be acquired safely."""


class StaleOwner(RuntimeError):
    """Raised when an old owner attempts a state transition."""


def claim_is_safe(
    record: DistributedOperationRecord | None,
    *,
    owner_id: str,
) -> bool:
    if record is None:
        return True
    if record.state in {
        DistributedOperationState.SUCCEEDED,
        DistributedOperationState.FAILED,
        DistributedOperationState.RECONCILED,
        DistributedOperationState.HOLD,
    }:
        return False
    return record.owner_id in {None, owner_id}


def validate_owner(
    record: DistributedOperationRecord,
    *,
    owner_id: str,
) -> None:
    if record.owner_id != owner_id:
        raise StaleOwner("owner does not match canonical operation record")


def validate_replay(
    existing: DistributedOperationRecord | None,
    *,
    operation_id: str,
    payload_fingerprint: str,
) -> DistributedOperationRecord | None:
    if existing is None:
        return None
    if existing.key.operation_id != operation_id:
        raise LeaseConflict("operation identity mismatch")
    if existing.key.payload_fingerprint != payload_fingerprint:
        raise LeaseConflict("idempotency conflict for operation_id")
    return existing
