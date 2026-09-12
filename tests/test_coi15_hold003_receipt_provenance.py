from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.cognitive_validation.action_receipt import ActionCognitiveReceiptIssuer
from app.cognitive_validation.authority_aware_discovery import (
    AuthorityAwareCapabilityDiscovery, AuthorityGrant, InstitutionalAuthorityRegistry,
)
from app.cognitive_validation.bootstrap_binding import BootstrapCognitiveBinding
from app.cognitive_validation.capability_fabric import CapabilityHealth, CapabilityRecord, InstitutionalCapabilityFabric
from app.cognitive_validation.mission_receipt import MissionCognitiveReceiptIssuer
from app.cognitive_validation.observation_evidence_state import (
    EffectObservation, InstitutionalStateStore, ObservationEvidenceStateUpdater,
)
from app.cognitive_validation.operational_learning_loop import ClosedOperationalLearningLoop
from app.cognitive_validation.receipt_provenance import ReceiptProvenanceError, ReceiptProvenanceVerifier


def _chain():
    now = 100.0
    clock = lambda: now
    mission_issuer = MissionCognitiveReceiptIssuer(signing_secret=b"mission", clock=clock, nonce_factory=lambda: "mission-nonce")
    action_issuer = ActionCognitiveReceiptIssuer(signing_secret=b"action", mission_issuer=mission_issuer, clock=clock, nonce_factory=lambda: "action-nonce")
    binding = BootstrapCognitiveBinding(
        binding_id="binding-1", mission_id="mission-1", ocs_id="NOESIS", ocs_instance_id="noesis-1",
        generation=1, cognitive_entrypoint="UNIVERSAL_COGNITIVE_ENTRYPOINT", brain_path="AB0-AB13/canonical",
        authority_ref="authority:mission-1", state_namespace="state:mission-1", memory_namespace="memory:mission-1",
    )
    mission = mission_issuer.issue(binding, intent="build governed artifact", state_revision="r1", state_hash="state-0", cognition_cycle_id="cycle-1")
    action = action_issuer.issue(
        mission, plan_hash="plan-1", action_digest="write-artifact", capability_id="github",
        capability_version="v1", adapter_version="adapter-v1", authority_requirements=("repo:write",),
        state_hash="state-0", policy_version="policy-v1",
    )
    fabric = InstitutionalCapabilityFabric([CapabilityRecord(
        capability_id="github", capability_version="v1", adapter_id="github-adapter", adapter_version="adapter-v1",
        endpoint="github://api", schema_version="schema-v1", health=CapabilityHealth.HEALTHY,
        authorized_missions=("mission-1",),
    )])
    registry = InstitutionalAuthorityRegistry()
    registry.register(AuthorityGrant(
        authority_id="auth-1", mission_id="mission-1", ocs_id="NOESIS", capability_id="github",
        adapter_version="adapter-v1", operation_class="CLASS_3", policy_version="policy-v1",
        authority_requirements=("repo:write",), valid_from=90.0, valid_until=200.0,
    ))
    authority_gateway = AuthorityAwareCapabilityDiscovery(
        capability_fabric=fabric, authority_registry=registry, action_issuer=action_issuer,
        signing_secret=b"authority", clock=clock, nonce_factory=lambda: "authority-nonce",
    )
    discovery = authority_gateway.discover(
        capability_id="github", required_schema_version="schema-v1", action_receipt=action,
        authority_id="auth-1", operation_class="CLASS_3",
    )
    execution = SimpleNamespace(
        mission_id="mission-1", capability_id="github", ocs_id="NOESIS",
        governed_execution_receipt="governed-exec-1", execution_status="EXECUTED_CONFIRMED",
        adapter_execution_receipt=SimpleNamespace(execution_receipt="adapter-exec-1"),
    )
    observation = EffectObservation(
        mission_id="mission-1", capability_id="github", ocs_id="NOESIS",
        governed_execution_receipt="governed-exec-1", execution_status="EXECUTED_CONFIRMED",
        observed_effect={"commit":"abc123"},
    )
    coi11 = ObservationEvidenceStateUpdater(state_store=InstitutionalStateStore()).qualify_and_update(
        execution=execution, observation=observation, state_delta={"last_commit":"abc123"},
    )
    loop = ClosedOperationalLearningLoop()
    previous = loop.initial_plan(mission_id="mission-1", capability_id="github", state_hash="state-0")
    learning = loop.close_loop(previous_plan=previous, coi11_result=coi11, candidate_capabilities=("github","notion"), outcome="FAILURE")
    verifier = ReceiptProvenanceVerifier(
        mission_issuer=mission_issuer, action_issuer=action_issuer, authority_discovery=authority_gateway,
    )
    return verifier, mission, action, discovery.authority_receipt, execution, coi11, learning


