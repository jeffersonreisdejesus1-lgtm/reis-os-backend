import pytest

from production_effects import (
    ActivationLease,
    EffectRequest,
    GitHubProductionAdapter,
    ProductionAuthorizationPolicy,
    ProductionEffectAdapter,
    ProductionEffectGateway,
    RenderProductionAdapter,
    SandboxEffectAdapter,
)
from ocs_operationalization import OCSRuntimeEnforcer
from recursive_runtime.contracts.model import *
from recursive_runtime.repositories.state import *
from recursive_runtime.services.core import *
from recursive_runtime.runtime.integrated_runtime import IntegratedRuntime


def build_gateway(adapter=None, lease=None, policy=None, capabilities=None):
    capabilities = capabilities or frozenset({"analyze","delegate","publish"})
    states=StateRepository(); receipts=ReceiptRepository(); cps=CheckpointRepository(); ledger=BudgetLedger(); ledger.bind("B1","provider-canonical",20)
    actor=ActorState(actor_id="a",identity_id="NOESIS",session_binding="S1",mission_binding="M1",state_namespace="ns:a",authority=AuthorityGrant("AUTH:1",frozenset({"read","write","delegate"})),capability=CapabilityBinding("CAP:1",capabilities,frozenset({"tool:a"})),budget_ref="B1",provider_id="provider-canonical",trace_id="T1",span_id="span:a",generation=1,fencing_epoch=1,cancellation_policy_ref="C1")
    states.add(actor); trace=TraceService(receipts); trace.emit("SPAN_OPEN",actor,"ROOT")
    enforcer=OCSRuntimeEnforcer(); adapter=adapter or SandboxEffectAdapter(); gateway=ProductionEffectGateway(states,trace,enforcer,adapter,lease,policy)
    runtime=IntegratedRuntime(states,SelfInspectionService(states),ReflectionEngine(),SpawnTransactionService(states,ledger,trace),CancellationService(states,{"C1":CancellationPolicy("C1")},trace),RecoveryService(states,cps,trace),trace,StopEngine(),AssuranceGate(),ocs_enforcer=enforcer,production_effect_gateway=gateway)
    return states,receipts,adapter,gateway,runtime


def req(**overrides):
    data=dict(request_id="fx:1",actor_id="a",target="qualified-target",capability="publish",payload_ref="payload:1",authority_ref="AUTH:1",mission_binding="M1",generation=1,fencing_epoch=1)
    data.update(overrides); return EffectRequest(**data)


def active_policy(*,targets=frozenset({"github:","render:"}), capabilities=frozenset({"GITHUB_CREATE_BRANCH","GITHUB_CREATE_OR_UPDATE_FILE","GITHUB_OPEN_PR","GITHUB_UPDATE_PR","GITHUB_MERGE_PR","RENDER_TRIGGER_DEPLOY"})):
    return ProductionAuthorizationPolicy(
        policy_id="SYN-R004-GITHUB-RENDER-ZERO-SPEND-V1",
        allowed_ocs_ids=frozenset({"NOESIS","SOFIA","AGORA"}),
        allowed_target_prefixes=targets,
        allowed_capabilities=capabilities,
        founder_approval_ref="FOUNDER-FINAL-GATE-TEST",
        zero_unauthorized_spend=True,
        active=True,
    )


def lease(target, capability):
    return ActivationLease("L1","PRODUCTION",frozenset({target}),frozenset({capability}),"FOUNDER-FINAL-GATE-TEST",True)


def test_sandbox_effect_is_traceable_and_idempotent():
    _,receipts,adapter,gateway,runtime=build_gateway()
    r=runtime.execute_production_effect(req())
    assert r.status == "SIMULATED"
    assert runtime.execute_production_effect(req()) == r
    assert len(adapter.calls) == 1
    assert len(gateway.receipts()) == 1
    assert any(x.kind == "PRODUCTION_EFFECT_GATEWAY" for x in receipts.all())


