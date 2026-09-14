from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from hashlib import sha256
from typing import Any

BOUND_HEAD = "1a58599221b44128c08f85ca8e91efbf970c8c04"
CONTRACT_ID = "GICA-GA7-MINIMUM-EXECUTION-SUBSTRATE-002"
EXPECTED_PROGRAM = "GICA"
EXPECTED_GATE = "GA7"
EXPECTED_POLICY = "GICA-AUTHORITY-v1"
ALLOWED_OPERATION = "DISCOVERY_CASE_NONMATERIAL"


class Ga7CaseState(StrEnum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    ADMITTED = "ADMITTED"
    DENIED = "DENIED"
    RUNNING = "RUNNING"
    OBSERVED = "OBSERVED"
    EXPECTED_FAILURE = "EXPECTED_FAILURE"
    HOLD = "HOLD"
    ABORTED = "ABORTED"
    UNKNOWN = "UNKNOWN"
    RECONCILING = "RECONCILING"
    STILL_UNKNOWN = "STILL_UNKNOWN"


class Ga7Disposition(StrEnum):
    HOLD = "HOLD"
    DENIED = "DENIED"
    OBSERVED = "OBSERVED"
    EXPECTED_FAILURE = "EXPECTED_FAILURE"
    ABORTED = "ABORTED"
    UNKNOWN = "UNKNOWN"
    STOPPED = "STOPPED"


class Ga7ReceiptType(StrEnum):
    GA7_DISCOVERY_CASE = "GA7_DISCOVERY_CASE"
    AUTHORITY = "AUTHORITY"
    CAPABILITY_DISCOVERY = "CAPABILITY_DISCOVERY"
    OCS_COMPOSITION = "OCS_COMPOSITION"
    ACTION = "ACTION"
    EFFECT_DENIAL_OR_NONMATERIAL_EFFECT = "EFFECT_DENIAL_OR_NONMATERIAL_EFFECT"
    RECONCILIATION = "RECONCILIATION"
    RECOVERY = "RECOVERY"
    LEARNING = "LEARNING"
    EXPERIMENT = "EXPERIMENT"
    EVIDENCE_READBACK = "EVIDENCE_READBACK"
    GA7_AGGREGATION = "GA7_AGGREGATION"


class Ga7EpistemicClass(StrEnum):
    DECLARED = "DECLARED"
    OBSERVED = "OBSERVED"
    MEASURED = "MEASURED"
    REPRODUCED = "REPRODUCED"
    INFERRED = "INFERRED"


CRITICAL_FIELDS = (
    "program_id", "gate_id", "contract_id", "mission_id", "logical_operation_id",
    "discovery_case_id", "case_version", "bound_head", "object_version", "policy_version",
)


@dataclass(frozen=True)
class Ga7DiscoveryCaseInput:
    program_id: str
    gate_id: str
    contract_id: str
    mission_id: str
    saga_id: str
    logical_operation_id: str
    discovery_case_id: str
    case_version: str
    bound_head: str
    object_version: str
    policy_version: str
    discovery_corpus_ref: str
    discovery_corpus_version: str
    task_class: str
    mission_class: str
    risk_class: str
    effect_class: str
    input_artifact_refs: tuple[str, ...]
    expected_outcome_schema: str
    participating_specialties: tuple[str, ...]
    authority_ref: str
    authority_scope: str
    capability_bindings: tuple[str, ...]
    runtime_refs: tuple[str, ...]
    budget_ref: str
    stop_rules_ref: str
    evidence_ledger_ref: str
    trace_id: str
    correlation_id: str
    generation: int
    fencing_epoch: int
    attempt_id: str
    replay_of: str
    recovery_scenario: str
    baseline_required: bool
    baseline_ref: str
    baseline_version: str
    material_effect_allowed: bool = False
    max_parallelism: int = 1
    max_recursion_depth: int = 0

    def case_key(self) -> str:
        return f"{self.discovery_case_id}:{self.case_version}"

    def identity_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), default=str)
        return sha256(payload.encode()).hexdigest()

    def validate(self) -> tuple[bool, str]:
        for name in CRITICAL_FIELDS:
            if not str(getattr(self, name) or "").strip():
                return False, f"missing_{name}"
        if self.program_id != EXPECTED_PROGRAM:
            return False, "wrong_program"
        if self.gate_id != EXPECTED_GATE:
            return False, "wrong_gate"
        if self.bound_head != BOUND_HEAD:
            return False, "wrong_bound_head"
        if self.policy_version != EXPECTED_POLICY:
            return False, "wrong_policy"
        if self.contract_id != CONTRACT_ID:
            return False, "wrong_contract"
        if self.material_effect_allowed:
            return False, "material_effect_forbidden"
        if self.max_parallelism != 1:
            return False, "parallelism_denied"
        if self.max_recursion_depth != 0:
            return False, "recursion_denied"
        return True, "valid"

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, default=str)

    @classmethod
    def from_json(cls, blob: str) -> "Ga7DiscoveryCaseInput":
        data = json.loads(blob)
        for key in ("input_artifact_refs", "participating_specialties", "capability_bindings", "runtime_refs"):
            data[key] = tuple(data.get(key) or ())
        return cls(**data)


@dataclass
class Ga7DiscoveryCaseResult:
    case_key: str
    identity_hash: str
    state: Ga7CaseState
    disposition: Ga7Disposition
    observed: str = ""
    composition: tuple[str, ...] = ()
    authority_result: str = ""
    failure: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    baseline_delta: str = ""
    learning_candidates: tuple[str, ...] = ()
    findings: tuple[str, ...] = ()
    residual_risk: str = ""
    evidence_refs: tuple[str, ...] = ()
    promoted: bool = False
    ga7_entered: bool = False

    def to_json(self) -> str:
        payload = asdict(self)
        payload["state"] = self.state.value
        payload["disposition"] = self.disposition.value
        return json.dumps(payload, sort_keys=True, default=str)

    @classmethod
    def from_json(cls, blob: str) -> "Ga7DiscoveryCaseResult":
        data = json.loads(blob)
        data["state"] = Ga7CaseState(data["state"])
        data["disposition"] = Ga7Disposition(data["disposition"])
        for key in ("composition", "learning_candidates", "findings", "evidence_refs"):
            data[key] = tuple(data.get(key) or ())
        return cls(**data)