def test_authentic_receipts_and_full_lineage_qualify():
    verifier, mission, action, authority, execution, coi11, learning = _chain()
    result = verifier.verify(
        mission=mission, action=action, authority=authority, execution=execution,
        coi11=coi11, learning=learning, verification_time=100.0,
    )
    assert result.mission_receipt_id.startswith("mcr:")
    assert result.action_receipt_id.startswith("acr:")
    assert result.authority_receipt_id.startswith("authr:")
    assert result.evidence_receipt == coi11.evidence.evidence_receipt
    assert result.learning_receipt == learning.learning_receipt
    assert len(result.lineage_receipt) == 64


def test_tampered_mission_signature_is_rejected():
    verifier, mission, action, authority, execution, coi11, learning = _chain()
    with pytest.raises(ReceiptProvenanceError, match="invalid_mission_receipt"):
        verifier.verify(mission=replace(mission, signature="forged"), action=action, authority=authority,
                        execution=execution, coi11=coi11, learning=learning, verification_time=100.0)


def test_tampered_action_context_is_rejected():
    verifier, mission, action, authority, execution, coi11, learning = _chain()
    with pytest.raises(ReceiptProvenanceError, match="invalid_action_receipt"):
        verifier.verify(mission=mission, action=replace(action, capability_id="notion"), authority=authority,
                        execution=execution, coi11=coi11, learning=learning, verification_time=100.0)


def test_expired_action_is_rejected():
    verifier, mission, action, authority, execution, coi11, learning = _chain()
    with pytest.raises(ReceiptProvenanceError, match="invalid_action_receipt"):
        verifier.verify(mission=mission, action=action, authority=authority, execution=execution,
                        coi11=coi11, learning=learning, verification_time=action.expires_at)


def test_wrong_authority_lineage_is_rejected():
    verifier, mission, action, authority, execution, coi11, learning = _chain()
    with pytest.raises(ReceiptProvenanceError, match="invalid_authority_receipt"):
        verifier.verify(mission=mission, action=action, authority=replace(authority, action_receipt_id="acr:other"),
                        execution=execution, coi11=coi11, learning=learning, verification_time=100.0)


def test_falsified_evidence_receipt_is_rejected():
    verifier, mission, action, authority, execution, coi11, learning = _chain()
    forged = replace(coi11, evidence=replace(coi11.evidence, evidence_receipt="forged"))
    with pytest.raises(ReceiptProvenanceError, match="evidence_receipt_invalid"):
        verifier.verify(mission=mission, action=action, authority=authority, execution=execution,
                        coi11=forged, learning=learning, verification_time=100.0)


def test_learning_must_consume_exact_evidence_and_state():
    verifier, mission, action, authority, execution, coi11, learning = _chain()
    forged_learning = replace(learning, feedback=replace(learning.feedback, state_hash="forged"))
    with pytest.raises(ReceiptProvenanceError, match="learning_state_mismatch"):
        verifier.verify(mission=mission, action=action, authority=authority, execution=execution,
                        coi11=coi11, learning=forged_learning, verification_time=100.0)