def test_conflicting_request_id_fails_closed():
    states,_,_,_,runtime=build_gateway(); runtime.execute_production_effect(req())
    with pytest.raises(RuntimeError, match="EFFECT_REQUEST_ID_CONFLICT"):
        runtime.execute_production_effect(req(payload_ref="payload:other"))
    assert states.get("a").lifecycle is Lifecycle.FAILED_CLOSED


@pytest.mark.parametrize("field,value,reason",[
    ("authority_ref","AUTH:OTHER","EFFECT_AUTHORITY_MISMATCH"),
    ("mission_binding","M2","EFFECT_MISSION_MISMATCH"),
    ("capability","delete","EFFECT_CAPABILITY_NOT_BOUND"),
    ("generation",2,"STALE_GENERATION"),
    ("fencing_epoch",2,"STALE_FENCING"),
])
def test_common_boundaries_fail_closed(field,value,reason):
    states,_,_,_,runtime=build_gateway()
    with pytest.raises(Exception, match=reason): runtime.execute_production_effect(req(**{field:value}))
    assert states.get("a").lifecycle is Lifecycle.FAILED_CLOSED


def test_real_production_adapter_requires_activation_lease():
    states,_,_,_,runtime=build_gateway(adapter=ProductionEffectAdapter())
    with pytest.raises(RuntimeError, match="PRODUCTION_ACTIVATION_REQUIRED"):
        runtime.execute_production_effect(req())
    assert states.get("a").lifecycle is Lifecycle.FAILED_CLOSED


def test_real_production_adapter_requires_active_production_policy_after_lease():
    l=ActivationLease("L1","PRODUCTION",frozenset({"qualified-target"}),frozenset({"publish"}),"FOUNDER-FINAL-GATE-PENDING",True)
    states,_,_,_,runtime=build_gateway(adapter=ProductionEffectAdapter(),lease=l)
    with pytest.raises(RuntimeError, match="PRODUCTION_POLICY_NOT_ACTIVE"):
        runtime.execute_production_effect(req())
    assert states.get("a").lifecycle is Lifecycle.FAILED_CLOSED


def test_lease_target_allowlist_precedes_adapter_call():
    l=ActivationLease("L1","PRODUCTION",frozenset({"other-target"}),frozenset({"publish"}),"FOUNDER-FINAL-GATE-PENDING",True)
    with pytest.raises(RuntimeError, match="PRODUCTION_TARGET_NOT_ALLOWED"):
        build_gateway(adapter=ProductionEffectAdapter(),lease=l)[4].execute_production_effect(req())


def test_lease_capability_allowlist_precedes_adapter_call():
    l=ActivationLease("L1","PRODUCTION",frozenset({"qualified-target"}),frozenset({"other"}),"FOUNDER-FINAL-GATE-PENDING",True)
    with pytest.raises(RuntimeError, match="PRODUCTION_CAPABILITY_NOT_ALLOWED"):
        build_gateway(adapter=ProductionEffectAdapter(),lease=l)[4].execute_production_effect(req())


def test_founder_approval_reference_required():
    l=ActivationLease("L1","PRODUCTION",frozenset({"qualified-target"}),frozenset({"publish"}),"",True)
    with pytest.raises(RuntimeError, match="FOUNDER_APPROVAL_REF_REQUIRED"):
        build_gateway(adapter=ProductionEffectAdapter(),lease=l)[4].execute_production_effect(req())


def test_gateway_missing_fails_closed_without_effect():
    states,_,_,_,runtime=build_gateway(); runtime.production_effect_gateway=None
    assert runtime.execute_production_effect(req()) is Outcome.FAIL_CLOSED
    assert states.get("a").lifecycle is Lifecycle.FAILED_CLOSED


