from __future__ import annotations

from copy import deepcopy
from typing import Mapping

from app.ocs_v1_batch.contracts import (
    CandidateProfile,
    DecisionStatus,
    EvidenceState,
    GovernanceReceipt,
    GovernanceRequest,
    GovernorSpec,
    OCSV1InvariantError,
)


class OCSV1Runtime:
    """Fail-closed material candidate runtime shared by seven target-specific profiles.

    Shared mechanics do not share identity, state, authority, or Governor rosters.
    Each runtime instance is bound to exactly one CandidateProfile.
    """

    def __init__(
        self,
        *,
        profile: CandidateProfile,
        binding_refs: dict[str, str],
        derivation_ref: str,
        bound_object_ref: str | None = None,
        bound_exact_head: str | None = None,
    ) -> None:
        profile.validate()
        if derivation_ref != profile.derivation_ref:
            raise OCSV1InvariantError(f"{profile.ocs_id}:DERIVATION_REF_MISMATCH")
        if dict(binding_refs) != dict(profile.binding_refs):
            raise OCSV1InvariantError(f"{profile.ocs_id}:R1_R6_BINDING_REF_MISMATCH")
        if profile.ocs_id in {"AGORA", "SOFIA"} and (not bound_object_ref or not bound_exact_head):
            raise OCSV1InvariantError(f"{profile.ocs_id}:EXACT_OBJECT_HEAD_BINDING_REQUIRED")

        self.profile = profile
        self.identity_ref = profile.identity_ref
        self.derivation_ref = derivation_ref
        self.binding_refs = dict(binding_refs)
        self.bound_object_ref = bound_object_ref
        self.bound_exact_head = bound_exact_head
        self._state_version = 0
        self._state = {namespace: {} for namespace in profile.namespaces}
        self._governors = {g.governor_id: g for g in profile.governors}
        self._generation = {governor_id: 0 for governor_id in self._governors}
        self._owner_by_key: dict[tuple[str, str], str] = {}
        for governor in profile.governors:
            for namespace in governor.writable_namespaces:
                for key in governor.owned_state_keys:
                    marker = (namespace, key)
                    if marker in self._owner_by_key:
                        raise OCSV1InvariantError(f"{profile.ocs_id}:DUPLICATE_STATE_OWNER")
                    self._owner_by_key[marker] = governor.governor_id

    @property
    def state_version(self) -> int:
        return self._state_version

    @property
    def state(self) -> dict[str, dict[str, object]]:
        return deepcopy(self._state)

    @property
    def governor_ids(self) -> frozenset[str]:
        return frozenset(self._governors)

    @property
    def generation(self) -> dict[str, int]:
        return dict(self._generation)

    def fence_generation(self, governor_id: str) -> int:
        if governor_id not in self._governors:
            raise OCSV1InvariantError(f"{self.profile.ocs_id}:GOVERNOR_NOT_IN_LOCAL_DERIVED_ROSTER")
        self._generation[governor_id] += 1
        return self._generation[governor_id]

    def snapshot(self) -> dict[str, object]:
        return {
            "ocs_id": self.profile.ocs_id,
            "identity_ref": self.identity_ref,
            "derivation_ref": self.derivation_ref,
            "binding_refs": dict(self.binding_refs),
            "governor_ids": sorted(self._governors),
            "generation": dict(self._generation),
            "state_version": self._state_version,
            "state": deepcopy(self._state),
            "preserved_reservations": list(self.profile.preserved_reservations),
            "bound_object_ref": self.bound_object_ref,
            "bound_exact_head": self.bound_exact_head,
        }

    def restore_snapshot(self, snapshot: Mapping[str, object]) -> None:
        if snapshot.get("ocs_id") != self.profile.ocs_id:
            raise OCSV1InvariantError(f"{self.profile.ocs_id}:RECOVERY_OCS_ID_MISMATCH")
        if snapshot.get("identity_ref") != self.identity_ref:
            raise OCSV1InvariantError(f"{self.profile.ocs_id}:RECOVERY_IDENTITY_MISMATCH")
        if snapshot.get("derivation_ref") != self.derivation_ref:
            raise OCSV1InvariantError(f"{self.profile.ocs_id}:RECOVERY_DERIVATION_MISMATCH")
        if snapshot.get("binding_refs") != self.binding_refs:
            raise OCSV1InvariantError(f"{self.profile.ocs_id}:RECOVERY_BINDING_MISMATCH")

        restored_governors = set(snapshot.get("governor_ids") or ())
        canonical_governors = set(self._governors)
        if restored_governors != canonical_governors:
            raise OCSV1InvariantError(f"{self.profile.ocs_id}:RECOVERY_GOVERNOR_ROSTER_MISMATCH")

        generation = snapshot.get("generation")
        if not isinstance(generation, Mapping) or set(generation) != restored_governors:
            raise OCSV1InvariantError(f"{self.profile.ocs_id}:RECOVERY_GENERATION_OWNER_MISMATCH")
        if any(not isinstance(value, int) or value < 0 for value in generation.values()):
            raise OCSV1InvariantError(f"{self.profile.ocs_id}:RECOVERY_GENERATION_INVALID")

        state = snapshot.get("state")
        if not isinstance(state, Mapping) or set(state) != set(self.profile.namespaces):
            raise OCSV1InvariantError(f"{self.profile.ocs_id}:RECOVERY_NAMESPACE_MISMATCH")
        if any(not isinstance(state[namespace], Mapping) for namespace in self.profile.namespaces):
            raise OCSV1InvariantError(f"{self.profile.ocs_id}:RECOVERY_STATE_INVALID")

        state_version = snapshot.get("state_version")
        if not isinstance(state_version, int) or state_version < 0:
            raise OCSV1InvariantError(f"{self.profile.ocs_id}:RECOVERY_STATE_VERSION_INVALID")

        if tuple(snapshot.get("preserved_reservations") or ()) != self.profile.preserved_reservations:
            raise OCSV1InvariantError(f"{self.profile.ocs_id}:RECOVERY_RESERVATION_MISMATCH")
        if snapshot.get("bound_object_ref") != self.bound_object_ref or snapshot.get("bound_exact_head") != self.bound_exact_head:
            raise OCSV1InvariantError(f"{self.profile.ocs_id}:RECOVERY_OBJECT_HEAD_BINDING_MISMATCH")

        self._state = {namespace: deepcopy(dict(state[namespace])) for namespace in self.profile.namespaces}
        self._state_version = state_version
        self._generation = {str(key): int(value) for key, value in generation.items()}

    def execute(self, request: GovernanceRequest) -> GovernanceReceipt:
        before = self._state_version
        reason, hold = self._validate(request)
        if reason is not None:
            return self._receipt(request, before, DecisionStatus.HOLD if hold else DecisionStatus.DENIED, reason, 0)

        target = self._state[request.namespace]
        changed = 0
        for key, value in request.mutation.items():
            if target.get(key) != value:
                target[key] = deepcopy(value)
                changed += 1
        if changed:
            self._state_version += 1
        return self._receipt(request, before, DecisionStatus.ACCEPTED, f"{self.profile.ocs_id}:LOCAL_R7_GOVERNANCE_COMMIT", changed)

    def _governor(self, governor_id: str) -> GovernorSpec | None:
        return self._governors.get(governor_id)

    def _validate(self, request: GovernanceRequest) -> tuple[str | None, bool]:
        p = self.profile
        if request.ocs_id != p.ocs_id:
            return "CROSS_OCS_REQUEST_DENIED", False
        governor = self._governor(request.governor_id)
        if governor is None:
            return "GOVERNOR_NOT_IN_LOCAL_DERIVED_ROSTER", False
        if request.expected_generation != self._generation[governor.governor_id]:
            return "STALE_GOVERNOR_GENERATION", False
        if request.expected_state_version != self._state_version:
            return "STALE_STATE_VERSION", False
        if request.operation not in governor.allowed_operations:
            return "OPERATION_NOT_OWNED_BY_GOVERNOR", False
        if request.namespace not in governor.writable_namespaces:
            return "STATE_NAMESPACE_OWNERSHIP_VIOLATION", False
        if any(self._owner_by_key.get((request.namespace, key)) != governor.governor_id for key in request.mutation):
            return "STATE_KEY_OWNERSHIP_VIOLATION", False

        if request.self_assurance_requested:
            return "SELF_ASSURANCE_FORBIDDEN", False
        if request.promotion_requested:
            return "CANONICAL_PROMOTION_NOT_AUTHORIZED", False
        if request.runtime_activation_requested:
            return "RUNTIME_GOVERNOR_ACTIVATION_NOT_AUTHORIZED", False
        if request.authority_transfer_requested:
            return "AUTHORITY_TRANSFER_FORBIDDEN", False

        if p.ocs_id in {"DEDALA", "AGORA", "SOFIA", "METIS", "LYRA"}:
            if request.evidence_state is not EvidenceState.CURRENT:
                return f"HOLD_EVIDENCE_{request.evidence_state.value}", True

        if p.ocs_id == "DEDALA":
            if not request.evidence_ref or not request.provenance_ref:
                return "HOLD_EVIDENCE_PROVENANCE_REQUIRED", True
            if request.causal_consistent is False:
                return "HOLD_CAUSAL_INCONSISTENCY", True

        elif p.ocs_id == "AGORA":
            if request.object_ref != self.bound_object_ref or request.exact_head != self.bound_exact_head:
                return "HOLD_EXACT_IMPLEMENTATION_OBJECT_HEAD_MISMATCH", True
            if not request.evidence_ref:
                return "HOLD_MISSING_TEST_OR_VERIFICATION_EVIDENCE", True

        elif p.ocs_id == "SOFIA":
            if request.object_ref != self.bound_object_ref or request.exact_head != self.bound_exact_head:
                return "HOLD_EXACT_REPOSITORY_OBJECT_HEAD_MISMATCH", True
            if request.external_write_requested and not request.authority_ref:
                return "REPOSITORY_WRITE_AUTHORITY_REQUIRED", False

        elif p.ocs_id == "METIS":
            if not request.provenance_ref:
                return "HOLD_SOURCE_PROVENANCE_REQUIRED", True
            if request.strategy_as_execution_authority:
                return "STRATEGY_TO_EXECUTION_AUTHORITY_FORBIDDEN", False
            if request.mutation.get("certainty") == "CERTAIN" and request.evidence_state is not EvidenceState.CURRENT:
                return "UNSUPPORTED_CERTAINTY_INFLATION", False

        elif p.ocs_id == "AURI":
            if not request.provenance_ref:
                return "HOLD_PROVENANCE_REQUIRED", True
            if request.historical_provenance_claimed_resolved:
                return "HISTORICAL_V04_PROVENANCE_NOT_CURRENT_PROOF", False

        elif p.ocs_id == "SYNERGEIA":
            if request.external_write_requested and not request.authority_ref:
                return "EXTERNAL_CHANNEL_AUTHORITY_REQUIRED", False
            if request.package_id is None:
                return "HOLD_DELIVERY_PACKAGE_ID_REQUIRED", True
            if governor.role == "DELIVERY_RETURN_ROUTING_GOVERNOR" and request.return_receipt_package_id is None:
                return "HOLD_RETURN_RECEIPT_REQUIRED", True
            if request.return_receipt_package_id is not None and request.return_receipt_package_id != request.package_id:
                return "RETURN_RECEIPT_PACKAGE_MISMATCH", False

        elif p.ocs_id == "LYRA":
            if request.specialty_ref != "CSP-LYRA-vNEXT-CORR-001":
                return "CORRECTED_CSP_PRECEDENCE_REQUIRED", False
            if request.superseded_specialty_requested:
                return "SUPERSEDED_SPECIALTY_REVERSION_FORBIDDEN", False
            if request.communication_as_institutional_authority:
                return "COMMUNICATION_OUTPUT_NOT_INSTITUTIONAL_AUTHORITY", False
            if request.authority_ref == "IMPLICIT_BRAND_OWNERSHIP_TRANSFER":
                return "IMPLICIT_BRAND_OWNERSHIP_TRANSFER_FORBIDDEN", False

        return None, False

    def _receipt(
        self,
        request: GovernanceRequest,
        before: int,
        status: DecisionStatus,
        reason: str,
        mutation_count: int,
    ) -> GovernanceReceipt:
        after = self._state_version if status is DecisionStatus.ACCEPTED else before
        if status is not DecisionStatus.ACCEPTED and mutation_count != 0:
            raise OCSV1InvariantError(f"{self.profile.ocs_id}:DENY_MUTATION_NONZERO")
        return GovernanceReceipt(
            request_id=request.request_id,
            ocs_id=self.profile.ocs_id,
            status=status,
            reason=reason,
            mutation_count=mutation_count,
            state_version_before=before,
            state_version_after=after,
            identity_ref=self.identity_ref,
            derivation_ref=self.derivation_ref,
        )
