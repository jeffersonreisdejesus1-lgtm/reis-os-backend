from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Tuple, Optional

class Lifecycle(str, Enum):
    ACTIVE="ACTIVE"; HOLD="HOLD"; STOPPED="STOPPED"; FENCED="FENCED"; FAILED_CLOSED="FAILED_CLOSED"; CANCELLING="CANCELLING"
class Outcome(str, Enum):
    CONTINUE="CONTINUE"; DELEGATE="DELEGATE"; ESCALATE="ESCALATE"; HOLD="HOLD"; STOP="STOP"; FAIL_CLOSED="FAIL_CLOSED"
class PredicateSource(str, Enum):
    POLICY_DERIVED="POLICY_DERIVED"; STATE_DERIVED="STATE_DERIVED"; EVIDENCE_DERIVED="EVIDENCE_DERIVED"; MODEL_DERIVED="MODEL_DERIVED"
class Tri(str, Enum):
    TRUE="TRUE"; FALSE="FALSE"; UNKNOWN="UNKNOWN"
@dataclass(frozen=True)
class AuthorityGrant:
    authority_ref: str; scopes: FrozenSet[str]
@dataclass(frozen=True)
class CapabilityBinding:
    capability_ref: str; capabilities: FrozenSet[str]; tools: FrozenSet[str]
@dataclass(frozen=True)
class RecursionBudget:
    provider_id: str; max_depth: int; max_children: int; max_total_agents: int; max_spawns: int; max_retries: int
@dataclass
class ActorState:
    actor_id: str; identity_id: str; session_binding: str; mission_binding: str; state_namespace: str
    authority: AuthorityGrant; capability: CapabilityBinding; budget_ref: str; provider_id: str
    trace_id: str; span_id: str; generation: int; fencing_epoch: int; depth: int = 0
    lifecycle: Lifecycle = Lifecycle.ACTIVE; cancellation_policy_ref: Optional[str] = None
    parent_actor_id: Optional[str] = None; children: Tuple[str, ...] = (); confidence: float = 0.0
    assurance_satisfied: bool = False; promotion_authorized: bool = False
@dataclass(frozen=True)
class InspectionSnapshot:
    actor_id: str; identity_id: str; mission_binding: str; authority_ref: str; scopes: Tuple[str, ...]
    capabilities: Tuple[str, ...]; tools: Tuple[str, ...]; state_namespace: str; generation: int
    fencing_epoch: int; depth: int; trace_id: str; span_id: str; lifecycle: str
@dataclass(frozen=True)
class Predicate:
    name: str; value: Tri; source: PredicateSource; evidence_refs: Tuple[str, ...] = ()
@dataclass(frozen=True)
class ReflectionDecision:
    outcome: Outcome; rule: str; action_ref: Optional[str] = None
@dataclass(frozen=True)
class CancellationPolicy:
    policy_ref: str; timeout_outcome: str = "HOLD"
@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: str; actor: ActorState
@dataclass(frozen=True)
class Receipt:
    receipt_id: str; kind: str; actor_id: str; trace_id: str; span_id: str; detail: str; parent_span_id: Optional[str] = None
@dataclass(frozen=True)
class SpawnRequest:
    request_id: str; parent_actor_id: str; child_actor_id: str; child_identity_id: str
    requested_scopes: FrozenSet[str]; requested_capabilities: FrozenSet[str]; requested_tools: FrozenSet[str]
    child_namespace: str; stop_condition_ref: str; provider_id: str
@dataclass(frozen=True)
class SpawnResult:
    status: str; child_actor_id: Optional[str]; detail: str
@dataclass(frozen=True)
class JournalRecord:
    journal_id: str; kind: str; actor_id: str; trace_id: str; generation: int; fencing_epoch: int
    status: str; payload: Tuple[Tuple[str, str], ...] = ()
