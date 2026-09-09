from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import replace

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
    RecoveryCheckpoint,
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


def derived_governor_specs() -> tuple[GovernorSpec, ...]:
    return (
        GovernorSpec(
            "GOV-IRIS-01",
            "PERCEPTION_INTERACTION_GOVERNOR",
            ("NIR-01", "NIR-02"),
            (GOVERNOR_WRITABLE_NAMESPACE,),
            (GOVERNOR_WRITABLE_NAMESPACE, "NS_IRIS_EVIDENCE_FRESHNESS"),
            ("perception", "interaction", "hierarchy", "affordance"),
            ("SET_PERCEPTION_INTERACTION_STATE",),
        ),
        GovernorSpec(
            "GOV-IRIS-02",
            "EXPERIENCE_SCOPE_GOVERNOR",
            ("NIR-04", "NIR-09"),
            (GOVERNOR_WRITABLE_NAMESPACE,),
            (GOVERNOR_WRITABLE_NAMESPACE, "NS_IRIS_EVIDENCE_FRESHNESS"),
            ("experience_objective", "experience_scope", "intake_classification"),
            ("SET_EXPERIENCE_SCOPE_STATE",),
        ),
        GovernorSpec(
            "GOV-IRIS-03",
            "DESIGN_TRUST_AMBIGUITY_GOVERNOR",
            ("NIR-08", "NIR-10"),
            (GOVERNOR_WRITABLE_NAMESPACE,),
            (GOVERNOR_WRITABLE_NAMESPACE, "NS_IRIS_EVIDENCE_FRESHNESS"),
            ("trust_profile", "ambiguity", "ownership_recommendation"),
            ("SET_DESIGN_TRUST_STATE",),
        ),
        GovernorSpec(
            "GOV-IRIS-04",
            "DESIGN_ROUTING_GOVERNOR",
            ("NIR-11", "NIR-12", "NIR-13", "NIR-14", "NIR-15", "NIR-16"),
            (GOVERNOR_WRITABLE_NAMESPACE,),
            (GOVERNOR_WRITABLE_NAMESPACE, "NS_IRIS_EVIDENCE_FRESHNESS"),
            ("route", "handoff_type", "handoff_target"),
            ("SET_DESIGN_ROUTING_STATE",),
        ),
    )


_CANONICAL_SPECS = {spec.governor_id: spec for spec in derived_governor_specs()}


