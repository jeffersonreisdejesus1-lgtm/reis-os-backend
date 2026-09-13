from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType


CANONICAL_OCS_ROSTER = (
    "NÓESIS", "DÉDALA", "SÝNESIS", "ÍRIS", "LYRA", "SOFIA",
    "MÊTIS", "ÁGORA", "AURI", "SYNERGEIA", "TÊMIS",
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
    GicaGate.GA0: GicaGate.GA1, GicaGate.GA1: GicaGate.GA2,
    GicaGate.GA2: GicaGate.GA3, GicaGate.GA3: GicaGate.GA4,
    GicaGate.GA4: GicaGate.GA5, GicaGate.GA5: GicaGate.GA6,
    GicaGate.GA6: GicaGate.GA7, GicaGate.GA7: GicaGate.GA8,
    GicaGate.GA8: GicaGate.GA9, GicaGate.GA9: GicaGate.GA10,
    GicaGate.GA10: GicaGate.GA11, GicaGate.GA11: GicaGate.GA12,
}
_ASSURANCE_REQUIRED_GATES = frozenset({GicaGate.GA2, GicaGate.GA11})

# Institutional trust policy is not a transaction-call input. Identities and
# frozen policy registries are code-owned; key material is captured once from
# the runtime composition root at import/bootstrap. Missing keys fail closed.
_VERIFIER_ID = "SYNESIS-VERIFIER"
_AUTHORITY_ISSUER = "NOESIS-AUTHORITY"
_EVIDENCE_ISSUER = "SYNESIS-EVIDENCE"
_FOUNDER_ISSUER = "FOUNDER-RESERVED"
_POLICY_VERSION = "GICA-AUTHORITY-v1"
_ALLOWED_ASSURERS = MappingProxyType({gate: frozenset({"SYNESIS"}) for gate in GicaGate})
_INDEPENDENT_ASSURERS = frozenset({"SYNESIS"})
_CRITERIA_VERSIONS = MappingProxyType({gate: f"{gate.name}-CRITERIA-v1" for gate in GicaGate})


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
class TransitionReceipt:
    program_id: str
    object_version: str
    from_gate: GicaGate
    to_gate: GicaGate
    resulting_state: GicaProgramState
    criteria_version: str
    issuer: str
    verifier: str
    issued_at: datetime
    expires_at: datetime
    policy_version: str
    provenance: str
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
class _InstitutionalTrustRoot:
    authority_key: bytes | None
    gate_evidence_key: bytes | None
    founder_key: bytes | None
    bootstrap_provenance: str

    def _fresh(self, issued_at: datetime, expires_at: datetime, now: datetime) -> None:
        if issued_at.tzinfo is None or expires_at.tzinfo is None or now.tzinfo is None:
            raise ProgramTransitionError("timezone_aware_evidence_required")
        if issued_at > now or expires_at <= now or expires_at <= issued_at:
            raise ProgramTransitionError("stale_or_invalid_evidence_denied")

    def _policy(self, value: str) -> None:
        if value != _POLICY_VERSION:
            raise ProgramTransitionError("untrusted_policy_version_denied")

    def verify_authority(self, evidence: AuthorityEvidence | None, *, program_id: str, operation: str, object_version: str, now: datetime) -> None:
        if evidence is None:
            raise ProgramTransitionError("valid_authority_required")
        if self.authority_key is None:
            raise ProgramTransitionError("institutional_authority_root_unavailable")
        if evidence.program_id != program_id:
            raise ProgramTransitionError("authority_wrong_program_denied")
        if evidence.operation != operation:
            raise ProgramTransitionError("authority_wrong_scope_denied")
        if evidence.object_version != object_version:
            raise ProgramTransitionError("authority_wrong_object_version_denied")
        if evidence.issuer != _AUTHORITY_ISSUER:
            raise ProgramTransitionError("authority_untrusted_issuer_denied")
        if evidence.verifier != _VERIFIER_ID:
            raise ProgramTransitionError("authority_wrong_verifier_denied")
        _require_text(evidence.provenance, "authority_provenance_required")
        self._policy(evidence.policy_version)
        self._fresh(evidence.issued_at, evidence.expires_at, now)
        if not hmac.compare_digest(evidence.signature, _expected_signature(evidence, self.authority_key)):
            raise ProgramTransitionError("authority_forged_denied")

    def verify_gate_evidence(self, evidence: GateEvidence | None, *, program_id: str, gate: GicaGate, object_version: str, now: datetime) -> None:
        if evidence is None:
            raise ProgramTransitionError("gate_evidence_required")
        if self.gate_evidence_key is None:
            raise ProgramTransitionError("institutional_evidence_root_unavailable")
        if evidence.program_id != program_id:
            raise ProgramTransitionError("evidence_wrong_program_denied")
        if evidence.gate is not gate:
            raise ProgramTransitionError("evidence_wrong_gate_denied")
        if evidence.object_version != object_version:
            raise ProgramTransitionError("evidence_wrong_object_version_denied")
        if evidence.criteria_version != _CRITERIA_VERSIONS[gate]:
            raise ProgramTransitionError("evidence_wrong_criteria_version_denied")
        if not evidence.lineage or any(not item.strip() for item in evidence.lineage):
            raise ProgramTransitionError("evidence_lineage_required")
        if evidence.issuer != _EVIDENCE_ISSUER:
            raise ProgramTransitionError("evidence_untrusted_issuer_denied")
        if evidence.verifier != _VERIFIER_ID:
            raise ProgramTransitionError("evidence_wrong_verifier_denied")
        if evidence.assurer not in _ALLOWED_ASSURERS[gate]:
            raise ProgramTransitionError("evidence_untrusted_assurer_denied")
        _require_text(evidence.provenance, "evidence_provenance_required")
        self._policy(evidence.policy_version)
        self._fresh(evidence.issued_at, evidence.expires_at, now)
        if not hmac.compare_digest(evidence.signature, _expected_signature(evidence, self.gate_evidence_key)):
            raise ProgramTransitionError("evidence_forged_denied")
        if gate in _ASSURANCE_REQUIRED_GATES:
            if not evidence.assurance_pass:
                raise ProgramTransitionError("independent_assurance_pass_required")
            if evidence.assurer not in _INDEPENDENT_ASSURERS:
                raise ProgramTransitionError("independent_assurer_required")

    def verify_transition_receipt(self, receipt: TransitionReceipt | None, *, program_id: str, object_version: str, now: datetime) -> None:
        if receipt is None:
            raise ProgramTransitionError("legitimate_ga11_to_ga12_transition_proof_required")
        if self.gate_evidence_key is None:
            raise ProgramTransitionError("institutional_evidence_root_unavailable")
        if receipt.program_id != program_id or receipt.object_version != object_version:
            raise ProgramTransitionError("transition_proof_wrong_object_denied")
        if receipt.from_gate is not GicaGate.GA11 or receipt.to_gate is not GicaGate.GA12:
            raise ProgramTransitionError("transition_proof_wrong_route_denied")
        if receipt.resulting_state is not GicaProgramState.READY_FOR_FOUNDER:
            raise ProgramTransitionError("transition_proof_wrong_result_denied")
        if receipt.criteria_version != _CRITERIA_VERSIONS[GicaGate.GA11]:
            raise ProgramTransitionError("transition_proof_wrong_criteria_denied")
        if receipt.issuer != _EVIDENCE_ISSUER or receipt.verifier != _VERIFIER_ID:
            raise ProgramTransitionError("transition_proof_untrusted_issuer_denied")
        _require_text(receipt.provenance, "transition_proof_provenance_required")
        self._policy(receipt.policy_version)
        self._fresh(receipt.issued_at, receipt.expires_at, now)
        if not hmac.compare_digest(receipt.signature, _expected_signature(receipt, self.gate_evidence_key)):
            raise ProgramTransitionError("transition_proof_forged_denied")

    def verify_founder_authorization(self, evidence: FounderAuthorizationEvidence | None, *, program_id: str, object_version: str, now: datetime) -> None:
        if evidence is None:
            raise ProgramTransitionError("founder_authorization_required")
        if self.founder_key is None:
            raise ProgramTransitionError("institutional_founder_root_unavailable")
        if evidence.program_id != program_id:
            raise ProgramTransitionError("founder_wrong_program_denied")
        if evidence.gate is not GicaGate.GA12:
            raise ProgramTransitionError("founder_authorization_outside_ga12_denied")
        if evidence.object_version != object_version:
            raise ProgramTransitionError("founder_wrong_object_version_denied")
        if evidence.operation != "COMPLETE":
            raise ProgramTransitionError("founder_wrong_operation_denied")
        if evidence.issuer != _FOUNDER_ISSUER:
            raise ProgramTransitionError("founder_reserved_authority_required")
        if evidence.verifier != _VERIFIER_ID:
            raise ProgramTransitionError("founder_wrong_verifier_denied")
        _require_text(evidence.provenance, "founder_provenance_required")
        self._policy(evidence.policy_version)
        self._fresh(evidence.issued_at, evidence.expires_at, now)
        if not hmac.compare_digest(evidence.signature, _expected_signature(evidence, self.founder_key)):
            raise ProgramTransitionError("founder_authorization_forged_denied")


