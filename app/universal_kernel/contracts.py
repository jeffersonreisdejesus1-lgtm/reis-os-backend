from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AuthorizationDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class Evidence:
    ref: str
    passed: bool
    independent_assurer: str | None = None


@dataclass(frozen=True)
class ActionProposal:
    action_id: str
    actor: str
    ocs: str
    capability: str
    operation: str
    payload: dict[str, object]
    risk: RiskLevel
    lease_id: str | None = None
    evidence: tuple[Evidence, ...] = ()


@dataclass(frozen=True)
class AuthorizedActionEnvelope:
    action_id: str
    actor: str
    ocs: str
    capability: str
    operation: str
    payload: dict[str, object]
    lease_id: str | None
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class GovernanceResult:
    decision: AuthorizationDecision
    reason: str
    envelope: AuthorizedActionEnvelope | None = None


@dataclass(frozen=True)
class MaterialReadback:
    mutation_id: str
    state: dict[str, object]


@dataclass(frozen=True)
class ExecutionResult:
    authorized: bool
    effected: bool
    proven: bool
    reason: str
    readback: MaterialReadback | None = None


@dataclass(frozen=True)
class StateRecord:
    state_id: str
    ocs: str
    version: int
    predecessor: str | None
    payload: dict[str, object]
    verified: bool


@dataclass(frozen=True)
class VerifiedCheckpoint:
    checkpoint_id: str
    state: StateRecord


@dataclass(frozen=True)
class TraceEvent:
    event_id: str
    action_id: str
    stage: str
    predecessor: str | None
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class HandoffReceipt:
    receipt_id: str
    source_ocs: str
    target_ocs: str
    state_ref: str
    authority_transferred: bool = False


@dataclass(frozen=True)
class LPEUpdate:
    ocs: str
    category: str
    experience_ref: str
    changes_authority: bool = False
    changes_constitution: bool = False
    imports_autobiography_from_ocs: str | None = None