class IrisV1Runtime:
    """Fail-closed candidate Íris V1 local governance runtime."""

    def __init__(self, *, mission_id: str, bindings: IrisV1Bindings, derivation_ref: str) -> None:
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
        self._state: dict[str, dict[str, object]] = {namespace: {} for namespace in NAMESPACE_OWNERS}
        self._idempotency: dict[str, tuple[str, GovernanceReceipt, str]] = {}
        self._invalidated_idempotency: set[str] = set()
        self._checkpoints: dict[str, RecoveryCheckpoint] = {}

    @property
    def state_version(self) -> int:
        return self._state_version

    @property
    def state(self) -> dict[str, dict[str, object]]:
        return deepcopy(self._state)

    def register_governor(self, spec: GovernorSpec) -> None:
        spec.validate()
        canonical = _CANONICAL_SPECS.get(spec.governor_id)
        if canonical is None:
            raise IrisV1InvariantError("IRIS_V1_GOVERNOR_NOT_DERIVED")
        if spec != canonical:
            raise IrisV1InvariantError("IRIS_V1_GOVERNOR_CONTRACT_NOT_CANONICAL")
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
        existing = self._leases.get(lease.lease_id)
        if existing is not None and existing != lease:
            raise IrisV1InvariantError("IRIS_V1_LEASE_ID_CONFLICT")
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
        if request.idempotency_key and request.idempotency_key in self._invalidated_idempotency:
            return self._deny(request, before, "IDEMPOTENCY_KEY_INVALIDATED")

        fingerprint = self._request_fingerprint(request)
        if request.idempotency_key:
            prior = self._idempotency.get(request.idempotency_key)
            if prior is not None:
                prior_fingerprint, prior_receipt, _owner = prior
                if prior_fingerprint != fingerprint:
                    return self._deny(request, before, "IDEMPOTENCY_KEY_CONFLICT")
                return replace(prior_receipt, idempotent_replay=True)

        reason = self._validate_request(request, now=now)
        if reason is not None:
            return self._deny(request, before, reason)

        namespace_state = self._state[request.namespace]
        changed = 0
        for key, value in request.mutation.items():
            if namespace_state.get(key) != value:
                namespace_state[key] = deepcopy(value)
                changed += 1
        if changed:
            self._state_version += 1
        receipt = GovernanceReceipt(
            request_id=request.request_id,
            status=DecisionStatus.ACCEPTED,
            reason="IRIS_V1_LOCAL_GOVERNANCE_COMMIT",
            mutation_count=changed,
            state_version_before=before,
            state_version_after=self._state_version,
        )
        if request.idempotency_key:
            self._idempotency[request.idempotency_key] = (fingerprint, receipt, request.governor_id)
        return receipt

    def checkpoint(self, checkpoint_id: str, *, governor_id: str) -> RecoveryCheckpoint:
        spec = self._require_governor(governor_id)
        if checkpoint_id in self._checkpoints:
            raise IrisV1InvariantError("IRIS_V1_CHECKPOINT_ID_CONFLICT")
        working = self._state[GOVERNOR_WRITABLE_NAMESPACE]
        owned = {key: deepcopy(working[key]) for key in spec.owned_state_keys if key in working}
        checkpoint = RecoveryCheckpoint(
            checkpoint_id=checkpoint_id,
            mission_id=self.mission_id,
            governor_id=governor_id,
            generation=self._generation[governor_id],
            state_version=self._state_version,
            owned_state=owned,
        )
        self._checkpoints[checkpoint_id] = checkpoint
        return checkpoint

    def recover_governor(self, governor_id: str, *, checkpoint_id: str) -> int:
        spec = self._require_governor(governor_id)
        checkpoint = self._checkpoints.get(checkpoint_id)
        if checkpoint is None:
            raise IrisV1InvariantError("IRIS_V1_CHECKPOINT_NOT_FOUND")
        if checkpoint.mission_id != self.mission_id or checkpoint.governor_id != governor_id:
            raise IrisV1InvariantError("IRIS_V1_RECOVERY_OWNER_MISMATCH")

        working = self._state[GOVERNOR_WRITABLE_NAMESPACE]
        before = {key: deepcopy(working.get(key)) for key in spec.owned_state_keys}
        for key in spec.owned_state_keys:
            working.pop(key, None)
        for key, value in checkpoint.owned_state.items():
            if key not in spec.owned_state_keys:
                raise IrisV1InvariantError("IRIS_V1_RECOVERY_STATE_OWNERSHIP_VIOLATION")
            working[key] = deepcopy(value)
        after = {key: deepcopy(working.get(key)) for key in spec.owned_state_keys}
        if before != after:
            self._state_version += 1

        self._invalidate_governor_idempotency(governor_id)
        return self.fence_generation(governor_id)

    def _invalidate_governor_idempotency(self, governor_id: str) -> None:
        keys = [key for key, (_fp, _receipt, owner) in self._idempotency.items() if owner == governor_id]
        for key in keys:
            self._idempotency.pop(key, None)
            self._invalidated_idempotency.add(key)

    def _validate_request(self, request: GovernanceRequest, *, now: float) -> str | None:
        spec = self._require_governor(request.governor_id)
        if request.mission_id != self.mission_id:
            return "MISSION_MISMATCH"
        if request.expected_state_version != self._state_version:
            return "STALE_STATE_VERSION"
        if request.operation not in spec.allowed_operations:
            return "OPERATION_NOT_ALLOWED_FOR_GOVERNOR"
        if request.namespace not in NAMESPACE_OWNERS:
            return "UNKNOWN_NAMESPACE"
        if request.namespace not in spec.writable_namespaces:
            return "STATE_WRITER_OWNERSHIP_VIOLATION"
        if request.namespace != GOVERNOR_WRITABLE_NAMESPACE:
            return "GOVERNOR_DIRECT_WRITE_FORBIDDEN"
        if any(key not in spec.owned_state_keys for key in request.mutation):
            return "STATE_KEY_OWNERSHIP_VIOLATION"
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

    def _deny(self, request: GovernanceRequest, before: int, reason: str) -> GovernanceReceipt:
        status = DecisionStatus.HOLD if reason.startswith("HOLD_") else DecisionStatus.DENIED
        return GovernanceReceipt(
            request_id=request.request_id,
            status=status,
            reason=reason,
            mutation_count=0,
            state_version_before=before,
            state_version_after=before,
        )

    @staticmethod
    def _request_fingerprint(request: GovernanceRequest) -> str:
        raw = json.dumps(
            {
                "mission_id": request.mission_id,
                "governor_id": request.governor_id,
                "operation": request.operation,
                "namespace": request.namespace,
                "mutation": request.mutation,
                "expected_state_version": request.expected_state_version,
                "lease_id": request.lease_id,
                "generation": request.generation,
                "evidence_freshness": request.evidence_freshness.value,
                "accessibility_conflict": request.accessibility_conflict,
                "design_approval_claimed": request.design_approval_claimed,
                "authority_transfer_requested": request.authority_transfer_requested,
                "material_effect_requested": request.material_effect_requested,
            },
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(raw).hexdigest()

    def _require_governor(self, governor_id: str) -> GovernorSpec:
        if governor_id not in LOCAL_GOVERNOR_IDS:
            raise IrisV1InvariantError("IRIS_V1_GOVERNOR_NOT_DERIVED")
        spec = self._governors.get(governor_id)
        if spec is None:
            raise IrisV1InvariantError("IRIS_V1_GOVERNOR_NOT_REGISTERED")
        return spec
