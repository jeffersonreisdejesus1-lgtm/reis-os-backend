from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .identity import IdentityKernelGuard, IdentityRecheckTrigger


class InteractionIdentityStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    HOLD = "hold"


class IdentityClaimSource(StrEnum):
    USER = "user"
    PROMPT = "prompt"
    HANDOFF = "handoff"
    HOST = "host"
    INTERNAL_CONFIG = "internal_config"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class InteractionIdentityReadback:
    """Identity material safe for an interaction surface to disclose.

    Canonical identity fields are populated only after the Kernel binding has been
    materially revalidated against its canonical profile. A user statement, prompt,
    handoff, host label, or configured name is a claim source, never identity proof.
    """

    status: InteractionIdentityStatus
    reason: str
    run_id: str
    claim_source: IdentityClaimSource
    ocs_canonical_name: str | None = None
    ocs_id: str | None = None
    institution: str | None = None
    profile_version: str | None = None
    binding_hash: str | None = None
    evidence_source: str | None = None

    @property
    def canonical_identity_disclosable(self) -> bool:
        return self.status is InteractionIdentityStatus.VERIFIED

    def to_public_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "identity_status": self.status.value,
            "reason": self.reason,
            "run_id": self.run_id,
            "claim_source": self.claim_source.value,
        }
        if not self.canonical_identity_disclosable:
            return payload
        payload.update(
            {
                "ocs_canonical_name": self.ocs_canonical_name,
                "ocs_id": self.ocs_id,
                "institution": self.institution,
                "profile_version": self.profile_version,
                "binding_hash": self.binding_hash,
                "evidence_source": self.evidence_source,
            }
        )
        return payload


class InteractionIdentityEnforcer:
    """Fail closed when an interaction surface asserts its OCS identity."""

    EVIDENCE_SOURCE = "kernel_identity_binding_readback"

    def __init__(self, guard: IdentityKernelGuard) -> None:
        self._guard = guard

    def readback(
        self,
        *,
        run_id: str,
        claimed_ocs: str | None = None,
        claim_source: IdentityClaimSource = IdentityClaimSource.UNKNOWN,
        host: str | None = None,
    ) -> InteractionIdentityReadback:
        binding = self._guard.binding_for(run_id)
        if binding is None:
            return InteractionIdentityReadback(
                status=InteractionIdentityStatus.UNVERIFIED,
                reason="identity_binding_readback_missing",
                run_id=run_id,
                claim_source=claim_source,
            )

        if host is None:
            return InteractionIdentityReadback(
                status=InteractionIdentityStatus.UNVERIFIED,
                reason="interaction_host_context_required",
                run_id=run_id,
                claim_source=claim_source,
            )

        expected_ocs = binding.ocs_id if claimed_ocs is None else claimed_ocs
        try:
            verified = self._guard.require_valid(
                run_id=run_id,
                expected_ocs=expected_ocs,
                trigger=IdentityRecheckTrigger.IDENTITY_CONFLICT,
                host=host,
            )
        except ValueError as exc:
            return InteractionIdentityReadback(
                status=InteractionIdentityStatus.HOLD,
                reason=str(exc),
                run_id=run_id,
                claim_source=claim_source,
            )

        binding_hash = self._guard.audit_log.binding_hash(verified)
        self._guard.audit_log.append(
            "INTERACTION_IDENTITY_READBACK",
            verified,
            details={
                "claim_source": claim_source.value,
                "claimed_ocs": claimed_ocs,
                "result": "verified",
                "binding_hash": binding_hash,
            },
        )
        return InteractionIdentityReadback(
            status=InteractionIdentityStatus.VERIFIED,
            reason="identity_verified_by_binding_readback",
            run_id=run_id,
            claim_source=claim_source,
            ocs_canonical_name=verified.ocs_canonical_name,
            ocs_id=verified.ocs_id,
            institution=verified.institution,
            profile_version=verified.profile_version,
            binding_hash=binding_hash,
            evidence_source=self.EVIDENCE_SOURCE,
        )
