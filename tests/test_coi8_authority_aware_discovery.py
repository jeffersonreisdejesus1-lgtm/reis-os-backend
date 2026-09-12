from dataclasses import replace

import pytest

from app.cognitive_validation.action_receipt import ActionCognitiveReceiptIssuer
from app.cognitive_validation.authority_aware_discovery import (
    AuthorityAwareCapabilityDiscovery,
    AuthorityAwareDiscoveryError,
    AuthorityGrant,
    InstitutionalAuthorityRegistry,
)
from app.cognitive_validation.bootstrap_binding import BootstrapCognitiveBinding
from app.cognitive_validation.capability_fabric import (
    CapabilityHealth,
    CapabilityRecord,
    InstitutionalCapabilityFabric,
)
from app.cognitive_validation.mission_receipt import MissionCognitiveReceiptIssuer


def _system(now=100.0):
    clock = lambda: now
    mission_issuer = MissionCognitiveReceiptIssuer(signing_secret=b"mission", clock=clock)
    action_issuer = ActionCognitiveReceiptIssuer(
        signing_secret=b"action", mission_issuer=mission_issuer, clock=clock
    )
    binding = BootstrapCognitiveBinding(
        binding_id="binding-1",
        mission_id="mission-1",
        ocs_id="NOESIS",
        ocs_instance_id="noesis-1",
        generation=1,
        cognitive_entrypoint="UNIVERSAL_COGNITIVE_ENTRYPOINT",
        brain_path="AB0-AB13/canonical",
        authority_ref="authority:mission-1",
        state_namespace="state:mission-1",
        memory_namespace="memory:mission-1",
    )
    mission = mission_issuer.issue(
        binding,
        intent="intent",
        state_revision="state-r1",
        state_hash="state",
        cognition_cycle_id="cycle-1",
    )
    action = action_issuer.issue(
        mission, plan_hash="plan", action_digest="act", capability_id="github",
        capability_version="v1", adapter_version="adapter-v1",
        authority_requirements=("repo:write",), state_hash="state", policy_version="policy-v1",
    )
    fabric = InstitutionalCapabilityFabric([CapabilityRecord(
        capability_id="github", capability_version="v1", adapter_id="github-adapter",
        adapter_version="adapter-v1", endpoint="github://api", schema_version="schema-v1",
        health=CapabilityHealth.HEALTHY, authorized_missions=("mission-1",),
    )])
    registry = InstitutionalAuthorityRegistry()
    grant = AuthorityGrant(
        authority_id="auth-1", mission_id="mission-1", ocs_id="NOESIS",
        capability_id="github", adapter_version="adapter-v1", operation_class="CLASS_3",
        policy_version="policy-v1", authority_requirements=("repo:write",),
        valid_from=90.0, valid_until=200.0,
    )
    registry.register(grant)
    gateway = AuthorityAwareCapabilityDiscovery(
        capability_fabric=fabric, authority_registry=registry, action_issuer=action_issuer,
        signing_secret=b"authority", clock=clock, nonce_factory=lambda: "nonce",
    )
    return gateway, registry, action, grant


def test_exact_authority_context_enables_governed_discovery():
    gateway, _, action, _ = _system()
    result = gateway.discover(
        capability_id="github", required_schema_version="schema-v1",
        action_receipt=action, authority_id="auth-1", operation_class="CLASS_3",
    )
    assert result.capability_discovery.selected_capability.capability_id == "github"
    assert result.authority_receipt.status == "AUTHORIZED"
    assert gateway.verify_authority_receipt(result.authority_receipt, action_receipt=action)
    assert result.governed_discovery_receipt


