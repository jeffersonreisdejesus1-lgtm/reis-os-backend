from __future__ import annotations

from copy import deepcopy

from app.iris_v1.contracts import (
    DecisionStatus,
    EvidenceFreshness,
    GovernorLease,
    GovernorSpec,
    GovernanceReceipt,
    GovernanceRequest,
    IRIS_DESIGN_AUTHORITY,
    IRIS_DERIVATION_REF,
    IRIS_IDENTITY_STATE_ROOT,
    IrisV1Bindings,
    IrisV1InvariantError,
    LOCAL_GOVERNOR_IDS,
)


NAMESPACE_OWNERS = {
    "NS_IRIS_INSTITUTIONAL": "IRIS_CORE",
    "NS_IRIS_UI_NAV": "IRIS_INTERFACE_RUNTIME",
    "NS_IRIS_DESIGN_WORKING": "LOCAL_GOVERNOR",
    "NS_IRIS_DESIGN_DURABLE": "IRIS_DURABLE_STATE_CONTROL",
    "NS_IRIS_EVIDENCE_FRESHNESS": "EVIDENCE_FRESHNESS_CONTROL",
    "NS_IRIS_RECOVERY": "IRIS_RECOVERY_CONTROL",
}

GOVERNOR_WRITABLE_NAMESPACE = "NS_IRIS_DESIGN_WORKING"


class IrisV1Runtime:
    """Candidate Íris V1 local governance runtime.

    This runtime is fail-closed: construction requires all six R1-R6↔R7
    material bindings, and Governors remain constrained by the locally derived
    four-ID roster, Íris design authority, accessibility HOLD, evidence
    freshness, namespace ownership, leases and generation fencing.
    """

    def __init__(
        self,
        *,
        mission_id: str,
        bindings: IrisV1Bindings,
        derivation_ref: str,
    ) -> None:
        if not mission_id:
            raise ValueError("mission_id_required")
        bindings.assert_complete()
        if derivation_ref != IRIS_DERIVATION_REF:
            raise IrisV1InvariantError("IRIS_V1_DERIVATION_REF_MISMATCH")
        self.mission_id = mission_id
        self.bindings = bindings
        self.derivation_ref = derivation_ref
        self.identity_state_root = IRIS_IDENTITY_STATE_ROOT
        self.design_authority = IRIS_DESIGN_AUTHORITY
        self._governors: dict[str, GovernorSpec] = {}
        self._leases: dict[str, GovernorLease] = {}
        self._generation: dict[str, int] = {}
        self._state_version = 0
        self._state: dict[str, dict[str, object]] = {
            namespace: {} for namespace in NAMESPACE_OWNERS
        }

    @property
    def state_version(self) -> int:
        return self._state_version

    @property
    def state(self) -> dict[str, dict[str, object]]:
        return deepcopy(self._state)

    def register_governor(self, spec: GovernorSpec) -> None:
        spec.validate()
        if spec.governor_id not in LOCAL_GOVERNOR_IDS:
            raise IrisV1InvariantError("IRIS_V1_GOVERNOR_NOT_DERIVED")
        if spec.writable_namespaces != (GOVERNOR_WRITABLE_NAMESPACE,):
            raise IrisV1InvariantError("IRIS_V1_STATE_WRITER_OWNERSHIP_VIOLATION")
        existing = self._governors.get(spec.governor_id)
        if existing is not None and existing != spec:
            raise IrisV1InvariantError("IRIS_V1_GOVERNOR_CONTRACT_CONFLICT")
        self._governors[spec.governor_id] = spec
        self._generation.setdefault(spec.governor_id, 1)

    def bind_lease(self, lease: GovernorLease) -> None:
        spec = self._require_governor(lease.governor_id)
        if lease.mission_id != self.mission_id:
            raise IrisV1InvariantError("IRIS_V1_LEASE_MISSION_MISMATCH")
        if lease.authority_ref != spec.authority_ceiling:
            raise IrisV1InvariantError("IRIS_V1_LEASE_AUTHORITY_CEILING_MISMATCH")
        if lease.generation != self._generation[lease.governor_id]:
            raise IrisV1InvariantError("IRIS_V1_LEASE_GENERATION_MISMATCH")
        self._leases[lease.lease_id] = lease

    def fence_generation(self, governor_id: str) -> int:
        self._require_governor(governor_id)
        current = self._generation[governor_id]
        for lease in self._leases.values():
            if lease.governor_id == governor_id and lease.generation == current:
                lease.fenced = True
        self._generation[governor_id] = current + 1
        return current + 1

    def execute(self, request: GovernanceRequest, *, now: float) -> GovernanceReceipt:
        before = self._state_version
        reason = self._validate_request(request, now=now)
        if reason is not None:
            status = DecisionStatus.HOLD if reason.startswith("HOLD_") else DecisionStatus.DENIED
            return GovernanceReceipt(
                request_id=request.request_id,
                status=status,
                reason=reason,
                mutation_count=0,
                state_version_before=before,
                state_version_after=before,
            )

        namespace_state = self._state[request.namespace]
        changed = 0
        for key, value in request.mutation.items():
            if namespace_state.get(key) != value:
                namespace_state[key] = deepcopy(value)
                changed += 1
        if changed:
            self._state_version += 1
        return GovernanceReceipt(
            request_id=request.request_id,
            status=DecisionStatus.ACCEPTED,
            reason="IRIS_V1_LOCAL_GOVERNANCE_COMMIT",
            mutation_count=changed,
            state_version_before=before,
            state_version_after=self._state_version,
        )

    def _validate_request(self, request: GovernanceRequest, *, now: float) -> str | None:
        spec = self._require_governor(request.governor_id)
        if request.mission_id != self.mission_id:
            return "MISSION_MISMATCH"
        if request.expected_state_version != self._state_version:
            return "STALE_STATE_VERSION"
        if request.namespace not in NAMESPACE_OWNERS:
            return "UNKNOWN_NAMESPACE"
        if request.namespace not in spec.writable_namespaces:
            return "STATE_WRITER_OWNERSHIP_VIOLATION"
        if request.namespace != GOVERNOR_WRITABLE_NAMESPACE:
            return "GOVERNOR_DIRECT_WRITE_FORBIDDEN"
        if request.accessibility_conflict:
            return "HOLD_ACCESSIBILITY_CONFLICT"
        if request.evidence_freshness is not EvidenceFreshness.CURRENT:
            return f"HOLD_EVIDENCE_{request.evidence_freshness.value}"
        if request.design_approval_claimed:
            return "DESIGN_APPROVAL_REQUIRES_IRIS_AUTHORITY"
        if request.authority_transfer_requested:
            return "AUTHORITY_TRANSFER_FORBIDDEN"
        if request.material_effect_requested:
            return "MATERIAL_EFFECT_OUTSIDE_LOCAL_R7_BOUNDARY"
        if request.lease_id is None:
            return "LEASE_REQUIRED"
        lease = self._leases.get(request.lease_id)
        if lease is None:
            return "LEASE_NOT_FOUND"
        if lease.governor_id != request.governor_id:
            return "LEASE_GOVERNOR_MISMATCH"
        if lease.fenced:
            return "FENCED_GENERATION"
        if request.generation != self._generation[request.governor_id]:
            return "STALE_GENERATION"
        if lease.generation != request.generation:
            return "LEASE_GENERATION_MISMATCH"
        if now < lease.valid_from or now >= lease.expires_at:
            return "LEASE_EXPIRED_OR_NOT_YET_VALID"
        if request.namespace not in lease.scope:
            return "LEASE_SCOPE_OVERFLOW"
        if lease.authority_ref != IRIS_DESIGN_AUTHORITY:
            return "AUTHORITY_CEILING_MISMATCH"
        return None

    def _require_governor(self, governor_id: str) -> GovernorSpec:
        if governor_id not in LOCAL_GOVERNOR_IDS:
            raise IrisV1InvariantError("IRIS_V1_GOVERNOR_NOT_DERIVED")
        spec = self._governors.get(governor_id)
        if spec is None:
            raise IrisV1InvariantError("IRIS_V1_GOVERNOR_NOT_REGISTERED")
        return spec


