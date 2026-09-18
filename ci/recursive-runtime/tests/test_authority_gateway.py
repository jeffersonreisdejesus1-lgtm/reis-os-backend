import pytest

from authority_gateway import AuthorityGateway, AuthorityGatewayPolicy
from orchestrator_effect_bridge import OrchestratorEffectAuthorization

NOW = 2_000_000_000.0
MISSION = "REIS-AUTHORITY-GATEWAY-V1-IMPLEMENTATION-001"
RUN = "ORCH-RUN-AUTHORITY-GATEWAY-V1-001"
TARGET = "github:jeffersonreisdejesus1-lgtm/reis-os-backend"
CAP = "GITHUB_CREATE_OR_UPDATE_FILE"
APPROVAL = "FOUNDER-BOOTSTRAP-AUTHORITY-GATEWAY-V1-001"
PATH = "ci/recursive-runtime/authority_gateway.py"


def policy(**overrides):
    data = dict(
        policy_id="AUTHORITY-GATEWAY-V1-POLICY-001",
        mission_id=MISSION,
        orchestrator_run_id=RUN,
        mission_stage="IMPLEMENTATION",
        canonical_identity="NOESIS",
        target=TARGET,
        allowed_capabilities=frozenset({CAP}),
        allowed_payload_paths=frozenset({
            PATH,
            "ci/recursive-runtime/tests/test_authority_gateway.py",
            "artifacts/REIS-AUTHORITY-GATEWAY-V1-IMPLEMENTATION-EVIDENCE-001.md",
        }),
        founder_approval_ref=APPROVAL,
    )
    data.update(overrides)
    return AuthorityGatewayPolicy(**data)


def auth(**overrides):
    data = dict(
        authorization_id="AUTHZ:AUTHORITY-GATEWAY-V1:001",
        mission_id=MISSION,
        orchestrator_run_id=RUN,
        mission_stage="IMPLEMENTATION",
        actor_id="actor:noesis:authority-gateway-v1",
        canonical_identity="NOESIS",
        authority_ref="AUTH:NOESIS:AUTHORITY-GATEWAY-V1",
        mission_binding=MISSION,
        delegation_ref="DELEGATION:FOUNDER:NOESIS:AUTHORITY-GATEWAY-V1",
        target=TARGET,
        capability=CAP,
        payload_ref=PATH,
        founder_approval_ref=APPROVAL,
        generation=1,
        fencing_epoch=1,
        request_id="effect:authority-gateway-v1:001",
        evidence_parent="REIS-AUTHORITY-GATEWAY-V1-MISSION-AUTHORIZATION-001",
        issued_at_unix=NOW - 10,
        expires_at_unix=NOW + 600,
    )
    data.update(overrides)
    return OrchestratorEffectAuthorization(**data)


def gateway(p=None):
    return AuthorityGateway(p or policy(), clock=lambda: NOW)


def test_exact_orchestrated_authority_allows_one_bounded_non_merge_effect():
    prepared = gateway().authorize(auth())
    assert prepared.request.payload_ref == PATH
    assert prepared.lease.max_effects == 1
    assert prepared.policy.allow_github_merge is False
    assert prepared.policy.zero_unauthorized_spend is True


def test_capability_is_not_authority():
    with pytest.raises(RuntimeError, match="MISSION_MISMATCH"):
        gateway().authorize(auth(mission_id="UNAUTHORIZED-MISSION"))


def test_payload_surface_escape_fails_closed():
    with pytest.raises(RuntimeError, match="PAYLOAD_SURFACE_MISMATCH"):
        gateway().authorize(auth(payload_ref="README.md"))


def test_merge_capability_cannot_be_configured():
    with pytest.raises(RuntimeError, match="MERGE_CAPABILITY_FORBIDDEN"):
        AuthorityGateway(
            policy(allowed_capabilities=frozenset({"GITHUB_MERGE_PR"})),
            clock=lambda: NOW,
        )


def test_nonzero_cost_fails_closed():
    with pytest.raises(RuntimeError, match="ZERO_SPEND_POLICY_VIOLATION"):
        gateway().authorize(auth(estimated_incremental_cost_usd=0.01))


def test_expired_authority_fails_closed():
    with pytest.raises(RuntimeError, match="AUTHORITY_EXPIRED"):
        gateway().authorize(auth(expires_at_unix=NOW))
