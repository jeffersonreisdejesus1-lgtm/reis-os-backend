from dataclasses import dataclass
from typing import FrozenSet

from orchestrator_effect_bridge import (
    OrchestratorEffectAuthorization,
    OrchestratorEffectBridge,
    PreparedEffect,
)


@dataclass(frozen=True)
class AuthorityGatewayPolicy:
    policy_id: str
    mission_id: str
    orchestrator_run_id: str
    mission_stage: str
    canonical_identity: str
    target: str
    allowed_capabilities: FrozenSet[str]
    allowed_payload_paths: FrozenSet[str]
    founder_approval_ref: str


class AuthorityGateway:
    """Fail-closed institutional execution gate.

    Capability alone never authorizes mutation. A request must also match the exact
    orchestrated mission, run, stage, identity, target, payload surface, Founder
    approval and zero-spend constraints before a single bounded effect is prepared.
    """

    def __init__(self, policy: AuthorityGatewayPolicy, *, clock=None):
        if not policy.allowed_capabilities:
            raise RuntimeError("NO_CAPABILITY_SCOPE")
        if "GITHUB_MERGE_PR" in policy.allowed_capabilities:
            raise RuntimeError("MERGE_CAPABILITY_FORBIDDEN")
        self.policy = policy
        self.clock = clock

    def authorize(self, auth: OrchestratorEffectAuthorization) -> PreparedEffect:
        p = self.policy
        if auth.capability not in p.allowed_capabilities:
            raise RuntimeError("CAPABILITY_MISMATCH")
        if auth.payload_ref not in p.allowed_payload_paths:
            raise RuntimeError("PAYLOAD_SURFACE_MISMATCH")

        bridge = OrchestratorEffectBridge(
            expected_mission_id=p.mission_id,
            expected_run_id=p.orchestrator_run_id,
            expected_stage=p.mission_stage,
            allowed_identity=p.canonical_identity,
            allowed_target=p.target,
            allowed_capability=auth.capability,
            founder_approval_ref=p.founder_approval_ref,
            clock=self.clock,
        )
        prepared = bridge.prepare(auth)
        if prepared.policy.allow_github_merge:
            raise RuntimeError("MERGE_CAPABILITY_FORBIDDEN")
        if prepared.lease.max_effects != 1:
            raise RuntimeError("UNBOUNDED_EFFECT_FORBIDDEN")
        return prepared
