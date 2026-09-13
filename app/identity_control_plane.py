from __future__ import annotations

import hmac
import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from time import time
from typing import Any, Protocol

from app.ocs_instances.contracts import InstanceBinding, InstanceBindingError, InstanceStatus
from app.universal_kernel.governance import AuthorityLeaseManager
from app.universal_kernel.identity import IdentityAuditLog, IdentityKernelGuard, IdentityRecheckTrigger


class IdentityControlPlaneError(RuntimeError):
    """Fail-closed identity-control-plane rejection."""


class BindingReader(Protocol):
    def get(self, binding_id: str) -> InstanceBinding: ...


@dataclass(frozen=True, slots=True)
class ModelActionProposal:
    """Untrusted model proposal. Identity fields are advisory-only input."""

    requested_target: str
    object_id: str
    action_type: str
    payload: dict[str, Any]
    model_source_ocs: str | None = None
    model_source_instance_id: str | None = None
    model_generation: int | None = None


@dataclass(frozen=True, slots=True)
class SystemStampedEnvelope:
    source_ocs: str
    source_instance_id: str
    run_id: str
    generation: int
    binding_hash: str
    mission_id: str
    authority_ref: str
    lease_ref: str
    state_namespace: str
    memory_namespace: str
    requested_target: str
    object_id: str
    action_type: str
    payload: dict[str, Any]
    issued_at: float


@dataclass(frozen=True, slots=True)
class HandoffIdentityReceipt:
    handoff_id: str
    source_ocs_id: str
    source_instance_id: str
    source_run_id: str
    source_generation: int
    source_binding_hash: str
    source_mission_id: str
    source_authority_ref: str
    target_ocs_id: str
    object_id: str
    authorized_next_scope: tuple[str, ...]
    predecessor_event_hash: str | None
    issued_at: float
    integrity_proof: str


