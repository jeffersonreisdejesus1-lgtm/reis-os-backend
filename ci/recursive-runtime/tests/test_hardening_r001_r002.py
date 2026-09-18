import threading
import pytest
from recursive_runtime.contracts.model import *
from recursive_runtime.repositories.state import *
from recursive_runtime.services.core import *
from recursive_runtime.runtime.integrated_runtime import IntegratedRuntime

def build(tmp_path):
    states=StateRepository(); receipts=ReceiptRepository(); cps=CheckpointRepository(); ledger=BudgetLedger(); ledger.bind("B1","provider-canonical",20)
    root=ActorState(actor_id="root",identity_id="OCS:ROOT",session_binding="S1",mission_binding="M1",state_namespace="ns:root",authority=AuthorityGrant("AUTH:ROOT",frozenset({"read","delegate","write"})),capability=CapabilityBinding("CAP:ROOT",frozenset({"analyze","delegate"}),frozenset({"tool:a","tool:b"})),budget_ref="B1",provider_id="provider-canonical",trace_id="T1",span_id="span:root",generation=1,fencing_epoch=1,cancellation_policy_ref="C1")
    states.add(root); trace=TraceService(receipts); trace.emit("SPAN_OPEN",root,"ROOT"); journal=DurableJournalRepository(tmp_path/"journal.jsonl"); inspector=SelfInspectionService(states); reflection=ReflectionEngine(); spawn=SpawnTransactionService(states,ledger,trace); cancel=CancellationService(states,{"C1":CancellationPolicy("C1")},trace,journal); recovery=RecoveryService(states,cps,trace,journal); stop=StopEngine(); assurance=AssuranceGate(); runtime=IntegratedRuntime(states,inspector,reflection,spawn,cancel,recovery,trace,stop,assurance)
    return states,receipts,cps,ledger,trace,journal,spawn,cancel,recovery,runtime

def req(child="child",request_id="same"):
    return SpawnRequest(request_id=request_id,parent_actor_id="root",child_actor_id=child,child_identity_id=f"ID:{child}",requested_scopes=frozenset({"read","delegate"}),requested_capabilities=frozenset({"analyze","delegate"}),requested_tools=frozenset({"tool:a"}),child_namespace=f"ns:{child}",stop_condition_ref="STOP:1",provider_id="provider-canonical")

def test_syn_r001_concurrent_idempotency_publication_serialized(tmp_path):
    s,r,c,l,t,j,sp,ca,re,rt=build(tmp_path); results=[]; start=threading.Barrier(3)
    def worker(): start.wait(); results.append(sp.spawn(req()))
    t1=threading.Thread(target=worker); t2=threading.Thread(target=worker); t1.start(); t2.start(); start.wait(); t1.join(); t2.join(); assert [x.status for x in results]==["COMMITTED","COMMITTED"]; assert s.get("root").children==("child",); assert l.snapshot("B1")== (0,1); assert len([x for x in r.all() if x.kind=="SPAWN_COMMIT"])==1

def test_syn_r001_conflicting_request_id_fails_deterministically(tmp_path):
    s,r,c,l,t,j,sp,ca,re,rt=build(tmp_path); assert sp.spawn(req("child","same")).status=="COMMITTED"; out=sp.spawn(req("other","same")); assert out.status=="ABORTED" and out.detail=="REQUEST_ID_CONFLICT"; assert s.get("root").children==("child",); assert l.snapshot("B1")== (0,1)

def test_syn_r002_cancellation_intent_survives_restart(tmp_path):
    s,r,c,l,t,j,sp,ca,re,rt=build(tmp_path); ca.cancel("root","USER_CANCEL"); j2=DurableJournalRepository(tmp_path/"journal.jsonl"); ca2=CancellationService(s,{"C1":CancellationPolicy("C1")},t,j2)
    with s.lock: s.mutate("root").lifecycle=Lifecycle.ACTIVE
    replayed=ca2.replay(); assert "root" in replayed; assert s.get("root").lifecycle is Lifecycle.CANCELLING

def test_syn_r002_fencing_and_recovery_survive_restart(tmp_path):
    s,r,c,l,t,j,sp,ca,re,rt=build(tmp_path); re.checkpoint("root","CP1"); re.recover("root","root:g2"); j2=DurableJournalRepository(tmp_path/"journal.jsonl"); re2=RecoveryService(s,c,t,j2); replayed=re2.replay(); assert "root:g2" in replayed; assert s.get("root").lifecycle is Lifecycle.FENCED; assert s.get("root:g2").generation==2 and s.get("root:g2").fencing_epoch==2

def test_syn_r002_crash_after_journal_before_commit_recovers_deterministically(tmp_path):
    s,r,c,l,t,j,sp,ca,re,rt=build(tmp_path); re.checkpoint("root","CP1")
    with pytest.raises(RuntimeError,match="CRASH_INJECTED_AFTER_JOURNAL"): re.recover("root","root:g2",crash_at="AFTER_JOURNAL_BEFORE_COMMIT")
    re2=RecoveryService(s,c,t,DurableJournalRepository(tmp_path/"journal.jsonl")); replayed=re2.replay(); assert replayed==("root:g2",); assert s.get("root").lifecycle is Lifecycle.FENCED; assert s.get("root:g2").generation==2

def test_syn_r002_crash_after_commit_before_ack_does_not_double_commit(tmp_path):
    s,r,c,l,t,j,sp,ca,re,rt=build(tmp_path); re.checkpoint("root","CP1")
    with pytest.raises(RuntimeError,match="CRASH_INJECTED_AFTER_COMMIT"): re.recover("root","root:g2",crash_at="AFTER_COMMIT_BEFORE_ACK")
    before=[x for x in j.all() if x["kind"]=="RECOVERY_COMMIT"]; j2=DurableJournalRepository(tmp_path/"journal.jsonl"); re2=RecoveryService(s,c,t,j2); replayed=re2.replay(); after=[x for x in j2.all() if x["kind"]=="RECOVERY_COMMIT"]; assert replayed==("root:g2",); assert len(before)==1 and len(after)==1; assert s.get("root:g2").generation==2

def test_recovered_cancelling_successor_cannot_delegate(tmp_path):
    s,r,c,l,t,j,sp,ca,re,rt=build(tmp_path); ca.cancel("root","CANCEL"); re.checkpoint("root","CP1"); succ=re.recover("root","root:g2"); assert succ.lifecycle is Lifecycle.CANCELLING; assert rt.run_once("root:g2",[]) is Outcome.HOLD


def test_spawn_budget_counts_committed_and_reserved_total(tmp_path):
    s,r,c,l,t,j,sp,ca,re,rt=build(tmp_path)
    l._limits["B1"] = ("provider-canonical", 2)
    assert sp.spawn(req("child-1", "req-1")).status == "COMMITTED"
    assert l.snapshot("B1") == (0, 1)
    assert sp.spawn(req("child-2", "req-2")).status == "COMMITTED"
    assert l.snapshot("B1") == (0, 2)
    out = sp.spawn(req("child-3", "req-3"))
    assert out.status == "ABORTED"
    assert l.snapshot("B1") == (0, 2)
