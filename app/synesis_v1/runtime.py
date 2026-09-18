from __future__ import annotations

from copy import deepcopy
from typing import Mapping

from app.synesis_v1.contracts import (
    AssuranceReceipt,
    AssuranceRequest,
    DecisionStatus,
    EvidenceState,
    SynesisInvariantError,
    SynesisProfile,
)


class SynesisV1Runtime:
    """Material I1 candidate for Sýnesis-local assurance governance.

    This runtime is not an authority root, cannot self-assure, and cannot promote
    or activate itself. It preserves reservations and fail-closed evidence rules.
    """

    def __init__(self, *, profile: SynesisProfile | None = None) -> None:
        self.profile = profile or SynesisProfile()
        self.profile.validate()
        self._governors = {g.governor_id: g for g in self.profile.governors}
        self._generation = {governor_id: 0 for governor_id in self._governors}
        self._state_version = 0
        self._state = {
            namespace: {}
            for governor in self.profile.governors
            for namespace in governor.writable_namespaces
        }
        self._owner_by_key: dict[tuple[str, str], str] = {}
        for governor in self.profile.governors:
            for namespace in governor.writable_namespaces:
                for key in governor.owned_state_keys:
                    marker = (namespace, key)
                    if marker in self._owner_by_key:
                        raise SynesisInvariantError("SYNESIS:DUPLICATE_STATE_OWNER")
                    self._owner_by_key[marker] = governor.governor_id
        self._idempotency: dict[str, AssuranceReceipt] = {}

    @property
    def state(self) -> dict[str, dict[str, object]]:
        return deepcopy(self._state)

    @property
    def state_version(self) -> int:
        return self._state_version

    @property
    def generation(self) -> dict[str, int]:
        return dict(self._generation)

    @property
    def governor_ids(self) -> frozenset[str]:
        return frozenset(self._governors)

    def snapshot(self) -> dict[str, object]:
        return {
            "ocs_id": self.profile.ocs_id,
            "identity_ref": self.profile.identity_ref,
            "architecture_ref": self.profile.architecture_ref,
            "assurance_ref": self.profile.assurance_ref,
            "i0_ref": self.profile.i0_ref,
            "binding_refs": dict(self.profile.binding_refs),
            "governor_ids": sorted(self._governors),
            "generation": dict(self._generation),
            "state_version": self._state_version,
            "state": deepcopy(self._state),
            "preserved_reservations": list(self.profile.preserved_reservations),
            "excluded_predecessor": self.profile.excluded_predecessor,
        }

    def restore_snapshot(self, snapshot: Mapping[str, object]) -> None:
        exact = {
            "ocs_id": self.profile.ocs_id,
            "identity_ref": self.profile.identity_ref,
            "architecture_ref": self.profile.architecture_ref,
            "assurance_ref": self.profile.assurance_ref,
            "i0_ref": self.profile.i0_ref,
            "excluded_predecessor": self.profile.excluded_predecessor,
        }
        for field, expected in exact.items():
            if snapshot.get(field) != expected:
                raise SynesisInvariantError(f"SYNESIS:RECOVERY_{field.upper()}_MISMATCH")
        if snapshot.get("binding_refs") != dict(self.profile.binding_refs):
            raise SynesisInvariantError("SYNESIS:RECOVERY_BINDING_MISMATCH")
        if tuple(snapshot.get("preserved_reservations") or ()) != self.profile.preserved_reservations:
            raise SynesisInvariantError("SYNESIS:RECOVERY_RESERVATION_MISMATCH")

        restored_governors = set(snapshot.get("governor_ids") or ())
        if restored_governors != set(self._governors):
            raise SynesisInvariantError("SYNESIS:RECOVERY_GOVERNOR_ROSTER_MISMATCH")
        generation = snapshot.get("generation")
        if not isinstance(generation, Mapping) or set(generation) != restored_governors:
            raise SynesisInvariantError("SYNESIS:RECOVERY_GENERATION_OWNER_MISMATCH")
        if any(not isinstance(value, int) or value < 0 for value in generation.values()):
            raise SynesisInvariantError("SYNESIS:RECOVERY_GENERATION_INVALID")

        state = snapshot.get("state")
        if not isinstance(state, Mapping) or set(state) != set(self._state):
            raise SynesisInvariantError("SYNESIS:RECOVERY_NAMESPACE_MISMATCH")
        for namespace, values in state.items():
            if not isinstance(values, Mapping):
                raise SynesisInvariantError("SYNESIS:RECOVERY_STATE_INVALID")
            for key in values:
                if self._owner_by_key.get((str(namespace), str(key))) is None:
                    raise SynesisInvariantError("SYNESIS:RECOVERY_STATE_KEY_OWNERSHIP_VIOLATION")

        state_version = snapshot.get("state_version")
        if not isinstance(state_version, int) or state_version < 0:
            raise SynesisInvariantError("SYNESIS:RECOVERY_STATE_VERSION_INVALID")

        pre = dict(self._generation)
        self._state = {str(ns): deepcopy(dict(values)) for ns, values in state.items()}
        self._state_version = state_version
        self._generation = {
            governor_id: max(pre[governor_id], int(generation[governor_id])) + 1
            for governor_id in self._governors
        }
        self._idempotency = {}

    def execute(self, request: AssuranceRequest) -> AssuranceReceipt:
        if request.request_id in self._idempotency:
            return self._idempotency[request.request_id]

        before = self._state_version
        reason, status = self._validate(request)
        if reason is not None:
            receipt = self._receipt(request, before, status, reason, 0)
            self._idempotency[request.request_id] = receipt
            return receipt

        target = self._state[request.namespace]
        changed = 0
        for key, value in request.mutation.items():
            if target.get(key) != value:
                target[key] = deepcopy(value)
                changed += 1
        if changed:
            self._state_version += 1
        disposition = request.requested_disposition or DecisionStatus.PASS
        receipt = self._receipt(request, before, disposition, "SYNESIS:LOCAL_R7_ASSURANCE_COMMIT", changed)
        self._idempotency[request.request_id] = receipt
        return receipt

    def _validate(self, request: AssuranceRequest) -> tuple[str | None, DecisionStatus]:
        if request.ocs_id != self.profile.ocs_id:
            return "SYNESIS:CROSS_OCS_WRITE_DENIED", DecisionStatus.DENIED
        governor = self._governors.get(request.governor_id)
        if governor is None:
            return "SYNESIS:GOVERNOR_NOT_IN_LOCAL_ROSTER", DecisionStatus.DENIED
        if request.expected_generation != self._generation[governor.governor_id]:
            return "SYNESIS:STALE_GOVERNOR_GENERATION", DecisionStatus.DENIED
        if request.expected_state_version != self._state_version:
            return "SYNESIS:STALE_STATE_VERSION", DecisionStatus.DENIED
        if request.operation not in governor.allowed_operations:
            return "SYNESIS:OPERATION_NOT_OWNED", DecisionStatus.DENIED
        if request.namespace not in governor.writable_namespaces:
            return "SYNESIS:STATE_NAMESPACE_OWNERSHIP_VIOLATION", DecisionStatus.DENIED
        if any(self._owner_by_key.get((request.namespace, key)) != governor.governor_id for key in request.mutation):
            return "SYNESIS:STATE_KEY_OWNERSHIP_VIOLATION", DecisionStatus.DENIED

        if request.self_assurance_requested:
            return "SYNESIS:SELF_ASSURANCE_FORBIDDEN", DecisionStatus.DENIED
        if request.self_homologation_requested:
            return "SYNESIS:SELF_HOMOLOGATION_FORBIDDEN", DecisionStatus.DENIED
        if request.promotion_requested:
            return "SYNESIS:CANONICAL_PROMOTION_NOT_AUTHORIZED", DecisionStatus.DENIED
        if request.runtime_activation_requested:
            return "SYNESIS:RUNTIME_GOVERNOR_ACTIVATION_NOT_AUTHORIZED", DecisionStatus.DENIED
        if request.authority_transfer_requested:
            return "SYNESIS:AUTHORITY_TRANSFER_FORBIDDEN", DecisionStatus.DENIED
        if request.predecessor_ref == self.profile.excluded_predecessor:
            return "SYNESIS:VOID_PREDECESSOR_FORBIDDEN", DecisionStatus.DENIED

        if not request.object_ref or not request.exact_revision:
            return "SYNESIS:HOLD_OBJECT_VERSION_BINDING_REQUIRED", DecisionStatus.HOLD
        if request.evidence_state is not EvidenceState.CURRENT:
            return f"SYNESIS:HOLD_EVIDENCE_{request.evidence_state.value}", DecisionStatus.HOLD
        if not request.evidence_ref or not request.provenance_ref:
            return "SYNESIS:HOLD_EVIDENCE_PROVENANCE_REQUIRED", DecisionStatus.HOLD

        if request.requested_disposition is DecisionStatus.PASS and request.reservation_refs:
            return "SYNESIS:RESERVATIONS_CANNOT_BE_COLLAPSED_TO_PASS", DecisionStatus.DENIED
        if request.requested_disposition is DecisionStatus.PASS_WITH_RESERVATIONS and not request.reservation_refs:
            return "SYNESIS:HOLD_EXPLICIT_RESERVATIONS_REQUIRED", DecisionStatus.HOLD

        return None, request.requested_disposition or DecisionStatus.PASS

    def _receipt(
        self,
        request: AssuranceRequest,
        before: int,
        status: DecisionStatus,
        reason: str,
        mutation_count: int,
    ) -> AssuranceReceipt:
        if status in {DecisionStatus.DENIED, DecisionStatus.HOLD, DecisionStatus.FINDING} and mutation_count != 0:
            raise SynesisInvariantError("SYNESIS:DENY_OR_HOLD_MUTATION_NONZERO")
        return AssuranceReceipt(
            request_id=request.request_id,
            status=status,
            reason=reason,
            mutation_count=mutation_count,
            state_version_before=before,
            state_version_after=self._state_version if mutation_count else before,
            generation=self._generation.get(request.governor_id, -1),
        )
