from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import NoReturn, Protocol


class DistributedOperationState(StrEnum):
    ABSENT = "ABSENT"
    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    RECONCILING = "RECONCILING"
    RECONCILED = "RECONCILED"
    HOLD = "HOLD"


@dataclass(frozen=True)
class DistributedOperationKey:
    mission_id: str
    operation_id: str
    payload_fingerprint: str
    schema_version: str


@dataclass(frozen=True)
class DistributedOperationRecord:
    key: DistributedOperationKey
    state: DistributedOperationState
    owner_id: str | None = None
    receipt_id: str | None = None
    result_reference: str | None = None


class DistributedStorageUnavailable(RuntimeError):
    """Raised when no approved distributed storage backend is bound."""


class DistributedStorageAdapter(Protocol):
    def read(
        self, key: DistributedOperationKey
    ) -> DistributedOperationRecord | None:
        ...

    def claim(
        self, key: DistributedOperationKey, owner_id: str
    ) -> DistributedOperationRecord:
        ...

    def write(
        self, record: DistributedOperationRecord
    ) -> DistributedOperationRecord:
        ...


class UnboundDistributedStorage:
    """Explicit fail-closed adapter until a backend is independently approved."""

    def _unavailable(self) -> NoReturn:
        raise DistributedStorageUnavailable(
            "distributed storage backend is not bound"
        )

    def read(
        self, key: DistributedOperationKey
    ) -> DistributedOperationRecord | None:
        self._unavailable()

    def claim(
        self, key: DistributedOperationKey, owner_id: str
    ) -> DistributedOperationRecord:
        self._unavailable()

    def write(
        self, record: DistributedOperationRecord
    ) -> DistributedOperationRecord:
        self._unavailable()