def _bootstrap_runtime_trust_root() -> _InstitutionalTrustRoot:
    def key(name: str) -> bytes | None:
        value = os.environ.get(name)
        return value.encode() if value else None
    return _InstitutionalTrustRoot(
        authority_key=key("GICA_AUTHORITY_HMAC_KEY"),
        gate_evidence_key=key("GICA_GATE_EVIDENCE_HMAC_KEY"),
        founder_key=key("GICA_FOUNDER_HMAC_KEY"),
        bootstrap_provenance=os.environ.get("GICA_TRUST_BOOTSTRAP_PROVENANCE", "runtime-bootstrap:unprovisioned"),
    )


def _make_trust_resolver():
    root = _bootstrap_runtime_trust_root()
    def resolve() -> _InstitutionalTrustRoot:
        return root
    return resolve


_resolve_institutional_trust = _make_trust_resolver()


@dataclass(frozen=True)
class GicaProgramContract:
    program_id: str
    gate: GicaGate
    object_version: str
    state: GicaProgramState = GicaProgramState.ACTIVE
    gate_history: tuple[GicaGate, ...] = field(default_factory=tuple)
    transition_receipt: TransitionReceipt | None = None

    def validate_roster(self) -> None:
        if len(CANONICAL_OCS_ROSTER) != 11:
            raise ProgramTransitionError("canonical_11_ocs_roster_required")
        if len(set(CANONICAL_OCS_ROSTER)) != 11:
            raise ProgramTransitionError("ocs_identity_uniqueness_required")

    def transition_to(self, target: GicaGate, *, authority: AuthorityEvidence | None, gate_evidence: GateEvidence | None, now: datetime | None = None) -> "GicaProgramContract":
        self.validate_roster()
        if self.state is not GicaProgramState.ACTIVE:
            raise ProgramTransitionError("program_not_in_active_state")
        expected = _NEXT_GATE.get(self.gate)
        if expected is None or target is not expected:
            raise ProgramTransitionError("non_sequential_gate_transition_denied")
        effective_now = now or _utc_now()
        root = _resolve_institutional_trust()
        root.verify_authority(authority, program_id=self.program_id, operation=f"transition:{self.gate.name}->{target.name}", object_version=self.object_version, now=effective_now)
        root.verify_gate_evidence(gate_evidence, program_id=self.program_id, gate=self.gate, object_version=self.object_version, now=effective_now)
        receipt = None
        if self.gate is GicaGate.GA11 and target is GicaGate.GA12:
            value = TransitionReceipt(self.program_id, self.object_version, self.gate, target,
                GicaProgramState.READY_FOR_FOUNDER, _CRITERIA_VERSIONS[self.gate],
                _EVIDENCE_ISSUER, _VERIFIER_ID, effective_now, gate_evidence.expires_at,
                _POLICY_VERSION, f"governed-transition:{self.program_id}:{self.object_version}:GA11->GA12", "")
            receipt = replace(value, signature=_expected_signature(value, root.gate_evidence_key))
        return GicaProgramContract(
            program_id=self.program_id,
            gate=target,
            object_version=self.object_version,
            state=GicaProgramState.READY_FOR_FOUNDER if target is GicaGate.GA12 else GicaProgramState.ACTIVE,
            gate_history=self.gate_history + (self.gate,),
            transition_receipt=receipt,
        )

    def founder_promote(self, *, authorization: FounderAuthorizationEvidence | None, now: datetime | None = None) -> "GicaProgramContract":
        if self.gate is not GicaGate.GA12:
            raise ProgramTransitionError("founder_promotion_outside_ga12_denied")
        if self.state is not GicaProgramState.READY_FOR_FOUNDER:
            raise ProgramTransitionError("program_not_ready_for_founder")
        if not self.gate_history or self.gate_history[-1] is not GicaGate.GA11:
            raise ProgramTransitionError("legitimate_ga12_transition_required")
        root = _resolve_institutional_trust()
        root.verify_transition_receipt(self.transition_receipt, program_id=self.program_id, object_version=self.object_version, now=now or _utc_now())
        root.verify_founder_authorization(
            authorization, program_id=self.program_id, object_version=self.object_version, now=now or _utc_now()
        )
        return GicaProgramContract(
            program_id=self.program_id,
            gate=self.gate,
            object_version=self.object_version,
            state=GicaProgramState.COMPLETE,
            gate_history=self.gate_history,
            transition_receipt=self.transition_receipt,
        )
