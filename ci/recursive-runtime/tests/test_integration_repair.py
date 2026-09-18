import threading
import pytest
from recursive_runtime.contracts.model import *
from recursive_runtime.repositories.state import *
from recursive_runtime.services.core import *
from recursive_runtime.runtime.integrated_runtime import IntegratedRuntime

def build():
    states=StateRepository(); receipts=ReceiptRepository(); cps=CheckpointRepository(); ledger=BudgetLedger(); ledger.bind("B1","provider-canonical",20)
    root=ActorState(actor_id="root",identity_id="OCS:ROOT",session_binding="S1",mission_binding="M1",state_namespace="ns:root",authority=AuthorityGrant("AUTH:ROOT",frozenset({"read","delegate","write"})),capability=CapabilityBinding("CAP:ROOT",frozenset({"analyze","delegate"}),frozenset({"tool:a","tool:b"})),budget_ref="B1",provider_id="provider-canonical",trace_id="T1",span_id="span:root",generation=1,fencing_epoch=1,cancellation_policy_ref="C1")
    states.add(root); trace=TraceService(receipts); trace.emit("SPAN_OPEN",root,"ROOT"); inspector=SelfInspectionService(states); reflection=ReflectionEngine(); spawn=SpawnTransactionService(states,ledger,trace); cancel=CancellationService(states,{"C1":CancellationPolicy("C1")},trace); recovery=RecoveryService(states,cps,trace); stop=StopEngine(); assurance=AssuranceGate(); runtime=IntegratedRuntime(states,inspector,reflection,spawn,cancel,recovery,trace,stop,assurance)
    return states,receipts,cps,ledger,trace,inspector,reflection,spawn,cancel,recovery,stop,assurance,runtime

def req(parent,child,ns,request_id):
    return SpawnRequest(request_id=request_id,parent_actor_id=parent,child_actor_id=child,child_identity_id=f"ID:{child}",requested_scopes=frozenset({"read","delegate"}),requested_capabilities=frozenset({"analyze","delegate"}),requested_tools=frozenset({"tool:a"}),child_namespace=ns,stop_condition_ref="STOP:1",provider_id="provider-canonical")

def test_r1_canonical_shared_contracts_are_single_import_surface():
    import recursive_runtime.contracts as c; assert c.ActorState is ActorState and c.SpawnRequest is SpawnRequest

def test_r2_runtime_uses_actual_services_not_slice8_doubles():
    s,r,c,l,t,i,f,sp,ca,re,st,a,rt=build(); assert rt.inspector is i and rt.reflection is f and rt.spawn is sp and rt.cancel is ca and rt.recovery is re

def test_r3_provider_resolved_from_authoritative_budget_binding():
    *_,sp,ca,re,st,a,rt=build(); bad=req("root","c1","ns:c1","r1"); bad=SpawnRequest(**{**bad.__dict__,"provider_id":"hardcoded-provider-A"}); out=sp.spawn(bad); assert out.status=="ABORTED" and out.detail=="PROVIDER_BINDING_MISMATCH"

def test_r5_three_level_recursive_trace_and_receipts_reconcile():
    s,r,c,l,t,i,f,sp,ca,re,st,a,rt=build(); assert sp.spawn(req("root","child","ns:child","r1")).status=="COMMITTED"; assert sp.spawn(req("child","grand","ns:grand","r2")).status=="COMMITTED"; rows=t.reconcile("T1"); assert [x[0] for x in rows].count("SPAWN_COMMIT")==2 and any(x[2]=="span:grand" for x in rows)

def test_r6_root_stop_terminates_recursive_chain():
    s,r,c,l,t,i,f,sp,ca,re,st,a,rt=build(); sp.spawn(req("root","child","ns:child","r1")); sp.spawn(req("child","grand","ns:grand","r2")); rt.run_once("root",[],causes=("PARENT_CANCELS",)); assert s.get("root").lifecycle is Lifecycle.CANCELLING and s.get("child").lifecycle is Lifecycle.CANCELLING and s.get("grand").lifecycle is Lifecycle.CANCELLING

def test_r7_concurrent_same_request_commit_is_idempotent_single_child_and_single_budget_actual():
    s,r,c,l,t,i,f,sp,ca,re,st,a,rt=build(); rq=req("root","child","ns:child","same"); results=[]
    def run(): results.append(sp.spawn(rq))
    t1=threading.Thread(target=run); t2=threading.Thread(target=run); t1.start(); t2.start(); t1.join(); t2.join(); assert all(x.status=="COMMITTED" for x in results); assert s.get("root").children==("child",); assert l.snapshot("B1")== (0,1)

