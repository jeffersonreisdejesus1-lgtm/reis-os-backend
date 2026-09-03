from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from enum import StrEnum
from hashlib import sha256
from hmac import compare_digest
from hmac import new as hmac_new
from json import dumps
from threading import RLock
from time import time

from .contracts import (
    ActionProposal,
    AuthorizationDecision,
    AuthorizedActionEnvelope,
    EvidenceAssessment,
    GovernanceResult,
    RiskLevel,
)


@dataclass(frozen=True)
class OCSIdentity:
    ocs: str
    specialty: str
    constitution_version: str
    allowed_capabilities: frozenset[str]
    self_assurance_allowed: bool = False


class IdentityConstitutionLoader:
    def __init__(self, identities: tuple[OCSIdentity, ...]) -> None:
        self._identities = {identity.ocs: identity for identity in identities}

    def load(self, ocs: str) -> OCSIdentity:
        try:
            return self._identities[ocs]
        except KeyError as exc:
            raise ValueError("unknown_ocs_identity") from exc


class CapabilityRegistry:
    def __init__(self) -> None:
        self._capabilities: dict[str, frozenset[str]] = {}

    def register(self, ocs: str, capabilities: frozenset[str]) -> None:
        self._capabilities[ocs] = capabilities

    def has(self, ocs: str, capability: str) -> bool:
        return capability in self._capabilities.get(ocs, frozenset())


class EvidenceEngine:
    def assess(self, proposal: ActionProposal) -> EvidenceAssessment:
        deficits: list[str] = []
        contradictions: list[str] = []
        if not proposal.evidence:
            deficits.append("evidence_required")
        failed = tuple(item.ref for item in proposal.evidence if not item.passed)
        if failed:
            deficits.append("evidence_failed")
            contradictions.extend(failed)
        if proposal.risk is RiskLevel.HIGH:
            independent = [
                evidence
                for evidence in proposal.evidence
                if evidence.independent_assurer is not None
                and evidence.independent_assurer != proposal.ocs
                and evidence.independent_assurer != proposal.actor
                and evidence.passed
            ]
            if not independent:
                deficits.append("independent_assurance_required")
        evidence_ref = proposal.evidence_assessment_ref or (
            f"assessment:{proposal.action_id}"
        )
        return EvidenceAssessment(
            sufficiency=not deficits,
            deficits=tuple(deficits),
            contradictions=tuple(contradictions),
            risk_burden=proposal.risk,
            evidence_ref=evidence_ref,
        )

    def sufficient(self, proposal: ActionProposal) -> tuple[bool, str]:
        assessment = self.assess(proposal)
        reason = (
            assessment.deficits[0]
            if assessment.deficits
            else "evidence_sufficient"
        )
        return assessment.sufficiency, reason


class LeaseState(StrEnum):
    ACTIVE = "active"
    CONSUMED = "consumed"
    RELEASED = "released"


@dataclass(frozen=True)
class AuthorityLease:
    lease_id: str
    ocs: str
    capability: str
    expires_at: float
    actor: str = ""
    issued_at: float = 0.0
    not_before: float = 0.0
    scope: tuple[str, ...] = ()
    tenant: str = ""
    context_ref: str = ""
    authority_ref: str = ""
    policy_snapshot: str = ""
    action_binding: str = ""
    object_ref_or_selector: str = ""
    trace_ref: str = ""
    max_uses: int = 1
    uses_consumed: int = 0
    revocable: bool = True
    single_use: bool = False
    state: LeaseState = LeaseState.ACTIVE
    revoked: bool = False


@dataclass
class _LeaseUsage:
    reservations: dict[str, tuple[str, int]] = field(default_factory=dict)


@dataclass(frozen=True)
class LeaseSnapshot:
    lease: AuthorityLease
    reservations: tuple[tuple[str, str, int], ...] = ()


def _canonical_snapshot_bytes(snapshot: tuple[LeaseSnapshot, ...]) -> bytes:
    payload = [asdict(item) for item in snapshot]
    return dumps(payload, sort_keys=True, separators=(",", ":")).encode()


