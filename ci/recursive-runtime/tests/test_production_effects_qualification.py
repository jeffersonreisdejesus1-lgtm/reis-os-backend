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
    VerifiedCostDecision,
)
from ocs_operationalization import OCSRuntimeEnforcer
from recursive_runtime.contracts.model import *
from recursive_runtime.repositories.state import *
from recursive_runtime.services.core import *
from recursive_runtime.runtime.integrated_runtime import IntegratedRuntime

NOW=2_000_000_000.0


def good_approval(ref): return ref == "FOUNDER-FINAL-GATE-TEST"
def zero_cost(_): return VerifiedCostDecision(0.0,False,"VERIFIED-COST-PREFLIGHT-TEST")


def build_gateway(adapter=None, lease=None, policy=None, capabilities=None, approval_verifier=None, cost_preflight=None, clock=None):
    capabilities = capabilities or frozenset({"analyze","delegate","publish"})
    states=StateRepository(); receipts=ReceiptRepository(); cps=CheckpointRepository(); ledger=BudgetLedger(); ledger.bind("B1","provider-canonical",20)
    actor=ActorState(actor_id="a",identity_id="NOESIS",session_binding="S1",mission_binding="M1",state_namespace="ns:a",authority=AuthorityGrant("AUTH:1",frozenset({"read","write","delegate"})),capability=CapabilityBinding("CAP:1",capabilities,frozenset({"tool:a"})),budget_ref="B1",provider_id="provider-canonical",trace_id="T1",span_id="span:a",generation=1,fencing_epoch=1,cancellation_policy_ref="C1")
    states.add(actor); trace=TraceService(receipts); trace.emit("SPAN_OPEN",actor,"ROOT")
    enforcer=OCSRuntimeEnforcer(); adapter=adapter or SandboxEffectAdapter(); gateway=ProductionEffectGateway(states,trace,enforcer,adapter,lease,policy,approval_verifier,cost_preflight,clock or (lambda: NOW))
    runtime=IntegratedRuntime(states,SelfInspectionService(states),ReflectionEngine(),SpawnTransactionService(states,ledger,trace),CancellationService(states,{"C1":CancellationPolicy("C1")},trace),RecoveryService(states,cps,trace),trace,StopEngine(),AssuranceGate(),ocs_enforcer=enforcer,production_effect_gateway=gateway)
    return states,receipts,adapter,gateway,runtime


def req(**overrides):
    data=dict(request_id="fx:1",actor_id="a",target="qualified-target",capability="publish",payload_ref="payload:1",authority_ref="AUTH:1",mission_binding="M1",generation=1,fencing_epoch=1)
    data.update(overrides); return EffectRequest(**data)


def active_policy(*,targets=frozenset({"github:","render:"}), capabilities=frozenset({"GITHUB_CREATE_BRANCH","GITHUB_CREATE_OR_UPDATE_FILE","GITHUB_OPEN_PR","GITHUB_UPDATE_PR","GITHUB_MERGE_PR","RENDER_TRIGGER_DEPLOY"}), allow_merge=False):
    return ProductionAuthorizationPolicy(
        policy_id="SYN-R004-GITHUB-RENDER-ZERO-SPEND-V1",
        allowed_ocs_ids=frozenset({"NOESIS","SOFIA","AGORA"}),
        allowed_target_prefixes=targets,
        allowed_capabilities=capabilities,
        founder_approval_ref="FOUNDER-FINAL-GATE-TEST",
        zero_unauthorized_spend=True,
        allow_github_merge=allow_merge,
        active=True,
    )


def lease(target, capability, *, max_effects=1, expires=NOW+3600):
    return ActivationLease("L1","PRODUCTION",frozenset({target}),frozenset({capability}),"FOUNDER-FINAL-GATE-TEST",True,max_effects,expires)


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


