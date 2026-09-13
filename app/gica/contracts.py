from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Mapping


CANONICAL_OCS_ROSTER = (
    "NÓESIS",
    "DÉDALA",
    "SÝNESIS",
    "ÍRIS",
    "LYRA",
    "SOFIA",
    "MÊTIS",
    "ÁGORA",
    "AURI",
    "SYNERGEIA",
    "TÊMIS",
)


class GicaGate(str, Enum):
    GA0 = "GA0_BOOTSTRAP"
    GA1 = "GA1_SPECIFICATION_CONSISTENCY"
    GA2 = "GA2_INDEPENDENT_ARCHITECTURAL_ASSURANCE"
    GA3 = "GA3_IMPLEMENTATION_CONTRACT"
    GA4 = "GA4_REFERENCE_IMPLEMENTATION"
    GA5 = "GA5_DETERMINISTIC_QUALIFICATION"
    GA6 = "GA6_CONCURRENCY_FAULT_QUALIFICATION"
    GA7 = "GA7_DISCOVERY_PILOT"
    GA8 = "GA8_EXPERIMENTAL_FREEZE"
    GA9 = "GA9_PAIRED_RANDOMIZED_QUALIFICATION"
    GA10 = "GA10_ADVERSARIAL_DISTRIBUTION_SHIFT"
    GA11 = "GA11_FINAL_INDEPENDENT_ASSURANCE"
    GA12 = "GA12_FINAL_FOUNDER_GATE"


class GicaProgramState(str, Enum):
    ACTIVE = "ACTIVE"
    HOLD = "HOLD"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    ABORTED_CANDIDATE = "ABORTED_CANDIDATE"
    EMERGENCY_CONTAINMENT = "EMERGENCY_CONTAINMENT"
    READY_FOR_FOUNDER = "READY_FOR_FOUNDER"
    COMPLETE = "COMPLETE"


class ProgramTransitionError(RuntimeError):
    pass


_NEXT_GATE = {
    GicaGate.GA0: GicaGate.GA1,
    GicaGate.GA1: GicaGate.GA2,
    GicaGate.GA2: GicaGate.GA3,
    GicaGate.GA3: GicaGate.GA4,
    GicaGate.GA4: GicaGate.GA5,
    GicaGate.GA5: GicaGate.GA6,
    GicaGate.GA6: GicaGate.GA7,
    GicaGate.GA7: GicaGate.GA8,
    GicaGate.GA8: GicaGate.GA9,
    GicaGate.GA9: GicaGate.GA10,
    GicaGate.GA10: GicaGate.GA11,
    GicaGate.GA11: GicaGate.GA12,
}

_ASSURANCE_REQUIRED_GATES = frozenset({GicaGate.GA2, GicaGate.GA11})


def _canonical_payload(value: object) -> bytes:
    data = asdict(value)  # type: ignore[arg-type]
    data.pop("signature", None)
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode()


def _expected_signature(value: object, key: bytes) -> str:
    return hmac.new(key, _canonical_payload(value), hashlib.sha256).hexdigest()


def _require_text(value: str, error: str) -> None:
    if not value or not value.strip():
        raise ProgramTransitionError(error)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AuthorityEvidence:
    program_id: str
    operation: str
    object_version: str
    issuer: str
    verifier: str
    issued_at: datetime
    expires_at: datetime
    policy_version: str
    provenance: str
    signature: str


@dataclass(frozen=True)
class GateEvidence:
    program_id: str
    gate: GicaGate
    object_version: str
    criteria_version: str
    lineage: tuple[str, ...]
    issuer: str
    assurer: str
    verifier: str
    issued_at: datetime
    expires_at: datetime
    policy_version: str
    provenance: str
    assurance_pass: bool
    signature: str


@dataclass(frozen=True)
class FounderAuthorizationEvidence:
    program_id: str
    gate: GicaGate
    object_version: str
    operation: str
    issuer: str
    verifier: str
    issued_at: datetime
    expires_at: datetime
    policy_version: str
    provenance: str
    signature: str


