from dataclasses import replace

import pytest

from app.cognitive_validation.authority_aware_discovery import (
    AuthorityAwareDiscoveryResult,
    AuthorityReceipt,
)
from app.cognitive_validation.capability_fabric import (
    CapabilityDiscoveryResult,
    CapabilityRecord,
    CapabilityHealth,
)
from app.cognitive_validation.ocs_composition import (
    GovernedOCSComposer,
    InstitutionalOCSRegistry,
    OCSCompositionError,
    OCSCompositionRequest,
    OCSRecord,
)


def _discovery(capability_id="github", mission_id="mission-1", governed="gdr-1"):
    record = CapabilityRecord(
        capability_id=capability_id,
        capability_version="v1",
        adapter_id=f"{capability_id}-adapter",
        adapter_version="a1",
        endpoint=f"internal://{capability_id}",
        schema_version="s1",
        health=CapabilityHealth.HEALTHY,
        authorized_missions=(mission_id,),
    )
    capability = CapabilityDiscoveryResult(
        selected_capability=record,
        registry_snapshot="registry",
        health_snapshot="health",
        authority_snapshot="authority",
        schema_snapshot="schema",
        discovery_receipt="cdr",
    )
    receipt = AuthorityReceipt(
        receipt_id="authr-1",
        authority_id="authority-1",
        action_receipt_id="action-1",
        mission_id=mission_id,
        ocs_id="NOESIS",
        capability_id=capability_id,
        adapter_version="a1",
        operation_class="CLASS_2",
        policy_version="p1",
        action_digest="act",
        issued_at=100.0,
        expires_at=200.0,
        nonce="n",
        status="AUTHORIZED",
        integrity_hash="ih",
        signature="sig",
    )
    return AuthorityAwareDiscoveryResult(capability, receipt, "as", governed)


def _registry(healthy=True):
    registry = InstitutionalOCSRegistry()
    registry.register(OCSRecord(
        ocs_id="SOFIA",
        ocs_version="v1",
        identity_ref="identity:sofia",
        constitution_ref="constitution:sofia",
        cognitive_entrypoint="UNIVERSAL_COGNITIVE_ENTRYPOINT",
        runtime_endpoint="internal://sofia",
        supported_capabilities=("github",),
        authority_requirements=("repo_write",),
        required_receipts=("MISSION_COGNITIVE_RECEIPT", "ACTION_COGNITIVE_RECEIPT", "AUTHORITY_RECEIPT"),
        healthy=healthy,
    ))
    return registry


def _request(receipts=("gdr-1",), capabilities=("github",)):
    return OCSCompositionRequest(
        mission_id="mission-1", plan_hash="plan-1",
        required_capabilities=capabilities,
        governed_discovery_receipts=receipts,
    )


def test_composes_registered_healthy_ocs_from_exact_governed_discovery():
    result = GovernedOCSComposer(_registry()).compose(_request(), [_discovery()])
    assert result.capability_assignments == (("github", "SOFIA"),)
    assert result.selected_ocs[0].ocs_id == "SOFIA"
    assert result.composition_receipt


def test_empty_registry_fails_closed():
    with pytest.raises(OCSCompositionError, match="registry_empty"):
        GovernedOCSComposer(InstitutionalOCSRegistry()).compose(_request(), [_discovery()])


def test_unhealthy_ocs_is_not_eligible():
    with pytest.raises(OCSCompositionError, match="no_eligible_ocs"):
        GovernedOCSComposer(_registry(False)).compose(_request(), [_discovery()])


def test_mission_mismatch_denied():
    with pytest.raises(OCSCompositionError, match="mission_mismatch"):
        GovernedOCSComposer(_registry()).compose(_request(), [_discovery(mission_id="other")])


def test_discovery_receipt_set_mismatch_denied():
    with pytest.raises(OCSCompositionError, match="receipt_set_mismatch"):
        GovernedOCSComposer(_registry()).compose(_request(receipts=("wrong",)), [_discovery()])


def test_capability_set_mismatch_denied():
    with pytest.raises(OCSCompositionError, match="capability_set_mismatch"):
        GovernedOCSComposer(_registry()).compose(_request(capabilities=("github", "notion")), [_discovery()])


def test_non_authorized_receipt_denied():
    discovery = _discovery()
    discovery = replace(discovery, authority_receipt=replace(discovery.authority_receipt, status="DENIED"))
    with pytest.raises(OCSCompositionError, match="not_authorized"):
        GovernedOCSComposer(_registry()).compose(_request(), [discovery])


def test_duplicate_ocs_registration_denied():
    registry = _registry()
    with pytest.raises(OCSCompositionError, match="duplicate_registration"):
        registry.register(registry.records()[0])


def test_missing_required_receipt_contract_denied():
    registry = InstitutionalOCSRegistry()
    registry.register(OCSRecord(
        ocs_id="SOFIA", ocs_version="v1", identity_ref="i", constitution_ref="c",
        cognitive_entrypoint="entry", runtime_endpoint="endpoint",
        supported_capabilities=("github",), authority_requirements=("repo_write",),
        required_receipts=("MISSION_COGNITIVE_RECEIPT", "ACTION_COGNITIVE_RECEIPT"), healthy=True,
    ))
    with pytest.raises(OCSCompositionError, match="no_eligible_ocs"):
        GovernedOCSComposer(registry).compose(_request(), [_discovery()])


def test_composition_receipt_is_context_bound():
    composer = GovernedOCSComposer(_registry())
    first = composer.compose(_request(), [_discovery()])
    second = composer.compose(replace(_request(), plan_hash="plan-2"), [_discovery()])
    assert first.composition_receipt != second.composition_receipt