def test_real_production_adapter_requires_active_policy():
    l=ActivationLease("L1","PRODUCTION",frozenset({"qualified-target"}),frozenset({"publish"}),"FOUNDER-FINAL-GATE-TEST",True,1,NOW+100)
    with pytest.raises(RuntimeError, match="PRODUCTION_POLICY_NOT_ACTIVE"):
        build_gateway(adapter=ProductionEffectAdapter(),lease=l,approval_verifier=good_approval,cost_preflight=zero_cost)[4].execute_production_effect(req())


def test_github_adapter_commits_only_with_all_external_gates():
    calls=[]; capability="GITHUB_CREATE_OR_UPDATE_FILE"; target="github:jeffersonreisdejesus1-lgtm/reis-os-backend"
    adapter=GitHubProductionAdapter(lambda r: calls.append(r) or "github:commit:test")
    runtime=build_gateway(adapter=adapter,lease=lease(target,capability),policy=active_policy(),capabilities=frozenset({capability}),approval_verifier=good_approval,cost_preflight=zero_cost)[4]
    out=runtime.execute_production_effect(req(target=target,capability=capability))
    assert out.status == "COMMITTED" and out.result_ref == "github:commit:test" and len(calls)==1


def test_render_adapter_commits_only_with_all_external_gates():
    calls=[]; capability="RENDER_TRIGGER_DEPLOY"; target="render:srv-qualified"
    adapter=RenderProductionAdapter(lambda r: calls.append(r) or "render:deploy:test")
    runtime=build_gateway(adapter=adapter,lease=lease(target,capability),policy=active_policy(),capabilities=frozenset({capability}),approval_verifier=good_approval,cost_preflight=zero_cost)[4]
    out=runtime.execute_production_effect(req(target=target,capability=capability))
    assert out.status == "COMMITTED" and out.result_ref == "render:deploy:test" and len(calls)==1


def test_unverified_founder_reference_cannot_self_activate():
    capability="GITHUB_CREATE_BRANCH"; target="github:jeffersonreisdejesus1-lgtm/reis-os-backend"
    with pytest.raises(RuntimeError, match="FOUNDER_APPROVAL_NOT_VERIFIED"):
        build_gateway(adapter=GitHubProductionAdapter(lambda r:"never"),lease=lease(target,capability),policy=active_policy(),capabilities=frozenset({capability}),approval_verifier=lambda _:False,cost_preflight=zero_cost)[4].execute_production_effect(req(target=target,capability=capability))


def test_missing_external_founder_verifier_fails_closed():
    capability="GITHUB_CREATE_BRANCH"; target="github:jeffersonreisdejesus1-lgtm/reis-os-backend"
    with pytest.raises(RuntimeError, match="FOUNDER_APPROVAL_VERIFIER_NOT_BOUND"):
        build_gateway(adapter=GitHubProductionAdapter(lambda r:"never"),lease=lease(target,capability),policy=active_policy(),capabilities=frozenset({capability}),cost_preflight=zero_cost)[4].execute_production_effect(req(target=target,capability=capability))


def test_missing_authoritative_cost_preflight_fails_closed():
    capability="RENDER_TRIGGER_DEPLOY"; target="render:srv-qualified"
    with pytest.raises(RuntimeError, match="COST_PREFLIGHT_NOT_BOUND"):
        build_gateway(adapter=RenderProductionAdapter(lambda r:"never"),lease=lease(target,capability),policy=active_policy(),capabilities=frozenset({capability}),approval_verifier=good_approval)[4].execute_production_effect(req(target=target,capability=capability))


def test_authoritative_cost_preflight_blocks_nonzero_cost():
    calls=[]; capability="RENDER_TRIGGER_DEPLOY"; target="render:srv-qualified"
    adapter=RenderProductionAdapter(lambda r: calls.append(r) or "never")
    costly=lambda _: VerifiedCostDecision(0.01,False,"ACCOUNT-PREFLIGHT")
    with pytest.raises(RuntimeError, match="ZERO_SPEND_POLICY_VIOLATION"):
        build_gateway(adapter=adapter,lease=lease(target,capability),policy=active_policy(),capabilities=frozenset({capability}),approval_verifier=good_approval,cost_preflight=costly)[4].execute_production_effect(req(target=target,capability=capability))
    assert calls == []