@dataclass(frozen=True)
class GicaVerificationContext:
    verifier_id: str
    authority_keys: Mapping[str, bytes]
    gate_evidence_keys: Mapping[str, bytes]
    founder_keys: Mapping[str, bytes]
    criteria_versions: Mapping[GicaGate, str]
    allowed_assurers: Mapping[GicaGate, frozenset[str]]
    independent_assurers: frozenset[str]
    reserved_founder_issuer: str
    accepted_policy_versions: frozenset[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "authority_keys", MappingProxyType(dict(self.authority_keys)))
        object.__setattr__(self, "gate_evidence_keys", MappingProxyType(dict(self.gate_evidence_keys)))
        object.__setattr__(self, "founder_keys", MappingProxyType(dict(self.founder_keys)))
        object.__setattr__(self, "criteria_versions", MappingProxyType(dict(self.criteria_versions)))
        object.__setattr__(
            self,
            "allowed_assurers",
            MappingProxyType({gate: frozenset(values) for gate, values in self.allowed_assurers.items()}),
        )

    def _verify_freshness(self, issued_at: datetime, expires_at: datetime, now: datetime) -> None:
        if issued_at.tzinfo is None or expires_at.tzinfo is None or now.tzinfo is None:
            raise ProgramTransitionError("timezone_aware_evidence_required")
        if issued_at > now or expires_at <= now or expires_at <= issued_at:
            raise ProgramTransitionError("stale_or_invalid_evidence_denied")

    def _verify_policy(self, policy_version: str) -> None:
        if policy_version not in self.accepted_policy_versions:
            raise ProgramTransitionError("untrusted_policy_version_denied")

    def verify_authority(
        self,
        evidence: AuthorityEvidence | None,
        *,
        program_id: str,
        operation: str,
        object_version: str,
        now: datetime,
    ) -> None:
        if evidence is None:
            raise ProgramTransitionError("valid_authority_required")
        if evidence.program_id != program_id:
            raise ProgramTransitionError("authority_wrong_program_denied")
        if evidence.operation != operation:
            raise ProgramTransitionError("authority_wrong_scope_denied")
        if evidence.object_version != object_version:
            raise ProgramTransitionError("authority_wrong_object_version_denied")
        if evidence.verifier != self.verifier_id:
            raise ProgramTransitionError("authority_wrong_verifier_denied")
        _require_text(evidence.provenance, "authority_provenance_required")
        self._verify_policy(evidence.policy_version)
        self._verify_freshness(evidence.issued_at, evidence.expires_at, now)
        key = self.authority_keys.get(evidence.issuer)
        if key is None:
            raise ProgramTransitionError("authority_untrusted_issuer_denied")
        if not hmac.compare_digest(evidence.signature, _expected_signature(evidence, key)):
            raise ProgramTransitionError("authority_forged_denied")

    def verify_gate_evidence(
        self,
        evidence: GateEvidence | None,
        *,
        program_id: str,
        gate: GicaGate,
        object_version: str,
        now: datetime,
    ) -> None:
        if evidence is None:
            raise ProgramTransitionError("gate_evidence_required")
        if evidence.program_id != program_id:
            raise ProgramTransitionError("evidence_wrong_program_denied")
        if evidence.gate is not gate:
            raise ProgramTransitionError("evidence_wrong_gate_denied")
        if evidence.object_version != object_version:
            raise ProgramTransitionError("evidence_wrong_object_version_denied")
        expected_criteria = self.criteria_versions.get(gate)
        if expected_criteria is None or evidence.criteria_version != expected_criteria:
            raise ProgramTransitionError("evidence_wrong_criteria_version_denied")
        if not evidence.lineage or any(not item.strip() for item in evidence.lineage):
            raise ProgramTransitionError("evidence_lineage_required")
        if evidence.verifier != self.verifier_id:
            raise ProgramTransitionError("evidence_wrong_verifier_denied")
        allowed = self.allowed_assurers.get(gate, frozenset())
        if evidence.assurer not in allowed:
            raise ProgramTransitionError("evidence_untrusted_assurer_denied")
        _require_text(evidence.provenance, "evidence_provenance_required")
        self._verify_policy(evidence.policy_version)
        self._verify_freshness(evidence.issued_at, evidence.expires_at, now)
        key = self.gate_evidence_keys.get(evidence.issuer)
        if key is None:
            raise ProgramTransitionError("evidence_untrusted_issuer_denied")
        if not hmac.compare_digest(evidence.signature, _expected_signature(evidence, key)):
            raise ProgramTransitionError("evidence_forged_denied")
        if gate in _ASSURANCE_REQUIRED_GATES:
            if not evidence.assurance_pass:
                raise ProgramTransitionError("independent_assurance_pass_required")
            if evidence.assurer not in self.independent_assurers:
                raise ProgramTransitionError("independent_assurer_required")

    def verify_founder_authorization(
        self,
        evidence: FounderAuthorizationEvidence | None,
        *,
        program_id: str,
        object_version: str,
        now: datetime,
    ) -> None:
        if evidence is None:
            raise ProgramTransitionError("founder_authorization_required")
        if evidence.program_id != program_id:
            raise ProgramTransitionError("founder_wrong_program_denied")
        if evidence.gate is not GicaGate.GA12:
            raise ProgramTransitionError("founder_authorization_outside_ga12_denied")
        if evidence.object_version != object_version:
            raise ProgramTransitionError("founder_wrong_object_version_denied")
        if evidence.operation != "COMPLETE":
            raise ProgramTransitionError("founder_wrong_operation_denied")
        if evidence.issuer != self.reserved_founder_issuer:
            raise ProgramTransitionError("founder_reserved_authority_required")
        if evidence.verifier != self.verifier_id:
            raise ProgramTransitionError("founder_wrong_verifier_denied")
        _require_text(evidence.provenance, "founder_provenance_required")
        self._verify_policy(evidence.policy_version)
        self._verify_freshness(evidence.issued_at, evidence.expires_at, now)
        key = self.founder_keys.get(evidence.issuer)
        if key is None:
            raise ProgramTransitionError("founder_reserved_authority_required")
        if not hmac.compare_digest(evidence.signature, _expected_signature(evidence, key)):
            raise ProgramTransitionError("founder_authorization_forged_denied")