@dataclass(frozen=True)
class AuthenticatedLeaseSnapshot:
    snapshots: tuple[LeaseSnapshot, ...]
    mac: str
    algorithm: str = "HMAC-SHA256"

    @classmethod
    def sign(
        cls,
        snapshots: tuple[LeaseSnapshot, ...],
        authentication_key: bytes,
    ) -> AuthenticatedLeaseSnapshot:
        if not authentication_key:
            raise ValueError("lease_snapshot_authentication_key_required")
        mac = hmac_new(
            authentication_key,
            _canonical_snapshot_bytes(snapshots),
            sha256,
        ).hexdigest()
        return cls(snapshots=snapshots, mac=mac)

    def authenticated(self, authentication_key: bytes) -> bool:
        if self.algorithm != "HMAC-SHA256" or not authentication_key:
            return False
        expected = hmac_new(
            authentication_key,
            _canonical_snapshot_bytes(self.snapshots),
            sha256,
        ).hexdigest()
        return compare_digest(expected, self.mac)


class AuthorityLeaseManager:
    def __init__(self) -> None:
        self._leases: dict[str, AuthorityLease] = {}
        self._usage: dict[str, _LeaseUsage] = {}
        self._lock = RLock()

    def issue(self, lease: AuthorityLease) -> None:
        now = time()
        if lease.max_uses <= 0:
            raise ValueError("lease_max_uses_must_be_positive")
        if lease.uses_consumed != 0:
            raise ValueError("lease_must_issue_unconsumed")
        if lease.single_use and lease.max_uses != 1:
            raise ValueError("single_use_lease_requires_max_uses_one")
        if not lease.scope:
            raise ValueError("lease_scope_required")
        if lease.state is not LeaseState.ACTIVE:
            raise ValueError("lease_must_issue_active")
        if lease.issued_at <= 0 or lease.issued_at > now:
            raise ValueError("lease_issued_at_invalid")
        if lease.not_before < lease.issued_at:
            raise ValueError("lease_not_before_invalid")
        if lease.expires_at <= lease.not_before:
            raise ValueError("lease_expiry_invalid")
        bindings = (
            lease.actor,
            lease.tenant,
            lease.context_ref,
            lease.authority_ref,
            lease.policy_snapshot,
            lease.action_binding,
            lease.object_ref_or_selector,
            lease.trace_ref,
        )
        if not all(bindings):
            raise ValueError("lease_binding_required")
        with self._lock:
            if lease.lease_id in self._leases:
                raise ValueError("duplicate_lease_id")
            self._leases[lease.lease_id] = lease
            self._usage[lease.lease_id] = _LeaseUsage()

    def snapshot(self) -> tuple[LeaseSnapshot, ...]:
        with self._lock:
            snapshots: list[LeaseSnapshot] = []
            for lease_id, lease in self._leases.items():
                usage = self._usage[lease_id]
                reservations = tuple(
                    sorted(
                        (key, action_id, use_index)
                        for key, (action_id, use_index) in usage.reservations.items()
                    )
                )
                snapshots.append(LeaseSnapshot(lease, reservations))
            return tuple(snapshots)

    def authenticated_snapshot(
        self,
        authentication_key: bytes,
    ) -> AuthenticatedLeaseSnapshot:
        return AuthenticatedLeaseSnapshot.sign(
            self.snapshot(),
            authentication_key,
        )

    @classmethod
    def from_snapshot(
        cls,
        snapshot: AuthenticatedLeaseSnapshot | tuple[LeaseSnapshot, ...],
        *,
        authentication_key: bytes | None = None,
    ) -> AuthorityLeaseManager:
        if not isinstance(snapshot, AuthenticatedLeaseSnapshot):
            raise ValueError("lease_snapshot_authentication_required")
        if authentication_key is None or not snapshot.authenticated(authentication_key):
            raise ValueError("lease_snapshot_authentication_failed")
        manager = cls()
        with manager._lock:
            for item in snapshot.snapshots:
                lease = item.lease
                if lease.lease_id in manager._leases:
                    raise ValueError("duplicate_lease_id")
                if lease.uses_consumed < 0 or lease.uses_consumed > lease.max_uses:
                    raise ValueError("lease_snapshot_usage_invalid")
                reservations: dict[str, tuple[str, int]] = {}
                indices: list[int] = []
                for key, action_id, use_index in item.reservations:
                    if not key or not action_id:
                        raise ValueError("lease_snapshot_reservation_binding_invalid")
                    if key in reservations:
                        raise ValueError("lease_snapshot_duplicate_idempotency_key")
                    reservations[key] = (action_id, use_index)
                    indices.append(use_index)
                expected_indices = list(range(1, lease.uses_consumed + 1))
                unique_indices = len(set(indices)) == len(indices)
                if sorted(indices) != expected_indices or not unique_indices:
                    raise ValueError("lease_snapshot_index_set_invalid")
                manager._leases[lease.lease_id] = lease
                manager._usage[lease.lease_id] = _LeaseUsage(reservations)
        return manager

    def revoke(self, lease_id: str) -> None:
        with self._lock:
            lease = self._leases[lease_id]
            if not lease.revocable:
                raise ValueError("lease_not_revocable")
            self._leases[lease_id] = replace(lease, revoked=True)

    def release(self, lease_id: str) -> None:
        with self._lock:
            lease = self._leases[lease_id]
            if lease.state is LeaseState.RELEASED:
                return
            if lease.state is not LeaseState.CONSUMED:
                raise ValueError("lease_release_requires_consumed_state")
            self._leases[lease_id] = replace(lease, state=LeaseState.RELEASED)

    def finalize(self, lease_id: str) -> LeaseState:
        with self._lock:
            lease = self._leases[lease_id]
            if lease.state is LeaseState.RELEASED:
                return LeaseState.RELEASED
            if lease.state is not LeaseState.CONSUMED:
                raise ValueError("lease_finalize_requires_consumed_state")
            if lease.single_use:
                lease = replace(lease, state=LeaseState.RELEASED)
                self._leases[lease_id] = lease
                return LeaseState.RELEASED
            return LeaseState.CONSUMED

    def lease_for(self, lease_id: str) -> AuthorityLease:
        with self._lock:
            return self._leases[lease_id]

    def validate(
        self,
        lease_id: str | None,
        ocs: str,
        capability: str,
    ) -> tuple[bool, str]:
        with self._lock:
            return self._validate_basic_unlocked(lease_id, ocs, capability)

    def validate_proposal(self, proposal: ActionProposal) -> tuple[bool, str]:
        with self._lock:
            basic_ok, reason = self._validate_basic_unlocked(
                proposal.lease_id,
                proposal.ocs,
                proposal.capability,
            )
            if not basic_ok:
                return False, reason
            assert proposal.lease_id is not None
            lease = self._leases[proposal.lease_id]
            if proposal.actor != lease.actor:
                return False, "lease_actor_mismatch"
            if proposal.action_type != lease.action_binding:
                return False, "lease_action_binding_mismatch"
            if proposal.object_ref != lease.object_ref_or_selector:
                return False, "lease_object_binding_mismatch"
            if proposal.trace_id != lease.trace_ref:
                return False, "lease_trace_binding_mismatch"
            if proposal.issued_at is None or proposal.issued_at < lease.not_before:
                return False, "lease_not_before"
            if proposal.tenant != lease.tenant:
                return False, "lease_tenant_mismatch"
            if proposal.context_ref != lease.context_ref:
                return False, "lease_context_mismatch"
            if proposal.authority_ref != lease.authority_ref:
                return False, "lease_authority_ref_mismatch"
            if proposal.policy_snapshot != lease.policy_snapshot:
                return False, "lease_policy_snapshot_mismatch"
            if not proposal.scope or not set(proposal.scope).issubset(set(lease.scope)):
                return False, "lease_scope_mismatch"
            if proposal.expires_at is None or proposal.expires_at > lease.expires_at:
                return False, "envelope_expiry_exceeds_lease"
            if proposal.expires_at <= time():
                return False, "envelope_expired"
            return True, "lease_binding_valid"

    def reserve_use(
        self,
        envelope: AuthorizedActionEnvelope,
    ) -> tuple[bool, str, int | None]:
        with self._lock:
            basic_ok, reason = self._validate_basic_unlocked(
                envelope.lease_id,
                envelope.ocs,
                envelope.capability,
            )
            if not basic_ok:
                return False, reason, None
            lease = self._leases[envelope.lease_id]
            usage = self._usage[envelope.lease_id]
            if envelope.actor != lease.actor:
                return False, "lease_actor_mismatch", None
            if envelope.action_type != lease.action_binding:
                return False, "lease_action_binding_mismatch", None
            if envelope.object_ref != lease.object_ref_or_selector:
                return False, "lease_object_binding_mismatch", None
            if envelope.trace_id != lease.trace_ref:
                return False, "lease_trace_binding_mismatch", None
            if envelope.issued_at < lease.not_before:
                return False, "lease_not_before", None
            if envelope.tenant != lease.tenant:
                return False, "lease_tenant_mismatch", None
            if envelope.context_ref != lease.context_ref:
                return False, "lease_context_mismatch", None
            if envelope.authority_ref != lease.authority_ref:
                return False, "lease_authority_ref_mismatch", None
            if envelope.policy_snapshot != lease.policy_snapshot:
                return False, "lease_policy_snapshot_mismatch", None
            valid_scope = envelope.valid_scope and set(envelope.scope).issubset(
                set(lease.scope)
            )
            if not valid_scope:
                return False, "lease_scope_mismatch", None
            if envelope.expires_at > lease.expires_at or envelope.expires_at <= time():
                return False, "envelope_expired", None
            if envelope.max_uses != lease.max_uses:
                return False, "lease_max_uses_binding_mismatch", None
            existing = usage.reservations.get(envelope.idempotency_key)
            if existing is not None:
                existing_action, use_index = existing
                if existing_action != envelope.action_id:
                    return False, "idempotency_conflict", None
                return True, "lease_use_already_reserved", use_index
            if lease.uses_consumed >= lease.max_uses:
                return False, "lease_max_uses_exhausted", None
            use_index = lease.uses_consumed + 1
            usage.reservations[envelope.idempotency_key] = (
                envelope.action_id,
                use_index,
            )
            self._leases[envelope.lease_id] = replace(
                lease,
                uses_consumed=use_index,
                state=LeaseState.CONSUMED,
            )
            return True, "lease_use_reserved", use_index

    def uses_consumed(self, lease_id: str) -> int:
        with self._lock:
            return self._leases[lease_id].uses_consumed

    def _validate_basic_unlocked(
        self,
        lease_id: str | None,
        ocs: str,
        capability: str,
    ) -> tuple[bool, str]:
        if lease_id is None:
            return False, "lease_required"
        lease = self._leases.get(lease_id)
        if lease is None:
            return False, "lease_unknown"
        if lease.revoked:
            return False, "lease_revoked"
        if lease.state is LeaseState.RELEASED:
            return False, "lease_released"
        now = time()
        if now < lease.not_before:
            return False, "lease_not_before"
        if lease.expires_at <= now:
            return False, "lease_expired"
        if lease.ocs != ocs or lease.capability != capability:
            return False, "lease_scope_mismatch"
        return True, "lease_valid"


