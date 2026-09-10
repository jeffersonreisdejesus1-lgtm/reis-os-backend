import pytest
from pathlib import Path

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


def scoped_approval(policy, lease, actor, request):
    return (
        policy.founder_approval_ref == "FOUNDER-FINAL-GATE-TEST"
        and lease.founder_approval_ref == policy.founder_approval_ref
        and actor.identity_id in policy.allowed_ocs_ids
        and request.capability in policy.allowed_capabilities
        and any(request.target.startswith(p) for p in policy.allowed_target_prefixes)
    )


def zero_cost(request):
    return VerifiedCostDecision(request.request_id,request.target,request.capability,0.0,False,"VERIFIED-COST-PREFLIGHT-TEST",NOW+60)


def build_gateway(adapter=None, lease=None, policy=None, capabilities=None, approval_verifier=None, cost_preflight=None, clock=None, journal=None, reconciler=None):
    capabilities = capabilities or frozenset({"analyze","delegate","publish"})
    states=StateRepository(); receipts=ReceiptRepository(); cps=CheckpointRepository(); ledger=BudgetLedger(); ledger.bind("B1","provider-canonical",20)
    actor=ActorState(actor_id="a",identity_id="NOESIS",session_binding="S1",mission_binding="M1",state_namespace="ns:a",authority=AuthorityGrant("AUTH:1",frozenset({"read","write","delegate"})),capability=CapabilityBinding("CAP:1",capabilities,frozenset({"tool:a"})),budget_ref="B1",provider_id="provider-canonical",trace_id="T1",span_id="span:a",generation=1,fencing_epoch=1,cancellation_policy_ref="C1")
    states.add(actor); trace=TraceService(receipts); trace.emit("SPAN_OPEN",actor,"ROOT")
    enforcer=OCSRuntimeEnforcer(); adapter=adapter or SandboxEffectAdapter(); gateway=ProductionEffectGateway(states,trace,enforcer,adapter,lease,policy,approval_verifier,cost_preflight,clock or (lambda: NOW),journal,reconciler)
    runtime=IntegratedRuntime(states,SelfInspectionService(states),ReflectionEngine(),SpawnTransactionService(states,ledger,trace),CancellationService(states,{"C1":CancellationPolicy("C1")},trace),RecoveryService(states,cps,trace),trace,StopEngine(),AssuranceGate(),ocs_enforcer=enforcer,production_effect_gateway=gateway)
    return states,receipts,adapter,gateway,runtime


def req(**overrides):
    data=dict(request_id="fx:1",actor_id="a",target="qualified-target",capability="publish",payload_ref="payload:1",authority_ref="AUTH:1",mission_binding="M1",generation=1,fencing_epoch=1)
    data.update(overrides); return EffectRequest(**data)


def active_policy(*,allow_merge=False):
    return ProductionAuthorizationPolicy(
        policy_id="SYN-R004-GITHUB-RENDER-ZERO-SPEND-V1",
        allowed_ocs_ids=frozenset({"NOESIS","SOFIA","AGORA"}),
        allowed_target_prefixes=frozenset({"github:","render:"}),
        allowed_capabilities=frozenset({"GITHUB_CREATE_BRANCH","GITHUB_CREATE_OR_UPDATE_FILE","GITHUB_OPEN_PR","GITHUB_UPDATE_PR","GITHUB_MERGE_PR","RENDER_TRIGGER_DEPLOY"}),
        founder_approval_ref="FOUNDER-FINAL-GATE-TEST",
        zero_unauthorized_spend=True,
        allow_github_merge=allow_merge,
        active=True,
    )


def lease(target, capability, *, max_effects=1, expires=NOW+3600):
    return ActivationLease("L1","PRODUCTION",frozenset({target}),frozenset({capability}),"FOUNDER-FINAL-GATE-TEST",True,max_effects,expires)


def journal(tmp_path): return DurableJournalRepository(tmp_path/"effects.jsonl")