@dataclass(frozen=True)
class GicaProgramContract:
    program_id: str
    gate: GicaGate
    object_version: str
    state: GicaProgramState = GicaProgramState.ACTIVE
    gate_history: tuple[GicaGate, ...] = field(default_factory=tuple)

    def validate_roster(self) -> None:
        if len(CANONICAL_OCS_ROSTER) != 11:
            raise ProgramTransitionError("canonical_11_ocs_roster_required")
        if len(set(CANONICAL_OCS_ROSTER)) != 11:
            raise ProgramTransitionError("ocs_identity_uniqueness_required")

    def transition_to(
        self,
        target: GicaGate,
        *,
        authority: AuthorityEvidence | None,
        gate_evidence: GateEvidence | None,
        verification: GicaVerificationContext,
        now: datetime | None = None,
    ) -> "GicaProgramContract":
        self.validate_roster()
        if self.state is not GicaProgramState.ACTIVE:
            raise ProgramTransitionError("program_not_in_active_state")
        expected = _NEXT_GATE.get(self.gate)
        if expected is None or target is not expected:
            raise ProgramTransitionError("non_sequential_gate_transition_denied")
        effective_now = now or _utc_now()
        operation = f"transition:{self.gate.name}->{target.name}"
        verification.verify_authority(
            authority,
            program_id=self.program_id,
            operation=operation,
            object_version=self.object_version,
            now=effective_now,
        )
        verification.verify_gate_evidence(
            gate_evidence,
            program_id=self.program_id,
            gate=self.gate,
            object_version=self.object_version,
            now=effective_now,
        )
        return GicaProgramContract(
            program_id=self.program_id,
            gate=target,
            object_version=self.object_version,
            state=(
                GicaProgramState.READY_FOR_FOUNDER
                if target is GicaGate.GA12
                else GicaProgramState.ACTIVE
            ),
            gate_history=self.gate_history + (self.gate,),
        )

    def founder_promote(
        self,
        *,
        authorization: FounderAuthorizationEvidence | None,
        verification: GicaVerificationContext,
        now: datetime | None = None,
    ) -> "GicaProgramContract":
        if self.gate is not GicaGate.GA12:
            raise ProgramTransitionError("founder_promotion_outside_ga12_denied")
        if self.state is not GicaProgramState.READY_FOR_FOUNDER:
            raise ProgramTransitionError("program_not_ready_for_founder")
        if not self.gate_history or self.gate_history[-1] is not GicaGate.GA11:
            raise ProgramTransitionError("legitimate_ga12_transition_required")
        verification.verify_founder_authorization(
            authorization,
            program_id=self.program_id,
            object_version=self.object_version,
            now=now or _utc_now(),
        )
        return GicaProgramContract(
            program_id=self.program_id,
            gate=self.gate,
            object_version=self.object_version,
            state=GicaProgramState.COMPLETE,
            gate_history=self.gate_history,
        )
