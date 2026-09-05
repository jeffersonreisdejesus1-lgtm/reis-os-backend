from __future__ import annotations

import hmac
from collections.abc import Callable
from dataclasses import asdict
from hashlib import sha256
from time import time

from app.ocs_instances.contracts import (
    BindingMaturity,
    InstanceBinding,
    InstanceBindingError,
    InstanceBootstrapEnvelope,
    InstanceStatus,
    PrepareInstanceRequest,
    canonical_hash,
    stable_run_id,
)
from app.ocs_instances.store import InstanceBindingStore
from app.profile_bindings.profiles import OCSProfile, PROFILES
from app.universal_kernel.governance import AuthorityLease, AuthorityLeaseManager
from app.universal_kernel.hazel_continuity import (
    HazelBoundContinuity,
    HazelIntegrationError,
)
from app.universal_kernel.identity import (
    IdentityAuditLog,
    IdentityKernelGuard,
    IdentityRecheckTrigger,
)

INSTITUTION_ID = "REIS OS"


class OCSInstanceBinder:
    """Bind a physical Work generation to a mission-scoped OCS identity.

    The binder never spawns a Work agent and never grants authority. It validates an
    action-specific lease, binds the canonical profile, persists through Hazel and
    caps its claim at OPERATIONALLY_BOUND_L1.
    """

    def __init__(
        self,
        *,
        store: InstanceBindingStore,
        identity_guard: IdentityKernelGuard,
        leases: AuthorityLeaseManager,
        continuity: HazelBoundContinuity,
        binding_secret: bytes,
        clock: Callable[[], float] = time,
    ) -> None:
        if not binding_secret:
            raise ValueError("instance_binding_secret_required")
        self._store = store
        self._identity_guard = identity_guard
        self._leases = leases
        self._continuity = continuity
        self._binding_secret = binding_secret
        self._clock = clock

    def prepare(
        self, request: PrepareInstanceRequest
    ) -> tuple[InstanceBinding, InstanceBootstrapEnvelope]:
        self._validate_request(request)
        profile = PROFILES.get(request.ocs_id)
        if profile is None:
            raise ValueError("unknown_ocs_identity")
        lease = self._validated_lease(request, profile)
        request_hash = canonical_hash(
            {
                "institution_id": INSTITUTION_ID,
                **asdict(request),
            }
        )
        recovered = self._store.by_idempotency(request.idempotency_key)
        if recovered is not None:
            if recovered.request_hash != request_hash:
                raise InstanceBindingError("instance_idempotency_conflict")
            nonce = self._nonce(request_hash)
            envelope = self._envelope(recovered, profile, lease, nonce)
            if envelope.digest() != recovered.bootstrap_hash:
                raise InstanceBindingError("bootstrap_recovery_hash_mismatch")
            if recovered.status is InstanceStatus.PREPARED:
                recovered = self._ensure_hazel(recovered, request, envelope)
            return recovered, envelope

        run_id = stable_run_id(
            INSTITUTION_ID,
            request.organization_id,
            request.mission_id,
            request.ocs_id,
        )
        active = self._identity_guard.binding_for(run_id)
        if active is None:
            active = self._identity_guard.bind_active_identity(
                run_id=run_id,
                ocs_id=request.ocs_id,
                host=request.host,
                session_context=request.mission_id,
            )
        active = self._identity_guard.require_valid(
            run_id=run_id,
            expected_ocs=request.ocs_id,
            trigger=IdentityRecheckTrigger.COLD_START,
            host=request.host,
        )
        identity_binding_hash = IdentityAuditLog.binding_hash(active)
        generation = (
            self._store.latest_generation(
                request.organization_id,
                request.mission_id,
                request.ocs_id,
            )
            + 1
        )
        now = self._clock()
        profile_hash = canonical_hash(asdict(profile))
        binding_id = f"binding:{request_hash[:32]}"
        nonce = self._nonce(request_hash)
        provisional = InstanceBinding(
            binding_id=binding_id,
            mission_id=request.mission_id,
            run_id=run_id,
            organization_id=request.organization_id,
            ocs_id=request.ocs_id,
            profile_version=profile.version,
            profile_hash=profile_hash,
            identity_binding_hash=identity_binding_hash,
            request_hash=request_hash,
            maturity=BindingMaturity.OPERATIONALLY_BOUND_L1,
            host=request.host,
            capability=request.capability,
            lease_id=request.lease_id,
            authority_ref=lease.authority_ref,
            scope=request.scope,
            state_namespace=active.state_namespace,
            memory_namespace=active.memory_namespace,
            generation=generation,
            platform_instance_id=None,
            challenge_hash=canonical_hash({"nonce": nonce}),
            bootstrap_hash="",
            status=InstanceStatus.PREPARED,
            version=1,
            predecessor_binding_id=None,
            checkpoint_version=0,
            checkpoint_hash=None,
            hazel_event_hash=None,
            idempotency_key=request.idempotency_key,
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
            created_at=now,
            updated_at=now,
        )
        unsigned = self._envelope(provisional, profile, lease, nonce)
        binding = InstanceBinding(
            **{
                **asdict(provisional),
                "maturity": provisional.maturity,
                "status": provisional.status,
                "bootstrap_hash": unsigned.digest(),
            }
        )
        envelope = self._envelope(binding, profile, lease, nonce)
        stored = self._store.create(binding)
        return self._ensure_hazel(stored, request, envelope), envelope

    def _ensure_hazel(
        self,
        binding: InstanceBinding,
        request: PrepareInstanceRequest,
        envelope: InstanceBootstrapEnvelope,
    ) -> InstanceBinding:
        state = {
            "binding_id": binding.binding_id,
            "mission_id": binding.mission_id,
            "organization_id": binding.organization_id,
            "generation": binding.generation,
            "profile_hash": binding.profile_hash,
            "identity_binding_hash": binding.identity_binding_hash,
            "bootstrap_hash": binding.bootstrap_hash,
            "maturity": binding.maturity.value,
            "status": InstanceStatus.PERSISTED.value,
        }
        recovered: dict[str, object] | None = None
        try:
            recovered = self._continuity.recover_state(
                run_id=binding.run_id,
                expected_ocs=binding.ocs_id,
                host=binding.host,
                authority_ref=binding.authority_ref,
            )
            if recovered.get("payload") != state:
                raise InstanceBindingError("hazel_prepare_recovery_conflict")
        except (KeyError, HazelIntegrationError, ValueError):
            persisted = self._continuity.persist_state(
                run_id=binding.run_id,
                expected_ocs=binding.ocs_id,
                host=binding.host,
                authority_ref=binding.authority_ref,
                state_version=1,
                predecessor_hash=None,
                state=state,
                trace_id=f"trace:{binding.binding_id}:prepare",
            )
            recovered = self._continuity.recover_state(
                run_id=binding.run_id,
                expected_ocs=binding.ocs_id,
                host=binding.host,
                authority_ref=binding.authority_ref,
            )
            if recovered.get("event_hash") != persisted.receipt.get("event_hash"):
                raise InstanceBindingError("hazel_prepare_readback_mismatch")
        if recovered is None or recovered.get("payload") != state:
            raise InstanceBindingError("hazel_prepare_readback_mismatch")
        return self._store.transition(
            binding.binding_id,
            expected_version=binding.version,
            target=InstanceStatus.PERSISTED,
            idempotency_key=f"{request.idempotency_key}:hazel",
            event_type="OCS_INSTANCE_PERSISTED",
            checkpoint_version=1,
            checkpoint_hash=str(recovered["payload_hash"]),
            hazel_event_hash=str(recovered["event_hash"]),
            payload={
                "event_hash": recovered["event_hash"],
                "payload_hash": recovered["payload_hash"],
            },
        )

    def _validated_lease(
        self, request: PrepareInstanceRequest, profile: OCSProfile
    ) -> AuthorityLease:
        valid, reason = self._leases.validate(
            request.lease_id, request.ocs_id, request.capability
        )
        if not valid:
            raise ValueError(reason)
        lease = self._leases.lease_for(request.lease_id)
        if lease.tenant != request.organization_id:
            raise ValueError("lease_tenant_mismatch")
        if lease.object_ref_or_selector != request.mission_id:
            raise ValueError("mission_specific_lease_required")
        if lease.action_binding != "ocs_instance_binding":
            raise ValueError("instance_binding_action_lease_required")
        if not set(request.scope).issubset(set(lease.scope)):
            raise ValueError("lease_scope_mismatch")
        if lease.authority_ref != profile.authority_envelope_ref:
            raise ValueError("profile_authority_ref_mismatch")
        if request.host != "ChatGPT Work":
            raise ValueError("work_host_required")
        return lease

    def _envelope(
        self,
        binding: InstanceBinding,
        profile: OCSProfile,
        lease: AuthorityLease,
        nonce: str,
    ) -> InstanceBootstrapEnvelope:
        return InstanceBootstrapEnvelope(
            schema_version="ocs-instance-bootstrap-v1",
            binding_id=binding.binding_id,
            mission_id=binding.mission_id,
            run_id=binding.run_id,
            ocs_id=binding.ocs_id,
            canonical_name=profile.ocs_id,
            identity_ref=profile.identity,
            ancestry_ref=profile.ancestry,
            constitution_ref=profile.constitution_ref,
            csp_ref=profile.csp_ref,
            profile_version=binding.profile_version,
            profile_hash=binding.profile_hash,
            identity_binding_hash=binding.identity_binding_hash,
            maturity=binding.maturity,
            host=binding.host,
            capability=binding.capability,
            lease_id=binding.lease_id,
            authority_ref=binding.authority_ref,
            scope=binding.scope,
            allowed_action_classes=profile.allowed_action_classes,
            denied_action_classes=profile.denied_action_classes,
            tool_permissions=profile.tool_permissions,
            state_namespace=binding.state_namespace,
            memory_namespace=binding.memory_namespace,
            stop_policy=profile.stop_policy,
            handoff_policy=profile.handoff_policy,
            recovery_policy=profile.recovery_policy,
            generation=binding.generation,
            predecessor_binding_id=binding.predecessor_binding_id,
            checkpoint_version=binding.checkpoint_version,
            checkpoint_hash=binding.checkpoint_hash,
            challenge_nonce=nonce,
            issued_at=binding.created_at,
            expires_at=lease.expires_at,
        )

    def _nonce(self, request_hash: str) -> str:
        return hmac.new(
            self._binding_secret,
            request_hash.encode(),
            sha256,
        ).hexdigest()

    @staticmethod
    def _validate_request(request: PrepareInstanceRequest) -> None:
        required = (
            request.mission_id,
            request.organization_id,
            request.ocs_id,
            request.capability,
            request.lease_id,
            request.host,
            request.idempotency_key,
            request.correlation_id,
        )
        if not all(required) or not request.scope:
            raise ValueError("instance_prepare_fields_required")