def test_github_adapter_commits_only_when_lease_policy_and_zero_spend_align():
    calls=[]
    adapter=GitHubProductionAdapter(lambda r: calls.append(r) or "github:commit:test")
    capability="GITHUB_CREATE_OR_UPDATE_FILE"; target="github:jeffersonreisdejesus1-lgtm/reis-os-backend"
    request=req(target=target,capability=capability)
    _,receipts,_,gateway,runtime=build_gateway(adapter=adapter,lease=lease(target,capability),policy=active_policy(),capabilities=frozenset({capability}))
    out=runtime.execute_production_effect(request)
    assert out.status == "COMMITTED" and out.result_ref == "github:commit:test"
    assert len(calls)==1 and len(gateway.receipts())==1
    assert any(x.kind == "PRODUCTION_EFFECT_GATEWAY" for x in receipts.all())


def test_render_adapter_commits_only_when_lease_policy_and_zero_spend_align():
    calls=[]
    adapter=RenderProductionAdapter(lambda r: calls.append(r) or "render:deploy:test")
    capability="RENDER_TRIGGER_DEPLOY"; target="render:srv-qualified"
    request=req(target=target,capability=capability)
    _,_,_,gateway,runtime=build_gateway(adapter=adapter,lease=lease(target,capability),policy=active_policy(),capabilities=frozenset({capability}))
    out=runtime.execute_production_effect(request)
    assert out.status == "COMMITTED" and out.result_ref == "render:deploy:test"
    assert len(calls)==1 and len(gateway.receipts())==1


def test_zero_spend_policy_blocks_nonzero_incremental_cost_before_provider_call():
    calls=[]
    capability="GITHUB_CREATE_OR_UPDATE_FILE"; target="github:jeffersonreisdejesus1-lgtm/reis-os-backend"
    adapter=GitHubProductionAdapter(lambda r: calls.append(r) or "should-not-run")
    request=req(target=target,capability=capability,estimated_incremental_cost_usd=0.01)
    with pytest.raises(RuntimeError, match="ZERO_SPEND_POLICY_VIOLATION"):
        build_gateway(adapter=adapter,lease=lease(target,capability),policy=active_policy(),capabilities=frozenset({capability}))[4].execute_production_effect(request)
    assert calls == []


def test_zero_spend_policy_blocks_paid_upgrade_before_provider_call():
    calls=[]
    capability="RENDER_TRIGGER_DEPLOY"; target="render:srv-qualified"
    adapter=RenderProductionAdapter(lambda r: calls.append(r) or "should-not-run")
    request=req(target=target,capability=capability,requires_paid_upgrade=True)
    with pytest.raises(RuntimeError, match="PAID_UPGRADE_FORBIDDEN"):
        build_gateway(adapter=adapter,lease=lease(target,capability),policy=active_policy(),capabilities=frozenset({capability}))[4].execute_production_effect(request)
    assert calls == []


def test_founder_approval_refs_must_match():
    capability="GITHUB_CREATE_BRANCH"; target="github:jeffersonreisdejesus1-lgtm/reis-os-backend"
    l=ActivationLease("L1","PRODUCTION",frozenset({target}),frozenset({capability}),"FOUNDER-A",True)
    policy=ProductionAuthorizationPolicy("P1",frozenset({"NOESIS"}),frozenset({"github:"}),frozenset({capability}),"FOUNDER-B",True,True)
    with pytest.raises(RuntimeError, match="FOUNDER_APPROVAL_REF_MISMATCH"):
        build_gateway(adapter=GitHubProductionAdapter(lambda r:"never"),lease=l,policy=policy,capabilities=frozenset({capability}))[4].execute_production_effect(req(target=target,capability=capability))


def test_provider_target_prefix_and_capability_are_enforced():
    gh=GitHubProductionAdapter(lambda r:"never")
    with pytest.raises(RuntimeError, match="GITHUB_TARGET_FORBIDDEN"):
        gh.execute(req(target="render:srv-x",capability="GITHUB_CREATE_BRANCH"))
    rd=RenderProductionAdapter(lambda r:"never")
    with pytest.raises(RuntimeError, match="RENDER_CAPABILITY_FORBIDDEN"):
        rd.execute(req(target="render:srv-x",capability="GITHUB_OPEN_PR"))