def production_runtime(tmp_path, adapter, target, capability, *, policy=None, approval=scoped_approval, cost=zero_cost, max_effects=1, reconciler=None):
    return build_gateway(
        adapter=adapter,
        lease=lease(target,capability,max_effects=max_effects),
        policy=policy or active_policy(),
        capabilities=frozenset({capability}),
        approval_verifier=approval,
        cost_preflight=cost,
        journal=journal(tmp_path),
        reconciler=reconciler,
    )


def test_sandbox_effect_is_traceable_and_idempotent():
    _,receipts,adapter,gateway,runtime=build_gateway()
    r=runtime.execute_production_effect(req())
    assert r.status == "SIMULATED"
    assert runtime.execute_production_effect(req()) == r
    assert len(adapter.calls) == 1 and len(gateway.receipts()) == 1
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


def test_production_requires_lease_and_policy(tmp_path):
    with pytest.raises(RuntimeError, match="PRODUCTION_ACTIVATION_REQUIRED"):
        build_gateway(adapter=ProductionEffectAdapter())[4].execute_production_effect(req())
    l=ActivationLease("L1","PRODUCTION",frozenset({"qualified-target"}),frozenset({"publish"}),"FOUNDER-FINAL-GATE-TEST",True,1,NOW+60)
    with pytest.raises(RuntimeError, match="PRODUCTION_POLICY_NOT_ACTIVE"):
        build_gateway(adapter=ProductionEffectAdapter(),lease=l,journal=journal(tmp_path))[4].execute_production_effect(req())


def test_github_adapter_commits_with_all_external_gates(tmp_path):
    calls=[]; capability="GITHUB_CREATE_OR_UPDATE_FILE"; target="github:jeffersonreisdejesus1-lgtm/reis-os-backend"
    adapter=GitHubProductionAdapter(lambda r: calls.append(r) or "github:commit:test")
    _,receipts,_,gateway,runtime=production_runtime(tmp_path,adapter,target,capability)
    out=runtime.execute_production_effect(req(target=target,capability=capability))
    assert out.status == "COMMITTED" and out.result_ref == "github:commit:test"
    assert len(calls)==1 and len(gateway.receipts())==1
    assert any(x.kind == "PRODUCTION_EFFECT_GATEWAY" for x in receipts.all())


def test_render_adapter_commits_with_all_external_gates(tmp_path):
    calls=[]; capability="RENDER_TRIGGER_DEPLOY"; target="render:srv-qualified"
    adapter=RenderProductionAdapter(lambda r: calls.append(r) or "render:deploy:test")
    out=production_runtime(tmp_path,adapter,target,capability)[4].execute_production_effect(req(target=target,capability=capability))
    assert out.status == "COMMITTED" and out.result_ref == "render:deploy:test" and len(calls)==1


def test_policy_object_cannot_expand_scope_behind_valid_founder_ref(tmp_path):
    capability="GITHUB_MERGE_PR"; target="github:jeffersonreisdejesus1-lgtm/reis-os-backend"
    expanded=active_policy(allow_merge=True)
    verifier=lambda policy,lease,actor,request: False
    with pytest.raises(RuntimeError, match="FOUNDER_APPROVAL_NOT_VERIFIED"):
        production_runtime(tmp_path,GitHubProductionAdapter(lambda r:"never"),target,capability,policy=expanded,approval=verifier)[4].execute_production_effect(req(target=target,capability=capability))


def test_missing_founder_verifier_fails_closed(tmp_path):
    capability="GITHUB_CREATE_BRANCH"; target="github:jeffersonreisdejesus1-lgtm/reis-os-backend"
    with pytest.raises(RuntimeError, match="FOUNDER_APPROVAL_VERIFIER_NOT_BOUND"):
        production_runtime(tmp_path,GitHubProductionAdapter(lambda r:"never"),target,capability,approval=None)[4].execute_production_effect(req(target=target,capability=capability))


