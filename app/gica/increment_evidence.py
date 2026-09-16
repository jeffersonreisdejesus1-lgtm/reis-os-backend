from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TypeVar


class EvidenceStatus(StrEnum):
    OBSERVED = "OBSERVED"
    NOT_EXECUTED = "NOT_EXECUTED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    UNKNOWN = "UNKNOWN"


class ExecutionStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_EXECUTED = "NOT_EXECUTED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    UNKNOWN = "UNKNOWN"


class EvidenceType(StrEnum):
    GITHUB = "GITHUB"
    TEST = "TEST"
    BUILD = "BUILD"
    RUNTIME = "RUNTIME"
    CODEMAGIC = "CODEMAGIC"
    LEDGER = "LEDGER"
    OTHER = "OTHER"


class ActorType(StrEnum):
    OCS = "OCS"
    HUMAN = "HUMAN"
    SYSTEM = "SYSTEM"


T = TypeVar("T")


@dataclass(frozen=True)
class EvidenceValue[T]:
    status: EvidenceStatus
    value: T | None = None
    evidence_ref: str | None = None

    def validate(self) -> None:
        if self.status is EvidenceStatus.OBSERVED and self.value is None:
            raise ValueError("observed_evidence_requires_value")
        if self.status is not EvidenceStatus.OBSERVED and self.value is not None:
            raise ValueError("non_observed_evidence_cannot_have_value")
        if self.status is EvidenceStatus.OBSERVED and not self.evidence_ref:
            raise ValueError("observed_evidence_requires_reference")


@dataclass(frozen=True)
class ExecutionEvidence:
    status: ExecutionStatus
    command: str | None = None
    exit_code: int | None = None
    started_at: str | None = None
    finished_at: str | None = None
    evidence_refs: tuple[str, ...] = ()

    def validate(self) -> None:
        if self.status is ExecutionStatus.PASS and not self.evidence_refs:
            raise ValueError("pass_execution_requires_evidence")
        if self.status is ExecutionStatus.PASS and self.exit_code not in (None, 0):
            raise ValueError("pass_execution_exit_code_must_be_zero")
        if self.status is ExecutionStatus.FAIL and self.exit_code == 0:
            raise ValueError("fail_execution_exit_code_cannot_be_zero")
        if self.status in {
            ExecutionStatus.NOT_EXECUTED,
            ExecutionStatus.NOT_AVAILABLE,
            ExecutionStatus.UNKNOWN,
        } and self.exit_code is not None:
            raise ValueError("unexecuted_execution_exit_code_must_be_null")


@dataclass(frozen=True)
class EvidenceReference:
    evidence_id: str
    evidence_type: EvidenceType
    locator: str
    digest: str | None = None

    def validate(self) -> None:
        if not self.evidence_id or not self.locator:
            raise ValueError("evidence_reference_identity_required")


@dataclass(frozen=True)
class ActorReference:
    actor_id: str
    actor_type: ActorType

    def validate(self) -> None:
        if not self.actor_id.strip():
            raise ValueError("actor_identity_required")
