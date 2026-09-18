from dataclasses import replace
import pytest
from app.cognitive_validation.action_receipt import ActionCognitiveReceiptIssuer
from app.cognitive_validation.adapter_fabric import AdapterHealth, AdapterRecord, InstitutionalAdapterFabric
from app.cognitive_validation.authority_aware_discovery import AuthorityAwareCapabilityDiscovery, AuthorityGrant, InstitutionalAuthorityRegistry
from app.cognitive_validation.bootstrap_binding import BootstrapCognitiveBinding
from app.cognitive_validation.capability_fabric import CapabilityHealth, CapabilityRecord, InstitutionalCapabilityFabric
from app.cognitive_validation.governed_execution import GovernedSoftwareExecutionError, GovernedSoftwareExecutor, SoftwareSelectionRequest
from app.cognitive_validation.mission_receipt import MissionCognitiveReceiptIssuer
from app.cognitive_validation.ocs_composition import GovernedOCSComposer, InstitutionalOCSRegistry, OCSCompositionRequest, OCSRecord
from app.cognitive_validation.runtime_anti_bypass import RuntimeAntiBypassGateway, RuntimeExecutionContext

def _system():
    clock=lambda:100.0
    mi=MissionCognitiveReceiptIssuer(signing_secret=b"m",clock=clock)
    ai=ActionCognitiveReceiptIssuer(signing_secret=b"a",mission_issuer=mi,clock=clock)
    binding=BootstrapCognitiveBinding(binding_id="b",mission_id="mission-1",ocs_id="SOFIA",ocs_instance_id="sofia-1",generation=1,cognitive_entrypoint="UNIVERSAL_COGNITIVE_ENTRYPOINT",brain_path="AB0-AB13/canonical",authority_ref="auth",state_namespace="state",memory_namespace="memory")
    mission=mi.issue(binding,intent="implement",state_revision="r1",state_hash="state",cognition_cycle_id="c1")
    action=ai.issue(mission,plan_hash="plan",action_digest="act",capability_id="github",capability_version="v1",adapter_version="a1",authority_requirements=("repo:write",),state_hash="state",policy_version="p1")
    cf=InstitutionalCapabilityFabric([CapabilityRecord(capability_id="github",capability_version="v1",adapter_id="github-adapter",adapter_version="a1",endpoint="github://api",schema_version="s1",health=CapabilityHealth.HEALTHY,authorized_missions=("mission-1",))])
    ar=InstitutionalAuthorityRegistry(); ar.register(AuthorityGrant(authority_id="auth-1",mission_id="mission-1",ocs_id="SOFIA",capability_id="github",adapter_version="a1",operation_class="CLASS_3",policy_version="p1",authority_requirements=("repo:write",),valid_from=90,valid_until=200))
    ad=AuthorityAwareCapabilityDiscovery(capability_fabric=cf,authority_registry=ar,action_issuer=ai,signing_secret=b"auth",clock=clock,nonce_factory=lambda:"n")
    discovery=ad.discover(capability_id="github",required_schema_version="s1",action_receipt=action,authority_id="auth-1",operation_class="CLASS_3")
    reg=InstitutionalOCSRegistry(); reg.register(OCSRecord(ocs_id="SOFIA",ocs_version="v1",identity_ref="i",constitution_ref="c",cognitive_entrypoint="UNIVERSAL_COGNITIVE_ENTRYPOINT",runtime_endpoint="internal://sofia",supported_capabilities=("github",),authority_requirements=("repo:write",),required_receipts=("MISSION_COGNITIVE_RECEIPT","ACTION_COGNITIVE_RECEIPT","AUTHORITY_RECEIPT")))
    composition=GovernedOCSComposer(reg).compose(OCSCompositionRequest(mission_id="mission-1",plan_hash="plan",required_capabilities=("github",),governed_discovery_receipts=(discovery.governed_discovery_receipt,)),[discovery])
    af=InstitutionalAdapterFabric(); calls=[]
    def handler(payload): calls.append(dict(payload)); return {"ok":True}
    af.register(AdapterRecord(adapter_id="github-adapter",adapter_version="a1",capability_id="github",capability_version="v1",endpoint="github://api",input_schema_version="s1",output_schema_version="out1",health=AdapterHealth.HEALTHY),handler)
    executor=GovernedSoftwareExecutor(authority_discovery=ad,anti_bypass=RuntimeAntiBypassGateway(action_issuer=ai),adapter_fabric=af)
    selection=SoftwareSelectionRequest("mission-1","github","SOFIA",composition.composition_receipt,discovery.governed_discovery_receipt,action.receipt_id,discovery.authority_receipt.receipt_id)
    runtime=RuntimeExecutionContext("mission-1","SOFIA","sofia-1",1,"github","v1","a1","act","state","p1")
    return executor,selection,composition,discovery,action,runtime,calls,ar

