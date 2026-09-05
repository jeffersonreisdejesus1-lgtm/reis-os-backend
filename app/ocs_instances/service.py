from __future__ import annotations

import hmac
from collections.abc import Callable
from dataclasses import asdict, replace
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
from app.profile_bindings.profiles import PROFILES, OCSProfile
from app.universal_kernel.contracts import (
    AuthorizedActionEnvelope,
    ReversibilityClass,
    SideEffectClass,
)
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
        request_hash = canonical_hash(
            {
                "institution_id": INSTITUTION_ID,
                **asdict(request),
            }
        )
        recovered = self._store.by_idempotency(request.idempotency_key)
        if recovered is not None:
            lease = self._leases.lease_for(recovered.lease_id)
            if recovered.request_hash != request_hash:
                raise InstanceBindingError("instance_idempotency_conflict")
            nonce = self._nonce(request_hash)
            envelope = self._envelope(recovered, profile, lease, nonce)
            if envelope.digest() != recovered.bootstrap_hash:
                raise InstanceBindingError("bootstrap_recovery_hash_mismatch")
            if recovered.status is InstanceStatus.PREPARED:
                recovered = self._ensure_hazel(recovered, request, envelope)
            return recovered, envelope

        lease = self._validated_lease(request, profile)
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
                session_context=f"context:{canonical_hash({
                    'institution_id': INSTITUTION_ID,
                    'organization_id': request.organization_id,
                    'mission_id': request.mission_id,
                    'ocs_id': request.ocs_id,
                    'context_ref': request.context_ref,
                    'policy_snapshot': request.policy_snapshot,
                    'trace_ref': request.trace_ref,
                })}",
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
            maturity=BindingMaturity.PREPARED_UNVERIFIED,
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
        durable = self._ensure_hazel(stored, request, envelope)
        self._consume_binding_lease(request, lease, durable)
        return durable, envelope

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

    def checkpoint(
        self,
        binding_id: str,
        *,
        platform_instance_id: str,
        generation: int,
        expected_version: int,
        state: dict[str, object],
        idempotency_key: str,
    ) -> InstanceBinding:
        binding = self._store.get(binding_id)
        if binding.status not in {
            InstanceStatus.ACTIVE,
            InstanceStatus.CHECKPOINTED,
        }:
            raise InstanceBindingError("active_instance_required_for_checkpoint")
        self._require_physical_worker(
            binding, platform_instance_id, generation
        )
        next_state_version = binding.checkpoint_version + 1
        persisted = self._continuity.persist_state(
            run_id=binding.run_id,
            expected_ocs=binding.ocs_id,
            host=binding.host,
            authority_ref=binding.authority_ref,
            state_version=next_state_version,
            predecessor_hash=binding.hazel_event_hash,
            state={
                "binding_id": binding.binding_id,
                "mission_id": binding.mission_id,
                "generation": binding.generation,
                "state": state,
            },
            trace_id=f"trace:{binding.binding_id}:checkpoint:{next_state_version}",
        )
        recovered = self._continuity.recover_state(
            run_id=binding.run_id,
            expected_ocs=binding.ocs_id,
            host=binding.host,
            authority_ref=binding.authority_ref,
        )
        if recovered.get("event_hash") != persisted.receipt.get("event_hash"):
            raise InstanceBindingError("checkpoint_readback_mismatch")
        return self._store.transition(
            binding.binding_id,
            expected_version=expected_version,
            target=InstanceStatus.CHECKPOINTED,
            idempotency_key=idempotency_key,
            event_type="OCS_INSTANCE_CHECKPOINTED",
            checkpoint_version=next_state_version,
            checkpoint_hash=str(recovered["payload_hash"]),
            hazel_event_hash=str(recovered["event_hash"]),
            payload={
                "state_version": next_state_version,
                "event_hash": recovered["event_hash"],
            },
        )

    def replace_instance(
        self,
        binding_id: str,
        request: PrepareInstanceRequest,
        *,
        platform_instance_id: str,
        generation: int,
        expected_version: int,
        replacement_idempotency_key: str,
    ) -> tuple[InstanceBinding, InstanceBootstrapEnvelope]:
        previous = self._store.get(binding_id)
        if previous.status is not InstanceStatus.CHECKPOINTED:
            raise InstanceBindingError("verified_checkpoint_required_for_replacement")
        self._require_physical_worker(
            previous, platform_instance_id, generation
        )
        if (
            request.organization_id != previous.organization_id
            or request.mission_id != previous.mission_id
            or request.ocs_id != previous.ocs_id
        ):
            raise InstanceBindingError("replacement_identity_scope_mismatch")
        profile = PROFILES[request.ocs_id]
        lease = self._validated_lease(request, profile)
        prior_state = self._continuity.recover_state(
            run_id=previous.run_id,
            expected_ocs=previous.ocs_id,
            host=previous.host,
            authority_ref=previous.authority_ref,
        )
        request_hash = canonical_hash(
            {"institution_id": INSTITUTION_ID, **asdict(request)}
        )
        now = self._clock()
        nonce = self._nonce(request_hash)
        provisional = replace(
            previous,
            binding_id=f"binding:{request_hash[:32]}",
            capability=request.capability,
            lease_id=request.lease_id,
            authority_ref=lease.authority_ref,
            scope=request.scope,
            generation=previous.generation + 1,
            platform_instance_id=None,
            challenge_hash=canonical_hash({"nonce": nonce}),
            bootstrap_hash="",
            status=InstanceStatus.PREPARED,
            version=1,
            predecessor_binding_id=previous.binding_id,
            checkpoint_version=previous.checkpoint_version,
            checkpoint_hash=previous.checkpoint_hash,
            hazel_event_hash=previous.hazel_event_hash,
            request_hash=request_hash,
            idempotency_key=request.idempotency_key,
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
            created_at=now,
            updated_at=now,
        )
        unsigned = self._envelope(provisional, profile, lease, nonce)
        next_binding = replace(
            provisional,
            bootstrap_hash=unsigned.digest(),
        )
        envelope = self._envelope(next_binding, profile, lease, nonce)
        self._store.create(next_binding)
        next_version = previous.checkpoint_version + 1
        persisted = self._continuity.persist_state(
            run_id=previous.run_id,
            expected_ocs=previous.ocs_id,
            host=previous.host,
            authority_ref=lease.authority_ref,
            state_version=next_version,
            predecessor_hash=previous.hazel_event_hash,
            state={
                "binding_id": next_binding.binding_id,
                "mission_id": next_binding.mission_id,
                "generation": next_binding.generation,
                "recovered_from": previous.binding_id,
                "recovered_payload": prior_state["payload"],
                "bootstrap_hash": next_binding.bootstrap_hash,
            },
            trace_id=f"trace:{next_binding.binding_id}:replacement",
        )
        recovered = self._continuity.recover_state(
            run_id=next_binding.run_id,
            expected_ocs=next_binding.ocs_id,
            host=next_binding.host,
            authority_ref=next_binding.authority_ref,
        )
        if recovered.get("event_hash") != persisted.receipt.get("event_hash"):
            raise InstanceBindingError("replacement_readback_mismatch")
        _, durable = self._store.commit_replacement(
            predecessor_id=previous.binding_id,
            predecessor_expected_version=expected_version,
            successor_id=next_binding.binding_id,
            successor_expected_version=1,
            idempotency_key=replacement_idempotency_key,
            checkpoint_version=next_version,
            checkpoint_hash=str(recovered["payload_hash"]),
            hazel_event_hash=str(recovered["event_hash"]),
        )
        self._consume_binding_lease(request, lease, durable)
        return durable, envelope

    @staticmethod
    def _require_physical_worker(
        binding: InstanceBinding,
        platform_instance_id: str,
        generation: int,
    ) -> None:
        if binding.platform_instance_id != platform_instance_id:
            raise InstanceBindingError("platform_instance_fenced")
        if binding.generation != generation:
            raise InstanceBindingError("instance_generation_fenced")

    def _consume_binding_lease(
        self,
        request: PrepareInstanceRequest,
        lease: AuthorityLease,
        binding: InstanceBinding,
    ) -> None:
        envelope = AuthorizedActionEnvelope(
            action_id=f"bind:{binding.binding_id}",
            actor=request.actor,
            ocs=request.ocs_id,
            capability=request.capability,
            operation="bind_instance",
            action_type="ocs_instance_binding",
            issued_at=binding.created_at,
            payload={"binding_id": binding.binding_id},
            lease_id=lease.lease_id,
            evidence_refs=(),
            csp_ref=PROFILES[request.ocs_id].csp_ref,
            object_ref=request.mission_id,
            tenant=request.organization_id,
            context_ref=request.context_ref,
            scope=request.scope,
            valid_scope=True,
            authority_ref=lease.authority_ref,
            policy_snapshot=request.policy_snapshot,
            idempotency_key=request.idempotency_key,
            expected_effect="bind_one_physical_instance_generation",
            side_effect_class=SideEffectClass.BOUNDED,
            reversibility_class=ReversibilityClass.REVERSIBLE,
            recovery_ref=PROFILES[request.ocs_id].recovery_policy,
            expires_at=lease.expires_at,
            evidence_assessment_ref=f"assessment:{binding.binding_id}",
            max_uses=lease.max_uses,
            trace_id=request.trace_ref,
        )
        ok, reason, use_index = self._leases.reserve_use(envelope)
        if not ok or use_index is None:
            raise InstanceBindingError(reason)
        self._leases.finalize(lease.lease_id)

    def _validated_lease(
        self, request: PrepareInstanceRequest, profile: OCSProfile
    ) -> AuthorityLease:
        valid, reason = self._leases.validate(
            request.lease_id, request.ocs_id, request.capability
        )
        if not valid:
            raise ValueError(reason)
        lease = self._leases.lease_for(request.lease_id)
        if lease.actor != request.actor:
            raise ValueError("lease_actor_mismatch")
        if lease.context_ref != request.context_ref:
            raise ValueError("lease_context_mismatch")
        if lease.policy_snapshot != request.policy_snapshot:
            raise ValueError("lease_policy_snapshot_mismatch")
        if lease.trace_ref != request.trace_ref:
            raise ValueError("lease_trace_binding_mismatch")
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
        bootstrap_checkpoint_version = binding.checkpoint_version
        bootstrap_checkpoint_hash = binding.checkpoint_hash
        if binding.status is not InstanceStatus.PREPARED:
            if binding.predecessor_binding_id is None:
                bootstrap_checkpoint_version = 0
                bootstrap_checkpoint_hash = None
            else:
                predecessor = self._store.get(binding.predecessor_binding_id)
                bootstrap_checkpoint_version = predecessor.checkpoint_version
                bootstrap_checkpoint_hash = predecessor.checkpoint_hash
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
            checkpoint_version=bootstrap_checkpoint_version,
            checkpoint_hash=bootstrap_checkpoint_hash,
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
            request.actor,
            request.context_ref,
            request.policy_snapshot,
            request.trace_ref,
        )
        if not all(required) or not request.scope:
            raise ValueError("instance_prepare_fields_required")