def derived_governor_specs() -> tuple[GovernorSpec, ...]:
    return (
        GovernorSpec(
            "GOV-IRIS-01",
            "PERCEPTION_INTERACTION_GOVERNOR",
            ("NIR-01", "NIR-02"),
            (GOVERNOR_WRITABLE_NAMESPACE,),
            (GOVERNOR_WRITABLE_NAMESPACE, "NS_IRIS_EVIDENCE_FRESHNESS"),
        ),
        GovernorSpec(
            "GOV-IRIS-02",
            "EXPERIENCE_SCOPE_GOVERNOR",
            ("NIR-04", "NIR-09"),
            (GOVERNOR_WRITABLE_NAMESPACE,),
            (GOVERNOR_WRITABLE_NAMESPACE, "NS_IRIS_EVIDENCE_FRESHNESS"),
        ),
        GovernorSpec(
            "GOV-IRIS-03",
            "DESIGN_TRUST_AMBIGUITY_GOVERNOR",
            ("NIR-08", "NIR-10"),
            (GOVERNOR_WRITABLE_NAMESPACE,),
            (GOVERNOR_WRITABLE_NAMESPACE, "NS_IRIS_EVIDENCE_FRESHNESS"),
        ),
        GovernorSpec(
            "GOV-IRIS-04",
            "DESIGN_ROUTING_GOVERNOR",
            ("NIR-11", "NIR-12", "NIR-13", "NIR-14", "NIR-15", "NIR-16"),
            (GOVERNOR_WRITABLE_NAMESPACE,),
            (GOVERNOR_WRITABLE_NAMESPACE, "NS_IRIS_EVIDENCE_FRESHNESS"),
        ),
    )