@pytest.mark.parametrize("boundary",["AFTER_RESERVATION","AFTER_CHILD_STATE","BEFORE_COMMIT"])
def test_r8_cancel_during_spawn_rolls_back_without_orphan_live_child(boundary):
    s,r,c,l,t,i,f,sp,ca,re,st,a,rt=build()
    def hook(point,parent,rq):
        if point==boundary: ca.cancel("root","RACE_CANCEL")
    sp.hook=hook; out=sp.spawn(req("root","child","ns:child",f"rq:{boundary}")); assert out.status=="ABORTED"; assert "child" not in s._actors; assert s.get("root").children==(); assert l.snapshot("B1")[0]==0

def test_r9_recovery_during_active_cancellation_preserves_intent_and_blocks_delegate():
    s,r,c,l,t,i,f,sp,ca,re,st,a,rt=build(); ca.cancel("root","CANCEL"); re.checkpoint("root","CP1"); succ=re.recover("root","root:g2"); assert succ.lifecycle is Lifecycle.CANCELLING; assert rt.run_once("root:g2",[]) is Outcome.HOLD; assert s.get("root").lifecycle is Lifecycle.FENCED

def test_r10_high_confidence_cannot_satisfy_assurance_or_promotion():
    s,r,c,l,t,i,f,sp,ca,re,st,a,rt=build()
    with s.lock:
        x=s.mutate("root"); x.confidence=0.999999; x.assurance_satisfied=False; x.promotion_authorized=False
    result=a.evaluate(s.get("root"),evidence_present=False); assert result["assurance_satisfied"] is False and result["promotion_authorized"] is False and result["authority_ref"]=="AUTH:ROOT"

def test_p1_child_authority_bounded():
    s,r,c,l,t,i,f,sp,ca,re,st,a,rt=build(); sp.spawn(req("root","c","ns:c","r")); assert s.get("c").authority.scopes <= s.get("root").authority.scopes

def test_p2_scope_escape_rejected():
    s,r,c,l,t,i,f,sp,ca,re,st,a,rt=build(); q=req("root","c","ns:c","r"); q=SpawnRequest(**{**q.__dict__,"requested_scopes":frozenset({"admin"})}); assert sp.spawn(q).status=="ABORTED"

def test_p7_self_inspect_read_only():
    s,r,c,l,t,i,f,sp,ca,re,st,a,rt=build(); before=s.get("root"); i.inspect("root"); assert before==s.get("root")

def test_p9_namespace_isolation():
    s,r,c,l,t,i,f,sp,ca,re,st,a,rt=build(); sp.spawn(req("root","c","ns:c","r1"))
    with pytest.raises(Conflict): s.add(ActorState(actor_id="x",identity_id="ID:X",session_binding="S1",mission_binding="M1",state_namespace="ns:c",authority=AuthorityGrant("A",frozenset()),capability=CapabilityBinding("C",frozenset(),frozenset()),budget_ref="B1",provider_id="provider-canonical",trace_id="T2",span_id="s",generation=1,fencing_epoch=1))

def test_p13_typed_predicate_derivation_precedence():
    e=ReflectionEngine(); ps=[Predicate("capability_sufficient",Tri.FALSE,PredicateSource.MODEL_DERIVED),Predicate("capability_sufficient",Tri.TRUE,PredicateSource.POLICY_DERIVED)]; assert e.evaluate(ps).outcome is Outcome.CONTINUE

def test_p14_unknown_critical_fail_closed():
    assert ReflectionEngine().evaluate([Predicate("authority_valid",Tri.UNKNOWN,PredicateSource.POLICY_DERIVED)]).outcome is Outcome.FAIL_CLOSED

def test_p16_terminal_precedence(): assert StopEngine().choose({"GOAL_SATISFIED","AUTHORITY_INVALID"})=="AUTHORITY_INVALID"

def test_p18_tool_boundary():
    s,r,c,l,t,i,f,sp,ca,re,st,a,rt=build(); q=req("root","c","ns:c","r"); q=SpawnRequest(**{**q.__dict__,"requested_tools":frozenset({"tool:forbidden"})}); assert sp.spawn(q).detail=="TOOL_ESCAPE"

def test_p19_trace_lineage_survives_recovery_generation_change():
    s,r,c,l,t,i,f,sp,ca,re,st,a,rt=build(); re.checkpoint("root","CP"); succ=re.recover("root","root:g2"); assert succ.trace_id=="T1" and succ.generation==2 and succ.fencing_epoch==2 and t.reconcile("T1")

def test_p20_budget_reservation_actual_reconciles():
    s,r,c,l,t,i,f,sp,ca,re,st,a,rt=build(); assert l.snapshot("B1")== (0,0); sp.spawn(req("root","c","ns:c","r")); assert l.snapshot("B1")== (0,1)
