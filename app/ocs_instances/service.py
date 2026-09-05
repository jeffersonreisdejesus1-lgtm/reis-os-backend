from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from secrets import token_urlsafe
from time import time
from uuid import uuid4

from app.ocs_instances.contracts import (
    InstanceBinding,
    InstanceBootstrapEnvelope,
    InstanceStatus,
    PrepareInstanceRequest,
    canonical_hash,
    stable_run_id,
)
from app.ocs_instances.store import InstanceBindingStore
from app.profile_bindings.profiles import PROFILES
from app.universal_kernel.governance import AuthorityLeaseManager
from app.universal_kernel.hazel_continuity import HazelBoundContinuity
from app.universal_kernel.identity import IdentityKernelGuard, IdentityRecheckTrigger


class OCSInstanceBinder:
    """Binds one physical worker generation to an OCS mission identity.

    This service does not spawn a Work agent and does not grant authority. It consumes
    an already-issued mission-specific lease, creates a bootstrap challenge, persists
    the binding and proves its recovery through Hazel.
    """

    def __init__(
        self,
        *,
        store: InstanceBindingStore,
        identity_guard: IdentityKernelGuard,
        leases: AuthorityLeaseManager,
        continuity: HazelBoundContinuity,
        clock: Callable[[], float] = time,
        nonce_factory: Callable[[], str] = token_urlsafe,
    ) -> None:
        self._store = store
        self._identity_guard = identity_guard
        self._leases = leases
        self._continuity = continuity
        self._clock = clock
        self._nonce_factory = nonce_factory

    def prepare(
        self, request: PrepareInstanceRequest
    ) -> tuple[InstanceBinding, InstanceBootstrapEnvelope]:
        self._validate_request(request)
        profile = PROFILES.get(request.ocs_id)
        if profile is None:
            raise ValueError("unknown_ocs_identity")
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
        if not set(request.scope).issubset(set(lease.scope)):
            raise ValueError("lease_scope_mismatch")
        if lease.authority_ref != profile.authority_envelope_ref:
            raise ValueError("profile_authority_ref_mismatch")
        if request.host != "ChatGPT Work":
            raise ValueError("work_host_required")

        run_id = stable_run_id(request.mission_id, request.ocs_id)
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

        generation = self._store.latest_generation(
            request.mission_id, request.ocs_id
        ) + 1
        now = self._clock()
        nonce = self._nonce_factory()
        profile_hash = canonical_hash(asdict(profile))
        binding_id = f"binding:{uuid4()}"
        envelope = InstanceBootstrapEnvelope(
            schema_version="ocs-instance-bootstrap-v1",
            binding_id=binding_id,
            mission_id=request.mission_id,
            run_id=run_id,
            ocs_id=request.ocs_id,
            canonical_name=profile.ocs_id,
            identity_ref=profile.identity,
            ancestry_ref=profile.ancestry,
            constitution_ref=profile.constitution_ref,
            csp_ref=profile.csp_ref,
            profile_version=profile.version,
            profile_hash=profile_hash,
            host=request.host,
            capability=request.capability,
            lease_id=request.lease_id,
            authority_ref=lease.authority_ref,
            scope=request.scope,
            allowed_action_classes=profile.allowed_action_classes,
            denied_action_classes=profile.denied_action_classes,
            tool_permissions=profile.tool_permissions,
            state_namespace=profile.state_namespace,
            memory_namespace=profile.memory_namespace,
            stop_policy=profile.stop_policy,
            handoff_policy=profile.handoff_policy,
            recovery_policy=profile.recovery_policy,
            generation=generation,
            predecessor_binding_id=None,
            checkpoint_version=0,
            checkpoint_hash=None,
            challenge_nonce=nonce,
            issued_at=now,
            expires_at=lease.expires_at,
        )
        binding = InstanceBinding(
            binding_id=binding_id,
            mission_id=request.mission_id,
            run_id=run_id,
            organization_id=request.organization_id,
            ocs_id=request.ocs_id,
            profile_version=profile.version,
            profile_hash=profile_hash,
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
            bootstrap_hash=envelope.digest(),
            status=InstanceStatus.PREPARED,
            version=1,
            predecessor_binding_id=None,
            checkpoint_version=0,
            checkpoint_hash=None,
            idempotency_key=request.idempotency_key,
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
            created_at=now,
            updated_at=now,
        )
        stored = self._store.create(binding)
        if stored.binding_id != binding.binding_id:
            raise ValueError("prepared_binding_replay_requires_bootstrap_recovery")

        persisted = self._continuity.persist_state(
            run_id=run_id,
            expected_ocs=request.ocs_id,
            host=request.host,
            authority_ref=lease.authority_ref,
            state_version=1,
            predecessor_hash=None,
            state={
                "binding_id": binding.binding_id,
                "mission_id": binding.mission_id,
                "generation": binding.generation,
                "profile_hash": binding.profile_hash,
                "bootstrap_hash": binding.bootstrap_hash,
                "status": binding.status.value,
            },
            trace_id=f"trace:{binding.binding_id}:prepare",
        )
        if not persisted.receipt.get("accepted"):
            raise RuntimeError("instance_hazel_prepare_not_accepted")
        return binding, envelope

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