def test_exact_chain_executes_once():
    e,s,c,d,a,r,calls,_=_system(); result=e.execute(selection=s,composition=c,discovery=d,action_receipt=a,runtime_context=r,payload={"x":1},input_schema_version="s1",expected_output_schema_version="out1")
    assert result.execution_status=="EXECUTED_CONFIRMED" and result.response=={"ok":True} and calls==[{"x":1}] and result.governed_execution_receipt

def test_composition_mismatch_denied_before_effect():
    e,s,c,d,a,r,calls,_=_system()
    with pytest.raises(GovernedSoftwareExecutionError,match="composition_receipt_mismatch"): e.execute(selection=replace(s,composition_receipt="bad"),composition=c,discovery=d,action_receipt=a,runtime_context=r,payload={},input_schema_version="s1",expected_output_schema_version="out1")
    assert calls==[]

def test_ocs_assignment_mismatch_denied():
    e,s,c,d,a,r,calls,_=_system()
    with pytest.raises(GovernedSoftwareExecutionError,match="ocs_assignment_mismatch"): e.execute(selection=replace(s,ocs_id="NOESIS"),composition=c,discovery=d,action_receipt=a,runtime_context=replace(r,ocs_id="NOESIS"),payload={},input_schema_version="s1",expected_output_schema_version="out1")
    assert calls==[]

def test_revoked_authority_denied_before_effect():
    e,s,c,d,a,r,calls,registry=_system(); registry.revoke("auth-1")
    with pytest.raises(GovernedSoftwareExecutionError,match="invalid_authority"): e.execute(selection=s,composition=c,discovery=d,action_receipt=a,runtime_context=r,payload={},input_schema_version="s1",expected_output_schema_version="out1")
    assert calls==[]

def test_runtime_context_mismatch_denied():
    e,s,c,d,a,r,calls,_=_system()
    with pytest.raises(GovernedSoftwareExecutionError,match="runtime_capability_mismatch"): e.execute(selection=s,composition=c,discovery=d,action_receipt=a,runtime_context=replace(r,capability_id="other"),payload={},input_schema_version="s1",expected_output_schema_version="out1")
    assert calls==[]

def test_replay_cannot_execute_twice():
    e,s,c,d,a,r,calls,_=_system(); e.execute(selection=s,composition=c,discovery=d,action_receipt=a,runtime_context=r,payload={},input_schema_version="s1",expected_output_schema_version="out1")
    with pytest.raises(GovernedSoftwareExecutionError,match="denied_or_failed"): e.execute(selection=s,composition=c,discovery=d,action_receipt=a,runtime_context=r,payload={},input_schema_version="s1",expected_output_schema_version="out1")
    assert len(calls)==1

def test_schema_mismatch_never_reaches_handler():
    e,s,c,d,a,r,calls,_=_system()
    with pytest.raises(GovernedSoftwareExecutionError,match="denied_or_failed"): e.execute(selection=s,composition=c,discovery=d,action_receipt=a,runtime_context=r,payload={},input_schema_version="wrong",expected_output_schema_version="out1")
    assert calls==[]
