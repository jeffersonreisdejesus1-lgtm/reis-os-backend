from __future__ import annotations

from dataclasses import dataclass
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
    revoked: bool = False


class AuthorityLeaseManager:
    def __init__(self) -> None:
        self._leases: dict[str, AuthorityLease] = {}

    def issue(self, lease: AuthorityLease) -> None:
        self._leases[lease.lease_id] = lease

    def revoke(self, lease_id: str) -> None:
        lease = self._leases[lease_id]
        self._leases[lease_id] = AuthorityLease(
            lease_id=lease.lease_id,
            ocs=lease.ocs,
            capability=lease.capability,
            expires_at=lease.expires_at,
            revoked=True,
        )

    def validate(
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
        lease_ok, lease_reason = self._leases.validate(
            proposal.lease_id,
            proposal.ocs,
            proposal.capability,
        )
        if not lease_ok:
            return GovernanceResult(AuthorizationDecision.DENY, lease_reason)
        envelope = AuthorizedActionEnvelope(
            action_id=proposal.action_id,
            actor=proposal.actor,
            ocs=proposal.ocs,
            capability=proposal.capability,
            operation=proposal.operation,
            payload=proposal.payload,
            lease_id=proposal.lease_id,
            evidence_refs=tuple(item.ref for item in proposal.evidence),
        )
        return GovernanceResult(
            AuthorizationDecision.ALLOW,
            "authorized",
            envelope,
        )