class GovernanceEngine:
    def __init__(
        self,
        identities: IdentityConstitutionLoader,
        capabilities: CapabilityRegistry,
        evidence: EvidenceEngine,
        leases: AuthorityLeaseManager,
    ) -> None:
        self._identities = identities
        self._capabilities = capabilities
        self._evidence = evidence
        self._leases = leases

    def authorize(self, proposal: ActionProposal) -> GovernanceResult:
        identity = self._identities.load(proposal.ocs)
        if proposal.actor != proposal.ocs:
            return GovernanceResult(AuthorizationDecision.DENY, "actor_ocs_mismatch")
        if proposal.capability not in identity.allowed_capabilities:
            return GovernanceResult(
                AuthorizationDecision.DENY,
                "constitution_denies_capability",
            )
        if not self._capabilities.has(proposal.ocs, proposal.capability):
            return GovernanceResult(
                AuthorizationDecision.DENY,
                "capability_not_registered",
            )
        if any(
            evidence.independent_assurer in {proposal.ocs, proposal.actor}
            for evidence in proposal.evidence
            if evidence.independent_assurer is not None
        ):
            return GovernanceResult(
                AuthorizationDecision.DENY,
                "self_assurance_denied",
            )
        assessment = self._evidence.assess(proposal)
        if assessment.contradictions:
            return GovernanceResult(
                AuthorizationDecision.DENY,
                "evidence_failed",
                evidence_assessment=assessment,
            )
        if not assessment.sufficiency:
            return GovernanceResult(
                AuthorizationDecision.HOLD,
                assessment.deficits[0],
                evidence_assessment=assessment,
            )
        envelope_ok, envelope_reason = self._validate_envelope_contract(proposal)
        if not envelope_ok:
            return GovernanceResult(
                AuthorizationDecision.DENY,
                envelope_reason,
                evidence_assessment=assessment,
            )
        lease_ok, lease_reason = self._leases.validate_proposal(proposal)
        if not lease_ok:
            return GovernanceResult(
                AuthorizationDecision.DENY,
                lease_reason,
                evidence_assessment=assessment,
            )
        assert proposal.lease_id is not None
        assert proposal.action_type is not None
        assert proposal.issued_at is not None
        assert proposal.csp_ref is not None
        assert proposal.object_ref is not None
        assert proposal.tenant is not None
        assert proposal.context_ref is not None
        assert proposal.authority_ref is not None
        assert proposal.policy_snapshot is not None
        assert proposal.idempotency_key is not None
        assert proposal.expected_effect is not None
        assert proposal.side_effect_class is not None
        assert proposal.reversibility_class is not None
        assert proposal.recovery_ref is not None
        assert proposal.expires_at is not None
        assert proposal.evidence_assessment_ref is not None
        assert proposal.trace_id is not None
        lease = self._leases.lease_for(proposal.lease_id)
        envelope = AuthorizedActionEnvelope(
            action_id=proposal.action_id,
            actor=proposal.actor,
            ocs=proposal.ocs,
            capability=proposal.capability,
            operation=proposal.operation,
            action_type=proposal.action_type,
            issued_at=proposal.issued_at,
            payload=proposal.payload,
            lease_id=proposal.lease_id,
            evidence_refs=tuple(item.ref for item in proposal.evidence),
            csp_ref=proposal.csp_ref,
            object_ref=proposal.object_ref,
            tenant=proposal.tenant,
            context_ref=proposal.context_ref,
            scope=proposal.scope,
            valid_scope=True,
            authority_ref=proposal.authority_ref,
            policy_snapshot=proposal.policy_snapshot,
            idempotency_key=proposal.idempotency_key,
            expected_effect=proposal.expected_effect,
            side_effect_class=proposal.side_effect_class,
            reversibility_class=proposal.reversibility_class,
            recovery_ref=proposal.recovery_ref,
            expires_at=proposal.expires_at,
            evidence_assessment_ref=proposal.evidence_assessment_ref,
            max_uses=lease.max_uses,
            trace_id=proposal.trace_id,
        )
        return GovernanceResult(
            AuthorizationDecision.ALLOW,
            "authorized",
            envelope,
            assessment,
        )

    def reserve_authority(
        self,
        envelope: AuthorizedActionEnvelope,
    ) -> GovernanceResult:
        ok, reason, use_index = self._leases.reserve_use(envelope)
        if not ok or use_index is None:
            return GovernanceResult(AuthorizationDecision.DENY, reason)
        return GovernanceResult(
            AuthorizationDecision.ALLOW,
            reason,
            replace(envelope, lease_use_index=use_index),
        )

    def finalize_authority(self, envelope: AuthorizedActionEnvelope) -> LeaseState:
        return self._leases.finalize(envelope.lease_id)

    @staticmethod
    def _validate_envelope_contract(proposal: ActionProposal) -> tuple[bool, str]:
        required = {
            "action_type": proposal.action_type,
            "issued_at": proposal.issued_at,
            "csp_ref": proposal.csp_ref,
            "object_ref": proposal.object_ref,
            "tenant": proposal.tenant,
            "context_ref": proposal.context_ref,
            "authority_ref": proposal.authority_ref,
            "policy_snapshot": proposal.policy_snapshot,
            "idempotency_key": proposal.idempotency_key,
            "expected_effect": proposal.expected_effect,
            "side_effect_class": proposal.side_effect_class,
            "reversibility_class": proposal.reversibility_class,
            "recovery_ref": proposal.recovery_ref,
            "expires_at": proposal.expires_at,
            "evidence_assessment_ref": proposal.evidence_assessment_ref,
            "trace_id": proposal.trace_id,
        }
        missing = [
            name for name, value in required.items() if value is None or value == ""
        ]
        if missing:
            missing_fields = ",".join(sorted(missing))
            return False, f"action_envelope_incomplete:{missing_fields}"
        if not proposal.scope:
            return False, "action_envelope_incomplete:scope"
        assert proposal.issued_at is not None
        assert proposal.expires_at is not None
        now = time()
        if proposal.issued_at > now:
            return False, "action_envelope_issued_in_future"
        if proposal.issued_at > proposal.expires_at:
            return False, "action_envelope_invalid_lifetime"
        return True, "action_envelope_complete"
