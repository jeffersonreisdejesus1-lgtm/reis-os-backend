from __future__ import annotations

from dataclasses import dataclass, field, replace
from threading import RLock
from time import time

from .contracts import (
    ActionProposal,
    AuthorizationDecision,
    AuthorizedActionEnvelope,
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
    def sufficient(self, proposal: ActionProposal) -> tuple[bool, str]:
        if not proposal.evidence:
            return False, "evidence_required"
        if not all(evidence.passed for evidence in proposal.evidence):
            return False, "evidence_failed"
        if proposal.risk is RiskLevel.HIGH:
            independent = [
                evidence
                for evidence in proposal.evidence
                if evidence.independent_assurer is not None
                and evidence.independent_assurer != proposal.ocs
                and evidence.independent_assurer != proposal.actor
            ]
            if not independent:
                return False, "independent_assurance_required"
        return True, "evidence_sufficient"


@dataclass(frozen=True)
class AuthorityLease:
    lease_id: str
    ocs: str
    capability: str
    expires_at: float
    scope: tuple[str, ...] = ()
    tenant: str = ""
    context_ref: str = ""
    authority_ref: str = ""
    policy_snapshot: str = ""
    max_uses: int = 1
    revoked: bool = False


@dataclass
class _LeaseUsage:
    uses_consumed: int = 0
    reservations: dict[str, tuple[str, int]] = field(default_factory=dict)


class AuthorityLeaseManager:
    def __init__(self) -> None:
        self._leases: dict[str, AuthorityLease] = {}
        self._usage: dict[str, _LeaseUsage] = {}
        self._lock = RLock()

    def issue(self, lease: AuthorityLease) -> None:
        if lease.max_uses <= 0:
            raise ValueError("lease_max_uses_must_be_positive")
        if not lease.scope:
            raise ValueError("lease_scope_required")
        if not all(
            (lease.tenant, lease.context_ref, lease.authority_ref, lease.policy_snapshot)
        ):
            raise ValueError("lease_binding_required")
        with self._lock:
            if lease.lease_id in self._leases:
                raise ValueError("duplicate_lease_id")
            self._leases[lease.lease_id] = lease
            self._usage[lease.lease_id] = _LeaseUsage()

    def revoke(self, lease_id: str) -> None:
        with self._lock:
            lease = self._leases[lease_id]
            self._leases[lease_id] = replace(lease, revoked=True)

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
        """Atomically revalidate and consume authority before adapter resolution."""
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
            if envelope.tenant != lease.tenant:
                return False, "lease_tenant_mismatch", None
            if envelope.context_ref != lease.context_ref:
                return False, "lease_context_mismatch", None
            if envelope.authority_ref != lease.authority_ref:
                return False, "lease_authority_ref_mismatch", None
            if envelope.policy_snapshot != lease.policy_snapshot:
                return False, "lease_policy_snapshot_mismatch", None
            if not envelope.valid_scope or not set(envelope.scope).issubset(set(lease.scope)):
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

            if usage.uses_consumed >= lease.max_uses:
                return False, "lease_max_uses_exhausted", None

            usage.uses_consumed += 1
            use_index = usage.uses_consumed
            usage.reservations[envelope.idempotency_key] = (
                envelope.action_id,
                use_index,
            )
            return True, "lease_use_reserved", use_index

    def uses_consumed(self, lease_id: str) -> int:
        with self._lock:
            return self._usage[lease_id].uses_consumed

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
        if lease.expires_at <= time():
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
            return GovernanceResult(
                AuthorizationDecision.DENY,
                "actor_ocs_mismatch",
            )
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
        evidence_ok, evidence_reason = self._evidence.sufficient(proposal)
        if not evidence_ok:
            return GovernanceResult(AuthorizationDecision.DENY, evidence_reason)
        envelope_ok, envelope_reason = self._validate_envelope_contract(proposal)
        if not envelope_ok:
            return GovernanceResult(AuthorizationDecision.DENY, envelope_reason)
        lease_ok, lease_reason = self._leases.validate_proposal(proposal)
        if not lease_ok:
            return GovernanceResult(AuthorizationDecision.DENY, lease_reason)

        assert proposal.lease_id is not None
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

        lease = self._leases._leases[proposal.lease_id]
        envelope = AuthorizedActionEnvelope(
            action_id=proposal.action_id,
            actor=proposal.actor,
            ocs=proposal.ocs,
            capability=proposal.capability,
            operation=proposal.operation,
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

    @staticmethod
    def _validate_envelope_contract(proposal: ActionProposal) -> tuple[bool, str]:
        required = {
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
        missing = [name for name, value in required.items() if value is None or value == ""]
        if missing:
            return False, f"action_envelope_incomplete:{','.join(sorted(missing))}"
        if not proposal.scope:
            return False, "action_envelope_incomplete:scope"
        return True, "action_envelope_complete"