def test_authoritative_cost_preflight_blocks_paid_upgrade():
    capability="RENDER_TRIGGER_DEPLOY"; target="render:srv-qualified"
    paid=lambda _: VerifiedCostDecision(0.0,True,"ACCOUNT-PREFLIGHT")
    with pytest.raises(RuntimeError, match="PAID_UPGRADE_FORBIDDEN"):
        build_gateway(adapter=RenderProductionAdapter(lambda r:"never"),lease=lease(target,capability),policy=active_policy(),capabilities=frozenset({capability}),approval_verifier=good_approval,cost_preflight=paid)[4].execute_production_effect(req(target=target,capability=capability))


def test_expired_lease_fails_closed_before_provider():
    capability="GITHUB_CREATE_BRANCH"; target="github:jeffersonreisdejesus1-lgtm/reis-os-backend"
    with pytest.raises(RuntimeError, match="PRODUCTION_LEASE_EXPIRED"):
        build_gateway(adapter=GitHubProductionAdapter(lambda r:"never"),lease=lease(target,capability,expires=NOW-1),policy=active_policy(),capabilities=frozenset({capability}),approval_verifier=good_approval,cost_preflight=zero_cost)[4].execute_production_effect(req(target=target,capability=capability))


def test_lease_effect_limit_is_enforced_across_distinct_requests():
    capability="GITHUB_CREATE_OR_UPDATE_FILE"; target="github:jeffersonreisdejesus1-lgtm/reis-os-backend"
    adapter=GitHubProductionAdapter(lambda r:f"github:{r.request_id}")
    runtime=build_gateway(adapter=adapter,lease=lease(target,capability,max_effects=1),policy=active_policy(),capabilities=frozenset({capability}),approval_verifier=good_approval,cost_preflight=zero_cost)[4]
    runtime.execute_production_effect(req(target=target,capability=capability,request_id="fx:1"))
    with pytest.raises(RuntimeError, match="PRODUCTION_LEASE_EFFECT_LIMIT_EXHAUSTED"):
        runtime.execute_production_effect(req(target=target,capability=capability,request_id="fx:2"))


def test_github_merge_requires_explicit_policy_even_after_final_approval():
    capability="GITHUB_MERGE_PR"; target="github:jeffersonreisdejesus1-lgtm/reis-os-backend"
    with pytest.raises(RuntimeError, match="GITHUB_MERGE_REQUIRES_EXPLICIT_POLICY"):
        build_gateway(adapter=GitHubProductionAdapter(lambda r:"never"),lease=lease(target,capability),policy=active_policy(allow_merge=False),capabilities=frozenset({capability}),approval_verifier=good_approval,cost_preflight=zero_cost)[4].execute_production_effect(req(target=target,capability=capability))


def test_provider_target_prefix_and_capability_are_enforced():
    gh=GitHubProductionAdapter(lambda r:"never")
    with pytest.raises(RuntimeError, match="GITHUB_TARGET_FORBIDDEN"):
        gh.execute(req(target="render:srv-x",capability="GITHUB_CREATE_BRANCH"))
    rd=RenderProductionAdapter(lambda r:"never")
    with pytest.raises(RuntimeError, match="RENDER_CAPABILITY_FORBIDDEN"):
        rd.execute(req(target="render:srv-x",capability="GITHUB_OPEN_PR"))


def test_gateway_missing_fails_closed_without_effect():
    states,_,_,_,runtime=build_gateway(); runtime.production_effect_gateway=None
    assert runtime.execute_production_effect(req()) is Outcome.FAIL_CLOSED
    assert states.get("a").lifecycle is Lifecycle.FAILED_CLOSED