@pytest.mark.parametrize("field,value,error", [
    ("mission_id", "other", "authority_mission_id_mismatch"),
    ("ocs_id", "OTHER", "authority_ocs_id_mismatch"),
    ("capability_id", "other", "authority_capability_id_mismatch"),
    ("adapter_version", "other", "authority_adapter_version_mismatch"),
    ("operation_class", "CLASS_2", "authority_operation_class_mismatch"),
    ("policy_version", "other", "authority_policy_version_mismatch"),
])
def test_exact_authority_scope_mismatch_denied(field, value, error):
    gateway, registry, action, grant = _system()
    registry._grants["auth-1"] = replace(grant, **{field: value})
    with pytest.raises(AuthorityAwareDiscoveryError, match=error):
        gateway.discover(
            capability_id="github", required_schema_version="schema-v1",
            action_receipt=action, authority_id="auth-1", operation_class="CLASS_3",
        )


def test_authority_requirements_mismatch_denied():
    gateway, registry, action, grant = _system()
    registry._grants["auth-1"] = replace(grant, authority_requirements=("other",))
    with pytest.raises(AuthorityAwareDiscoveryError, match="authority_requirements_mismatch"):
        gateway.discover(capability_id="github", required_schema_version="schema-v1", action_receipt=action, authority_id="auth-1", operation_class="CLASS_3")


def test_revoked_authority_denied_and_existing_receipt_invalidated():
    gateway, registry, action, _ = _system()
    result = gateway.discover(capability_id="github", required_schema_version="schema-v1", action_receipt=action, authority_id="auth-1", operation_class="CLASS_3")
    registry.revoke("auth-1")
    assert not gateway.verify_authority_receipt(result.authority_receipt, action_receipt=action)
    with pytest.raises(AuthorityAwareDiscoveryError, match="authority_revoked"):
        gateway.discover(capability_id="github", required_schema_version="schema-v1", action_receipt=action, authority_id="auth-1", operation_class="CLASS_3")


def test_expired_authority_denied():
    gateway, registry, action, grant = _system()
    registry._grants["auth-1"] = replace(grant, valid_until=100.0)
    with pytest.raises(AuthorityAwareDiscoveryError, match="authority_expired_or_not_yet_valid"):
        gateway.discover(capability_id="github", required_schema_version="schema-v1", action_receipt=action, authority_id="auth-1", operation_class="CLASS_3")


def test_unregistered_authority_denied():
    gateway, _, action, _ = _system()
    with pytest.raises(AuthorityAwareDiscoveryError, match="authority_not_registered"):
        gateway.discover(capability_id="github", required_schema_version="schema-v1", action_receipt=action, authority_id="missing", operation_class="CLASS_3")


def test_cognitive_action_receipt_cannot_self_authorize():
    gateway, _, action, _ = _system()
    promoted = replace(action, authority_granted=True, effects_permitted=True)
    with pytest.raises(AuthorityAwareDiscoveryError, match="authority_invalid_action_receipt"):
        gateway.discover(capability_id="github", required_schema_version="schema-v1", action_receipt=promoted, authority_id="auth-1", operation_class="CLASS_3")


def test_tampered_authority_receipt_invalid():
    gateway, _, action, _ = _system()
    result = gateway.discover(capability_id="github", required_schema_version="schema-v1", action_receipt=action, authority_id="auth-1", operation_class="CLASS_3")
    tampered = replace(result.authority_receipt, capability_id="other")
    assert not gateway.verify_authority_receipt(tampered, action_receipt=action)


def test_wrong_action_binding_invalidates_authority_receipt():
    gateway, _, action, _ = _system()
    result = gateway.discover(capability_id="github", required_schema_version="schema-v1", action_receipt=action, authority_id="auth-1", operation_class="CLASS_3")
    wrong = replace(action, receipt_id="acr:other")
    assert not gateway.verify_authority_receipt(result.authority_receipt, action_receipt=wrong)


def test_invalid_operation_class_denied():
    gateway, _, action, _ = _system()
    with pytest.raises(AuthorityAwareDiscoveryError, match="authority_operation_class_invalid"):
        gateway.discover(capability_id="github", required_schema_version="schema-v1", action_receipt=action, authority_id="auth-1", operation_class="MODEL_DECIDES")