def test_cost_preflight_is_scope_bound_and_fresh(tmp_path):
    capability="RENDER_TRIGGER_DEPLOY"; target="render:srv-qualified"; request=req(target=target,capability=capability)
    mismatched=lambda r: VerifiedCostDecision("other",r.target,r.capability,0.0,False,"ACCOUNT",NOW+60)
    with pytest.raises(RuntimeError, match="COST_PREFLIGHT_SCOPE_MISMATCH"):
        production_runtime(tmp_path,RenderProductionAdapter(lambda r:"never"),target,capability,cost=mismatched)[4].execute_production_effect(request)
    expired=lambda r: VerifiedCostDecision(r.request_id,r.target,r.capability,0.0,False,"ACCOUNT",NOW-1)
    with pytest.raises(RuntimeError, match="COST_PREFLIGHT_EXPIRED"):
        production_runtime(tmp_path,RenderProductionAdapter(lambda r:"never"),target,capability,cost=expired)[4].execute_production_effect(request)


def test_zero_spend_preflight_blocks_cost_and_paid_upgrade(tmp_path):
    capability="RENDER_TRIGGER_DEPLOY"; target="render:srv-qualified"; request=req(target=target,capability=capability)
    costly=lambda r: VerifiedCostDecision(r.request_id,r.target,r.capability,0.01,False,"ACCOUNT",NOW+60)
    with pytest.raises(RuntimeError, match="ZERO_SPEND_POLICY_VIOLATION"):
        production_runtime(tmp_path,RenderProductionAdapter(lambda r:"never"),target,capability,cost=costly)[4].execute_production_effect(request)
    paid=lambda r: VerifiedCostDecision(r.request_id,r.target,r.capability,0.0,True,"ACCOUNT",NOW+60)
    with pytest.raises(RuntimeError, match="PAID_UPGRADE_FORBIDDEN"):
        production_runtime(tmp_path,RenderProductionAdapter(lambda r:"never"),target,capability,cost=paid)[4].execute_production_effect(request)


def test_expired_lease_and_effect_limit_are_enforced(tmp_path):
    capability="GITHUB_CREATE_BRANCH"; target="github:jeffersonreisdejesus1-lgtm/reis-os-backend"; request=req(target=target,capability=capability)
    expired=lease(target,capability,expires=NOW-1)
    with pytest.raises(RuntimeError, match="PRODUCTION_LEASE_EXPIRED"):
        build_gateway(adapter=GitHubProductionAdapter(lambda r:"never"),lease=expired,policy=active_policy(),capabilities=frozenset({capability}),approval_verifier=scoped_approval,cost_preflight=zero_cost,journal=journal(tmp_path))[4].execute_production_effect(request)
    adapter=GitHubProductionAdapter(lambda r:f"github:{r.request_id}")
    runtime=production_runtime(tmp_path,adapter,target,capability,max_effects=1)[4]
    runtime.execute_production_effect(req(target=target,capability=capability,request_id="fx:1"))
    with pytest.raises(RuntimeError, match="PRODUCTION_LEASE_EFFECT_LIMIT_EXHAUSTED"):
        runtime.execute_production_effect(req(target=target,capability=capability,request_id="fx:2"))


def test_github_merge_requires_explicit_policy(tmp_path):
    capability="GITHUB_MERGE_PR"; target="github:jeffersonreisdejesus1-lgtm/reis-os-backend"
    with pytest.raises(RuntimeError, match="GITHUB_MERGE_REQUIRES_EXPLICIT_POLICY"):
        production_runtime(tmp_path,GitHubProductionAdapter(lambda r:"never"),target,capability,policy=active_policy(allow_merge=False))[4].execute_production_effect(req(target=target,capability=capability))