class AuthoritativeIdentityReferenceMonitor:
    """Mandatory identity mediation for institutionally significant effects.

    The model never supplies authoritative source identity. The monitor reads the
    durable OCS instance binding, cross-checks the IdentityKernelGuard and the
    authority lease, fences stale physical workers/generations and emits a
    system-stamped envelope. Any conflicting model identity claim fails closed.
    """

    _ACTIVE_STATUSES = frozenset({InstanceStatus.ACTIVE, InstanceStatus.CHECKPOINTED})

    def __init__(
        self,
        *,
        bindings: BindingReader,
        identity_guard: IdentityKernelGuard,
        leases: AuthorityLeaseManager,
        receipt_key: bytes,
        clock=time,
    ) -> None:
        if not receipt_key:
            raise ValueError("identity_receipt_key_required")
        self._bindings = bindings
        self._identity_guard = identity_guard
        self._leases = leases
        self._receipt_key = receipt_key
        self._clock = clock

    def stamp(
        self,
        *,
        binding_id: str,
        platform_instance_id: str,
        generation: int,
        mission_id: str,
        proposal: ModelActionProposal,
    ) -> SystemStampedEnvelope:
        try:
            binding = self._bindings.get(binding_id)
        except InstanceBindingError as exc:
            raise IdentityControlPlaneError("identity_binding_required") from exc

        if binding.status not in self._ACTIVE_STATUSES:
            raise IdentityControlPlaneError("identity_binding_not_active")
        if binding.platform_instance_id != platform_instance_id:
            raise IdentityControlPlaneError("platform_instance_fenced")
        if binding.generation != generation:
            raise IdentityControlPlaneError("instance_generation_fenced")
        if binding.mission_id != mission_id:
            raise IdentityControlPlaneError("mission_identity_mismatch")

        # Model-declared source identity is never adopted. A conflict is security
        # relevant and therefore rejected rather than silently normalized.
        if proposal.model_source_ocs is not None and proposal.model_source_ocs != binding.ocs_id:
            raise IdentityControlPlaneError("model_source_ocs_conflict")
        if (
            proposal.model_source_instance_id is not None
            and proposal.model_source_instance_id != binding.platform_instance_id
        ):
            raise IdentityControlPlaneError("model_source_instance_conflict")
        if proposal.model_generation is not None and proposal.model_generation != binding.generation:
            raise IdentityControlPlaneError("model_generation_conflict")

        authoritative = self._identity_guard.require_valid(
            run_id=binding.run_id,
            expected_ocs=binding.ocs_id,
            trigger=IdentityRecheckTrigger.PRE_ACTION,
            host=binding.host,
        )
        authoritative_hash = IdentityAuditLog.binding_hash(authoritative)
        if authoritative_hash != binding.identity_binding_hash:
            raise IdentityControlPlaneError("identity_binding_hash_mismatch")
        if authoritative.state_namespace != binding.state_namespace:
            raise IdentityControlPlaneError("identity_state_namespace_mismatch")
        if authoritative.memory_namespace != binding.memory_namespace:
            raise IdentityControlPlaneError("identity_memory_namespace_mismatch")

        lease = self._leases.lease_for(binding.lease_id)
        lease_ok, lease_reason = self._leases.validate(
            binding.lease_id, binding.ocs_id, binding.capability
        )
        if not lease_ok:
            raise IdentityControlPlaneError(lease_reason)
        if lease.authority_ref != binding.authority_ref:
            raise IdentityControlPlaneError("identity_authority_ref_mismatch")
        if not set(binding.scope).issubset(set(lease.scope)):
            raise IdentityControlPlaneError("identity_authorized_scope_mismatch")

        return SystemStampedEnvelope(
            source_ocs=binding.ocs_id,
            source_instance_id=platform_instance_id,
            run_id=binding.run_id,
            generation=binding.generation,
            binding_hash=binding.identity_binding_hash,
            mission_id=binding.mission_id,
            authority_ref=binding.authority_ref,
            lease_ref=binding.lease_id,
            state_namespace=binding.state_namespace,
            memory_namespace=binding.memory_namespace,
            requested_target=proposal.requested_target,
            object_id=proposal.object_id,
            action_type=proposal.action_type,
            payload=dict(proposal.payload),
            issued_at=float(self._clock()),
        )

    def issue_handoff_receipt(
        self,
        *,
        handoff_id: str,
        envelope: SystemStampedEnvelope,
        authorized_next_scope: tuple[str, ...],
        predecessor_event_hash: str | None,
    ) -> HandoffIdentityReceipt:
        if envelope.action_type != "handoff":
            raise IdentityControlPlaneError("handoff_action_required")
        payload = {
            "handoff_id": handoff_id,
            "source_ocs_id": envelope.source_ocs,
            "source_instance_id": envelope.source_instance_id,
            "source_run_id": envelope.run_id,
            "source_generation": envelope.generation,
            "source_binding_hash": envelope.binding_hash,
            "source_mission_id": envelope.mission_id,
            "source_authority_ref": envelope.authority_ref,
            "target_ocs_id": envelope.requested_target,
            "object_id": envelope.object_id,
            "authorized_next_scope": list(authorized_next_scope),
            "predecessor_event_hash": predecessor_event_hash,
            "issued_at": envelope.issued_at,
        }
        proof = hmac.new(self._receipt_key, self._canonical(payload), sha256).hexdigest()
        return HandoffIdentityReceipt(
            handoff_id=handoff_id,
            source_ocs_id=envelope.source_ocs,
            source_instance_id=envelope.source_instance_id,
            source_run_id=envelope.run_id,
            source_generation=envelope.generation,
            source_binding_hash=envelope.binding_hash,
            source_mission_id=envelope.mission_id,
            source_authority_ref=envelope.authority_ref,
            target_ocs_id=envelope.requested_target,
            object_id=envelope.object_id,
            authorized_next_scope=authorized_next_scope,
            predecessor_event_hash=predecessor_event_hash,
            issued_at=envelope.issued_at,
            integrity_proof=proof,
        )

    def verify_handoff_receipt(
        self,
        receipt: HandoffIdentityReceipt,
        *,
        expected_target_ocs: str,
    ) -> None:
        raw = asdict(receipt)
        proof = str(raw.pop("integrity_proof"))
        raw["authorized_next_scope"] = list(receipt.authorized_next_scope)
        expected = hmac.new(self._receipt_key, self._canonical(raw), sha256).hexdigest()
        if not hmac.compare_digest(expected, proof):
            raise IdentityControlPlaneError("handoff_integrity_proof_invalid")
        if receipt.target_ocs_id != expected_target_ocs:
            raise IdentityControlPlaneError("handoff_receiver_target_mismatch")

    @staticmethod
    def _canonical(value: dict[str, Any]) -> bytes:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
