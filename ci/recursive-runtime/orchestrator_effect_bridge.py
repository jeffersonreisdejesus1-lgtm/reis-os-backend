from dataclasses import dataclass
import time

from production_effects import (
    ActivationLease,
    EffectRequest,
    ProductionAuthorizationPolicy,
)


@dataclass(frozen=True)
class OrchestratorEffectAuthorization:
    authorization_id: str
    mission_id: str
    orchestrator_run_id: str
    mission_stage: str
    actor_id: str
    canonical_identity: str
    authority_ref: str
    mission_binding: str
    delegation_ref: str
    target: str
    capability: str
    payload_ref: str
    founder_approval_ref: str
    generation: int
    fencing_epoch: int
    request_id: str
    evidence_parent: str
    issued_at_unix: float
    expires_at_unix: float
    estimated_incremental_cost_usd: float = 0.0
    requires_paid_upgrade: bool = False


@dataclass(frozen=True)
class PreparedEffect:
    request: EffectRequest
    lease: ActivationLease
    policy: ProductionAuthorizationPolicy


class OrchestratorEffectBridge:
    """Bootstrap binding from orchestrated mission authority to the existing effect gateway.

    This class never executes a provider effect itself. It only converts an exact,
    scope-bound Orchestrator authorization into the already-canonical request/lease/policy
    structures consumed by ProductionEffectGateway.
    """

    def __init__(self, *, expected_mission_id: str, expected_run_id: str,
                 expected_stage: str, allowed_identity: str, allowed_target: str,
                 allowed_capability: str, founder_approval_ref: str, clock=None):
        self.expected_mission_id = expected_mission_id
        self.expected_run_id = expected_run_id
        self.expected_stage = expected_stage
        self.allowed_identity = allowed_identity
        self.allowed_target = allowed_target
        self.allowed_capability = allowed_capability
        self.founder_approval_ref = founder_approval_ref
        self.clock = clock or time.time

    def _validate(self, auth: OrchestratorEffectAuthorization) -> None:
        if not auth.authorization_id or not auth.request_id or not auth.evidence_parent:
            raise RuntimeError("AUTHORITY_PROOF_INCOMPLETE")
        if auth.mission_id != self.expected_mission_id:
            raise RuntimeError("MISSION_MISMATCH")
        if auth.orchestrator_run_id != self.expected_run_id:
            raise RuntimeError("ORCHESTRATOR_RUN_MISMATCH")
        if auth.mission_stage != self.expected_stage:
            raise RuntimeError("MISSION_STAGE_MISMATCH")
        if auth.canonical_identity != self.allowed_identity:
            raise RuntimeError("IDENTITY_MISMATCH")
        if auth.target != self.allowed_target:
            raise RuntimeError("TARGET_MISMATCH")
        if auth.capability != self.allowed_capability:
            raise RuntimeError("CAPABILITY_MISMATCH")
        if auth.founder_approval_ref != self.founder_approval_ref or not auth.founder_approval_ref:
            raise RuntimeError("FOUNDER_APPROVAL_MISMATCH")
        if not auth.authority_ref or not auth.mission_binding or not auth.delegation_ref:
            raise RuntimeError("AUTHORITY_BINDING_INCOMPLETE")
        if auth.generation <= 0 or auth.fencing_epoch <= 0:
            raise RuntimeError("GENERATION_OR_FENCING_INVALID")
        now = self.clock()
        if auth.issued_at_unix > now:
            raise RuntimeError("AUTHORITY_NOT_YET_VALID")
        if auth.expires_at_unix <= now:
            raise RuntimeError("AUTHORITY_EXPIRED")
        if auth.estimated_incremental_cost_usd != 0:
            raise RuntimeError("ZERO_SPEND_POLICY_VIOLATION")
        if auth.requires_paid_upgrade:
            raise RuntimeError("PAID_UPGRADE_FORBIDDEN")

    def prepare(self, auth: OrchestratorEffectAuthorization) -> PreparedEffect:
        self._validate(auth)
        request = EffectRequest(
            request_id=auth.request_id,
            actor_id=auth.actor_id,
            target=auth.target,
            capability=auth.capability,
            payload_ref=auth.payload_ref,
            authority_ref=auth.authority_ref,
            mission_binding=auth.mission_binding,
            generation=auth.generation,
            fencing_epoch=auth.fencing_epoch,
            estimated_incremental_cost_usd=auth.estimated_incremental_cost_usd,
            requires_paid_upgrade=auth.requires_paid_upgrade,
        )
        lease = ActivationLease(
            lease_id=f"LEASE:{auth.authorization_id}",
            environment="PRODUCTION",
            allowed_targets=frozenset({auth.target}),
            allowed_capabilities=frozenset({auth.capability}),
            founder_approval_ref=auth.founder_approval_ref,
            active=True,
            max_effects=1,
            expires_at_unix=auth.expires_at_unix,
        )
        policy = ProductionAuthorizationPolicy(
            policy_id=f"POLICY:{auth.authorization_id}",
            allowed_ocs_ids=frozenset({auth.canonical_identity}),
            allowed_target_prefixes=frozenset({auth.target}),
            allowed_capabilities=frozenset({auth.capability}),
            founder_approval_ref=auth.founder_approval_ref,
            zero_unauthorized_spend=True,
            allow_github_merge=False,
            active=True,
        )
        return PreparedEffect(request=request, lease=lease, policy=policy)