def test_production_requires_durable_journal():
    capability="RENDER_TRIGGER_DEPLOY"; target="render:srv-qualified"
    with pytest.raises(RuntimeError, match="EFFECT_JOURNAL_NOT_BOUND"):
        build_gateway(adapter=RenderProductionAdapter(lambda r:"never"),lease=lease(target,capability),policy=active_policy(),capabilities=frozenset({capability}),approval_verifier=scoped_approval,cost_preflight=zero_cost)[4].execute_production_effect(req(target=target,capability=capability))


def test_crash_after_external_commit_does_not_blindly_retry(tmp_path):
    capability="RENDER_TRIGGER_DEPLOY"; target="render:srv-qualified"; request=req(target=target,capability=capability)
    j=journal(tmp_path); calls=[]
    def uncertain(r): calls.append(r); raise RuntimeError("CONNECTION_LOST_AFTER_PROVIDER_COMMIT")
    runtime=build_gateway(adapter=RenderProductionAdapter(uncertain),lease=lease(target,capability),policy=active_policy(),capabilities=frozenset({capability}),approval_verifier=scoped_approval,cost_preflight=zero_cost,journal=j)[4]
    with pytest.raises(RuntimeError, match="CONNECTION_LOST_AFTER_PROVIDER_COMMIT"):
        runtime.execute_production_effect(request)
    assert len(calls)==1
    runtime2=build_gateway(adapter=RenderProductionAdapter(lambda r: (_ for _ in ()).throw(AssertionError("must not re-execute"))),lease=lease(target,capability),policy=active_policy(),capabilities=frozenset({capability}),approval_verifier=scoped_approval,cost_preflight=zero_cost,journal=j)[4]
    with pytest.raises(RuntimeError, match="EFFECT_OUTCOME_UNKNOWN_HOLD"):
        runtime2.execute_production_effect(request)


def test_provider_reconciliation_can_close_uncertain_effect_without_reexecution(tmp_path):
    capability="RENDER_TRIGGER_DEPLOY"; target="render:srv-qualified"; request=req(target=target,capability=capability)
    j=journal(tmp_path)
    failing=RenderProductionAdapter(lambda r: (_ for _ in ()).throw(RuntimeError("UNKNOWN_AFTER_COMMIT")))
    runtime=build_gateway(adapter=failing,lease=lease(target,capability),policy=active_policy(),capabilities=frozenset({capability}),approval_verifier=scoped_approval,cost_preflight=zero_cost,journal=j)[4]
    with pytest.raises(RuntimeError): runtime.execute_production_effect(request)
    adapter2=RenderProductionAdapter(lambda r: (_ for _ in ()).throw(AssertionError("must not execute twice")))
    runtime2=build_gateway(adapter=adapter2,lease=lease(target,capability),policy=active_policy(),capabilities=frozenset({capability}),approval_verifier=scoped_approval,cost_preflight=zero_cost,journal=j,reconciler=lambda r:"render:deploy:reconciled")[4]
    out=runtime2.execute_production_effect(request)
    assert out.status=="COMMITTED" and out.result_ref=="render:deploy:reconciled"


def test_durable_commit_replays_idempotently_after_restart(tmp_path):
    capability="GITHUB_CREATE_OR_UPDATE_FILE"; target="github:jeffersonreisdejesus1-lgtm/reis-os-backend"; request=req(target=target,capability=capability)
    j=journal(tmp_path); calls=[]
    runtime=build_gateway(adapter=GitHubProductionAdapter(lambda r: calls.append(r) or "github:commit:1"),lease=lease(target,capability),policy=active_policy(),capabilities=frozenset({capability}),approval_verifier=scoped_approval,cost_preflight=zero_cost,journal=j)[4]
    first=runtime.execute_production_effect(request); assert len(calls)==1
    runtime2=build_gateway(adapter=GitHubProductionAdapter(lambda r: (_ for _ in ()).throw(AssertionError("must not repeat"))),lease=lease(target,capability),policy=active_policy(),capabilities=frozenset({capability}),approval_verifier=scoped_approval,cost_preflight=zero_cost,journal=j)[4]
    second=runtime2.execute_production_effect(request)
    assert second==first


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
