from copy import deepcopy
from uuid import uuid4
from recursive_runtime.contracts.model import *
from recursive_runtime.repositories.state import Conflict, Stale

class SelfInspectionService:
    def __init__(self, states): self.states=states
    def inspect(self, actor_id):
        a=self.states.get(actor_id)
        return InspectionSnapshot(actor_id=a.actor_id, identity_id=a.identity_id, mission_binding=a.mission_binding, authority_ref=a.authority.authority_ref, scopes=tuple(sorted(a.authority.scopes)), capabilities=tuple(sorted(a.capability.capabilities)), tools=tuple(sorted(a.capability.tools)), state_namespace=a.state_namespace, generation=a.generation, fencing_epoch=a.fencing_epoch, depth=a.depth, trace_id=a.trace_id, span_id=a.span_id, lifecycle=a.lifecycle.value)

class ReflectionEngine:
    PRECEDENCE={PredicateSource.POLICY_DERIVED:4,PredicateSource.STATE_DERIVED:3,PredicateSource.EVIDENCE_DERIVED:2,PredicateSource.MODEL_DERIVED:1}
    def evaluate(self,predicates,*,authorized_child=True,escalation_allowed=True):
        by_name={}
        for p in predicates:
            ex=by_name.get(p.name)
            if ex is None or self.PRECEDENCE[p.source] > self.PRECEDENCE[ex.source]: by_name[p.name]=p
        for n in ("authority_valid","fencing_valid","safety_clear"):
            p=by_name.get(n)
            if p and p.value is Tri.UNKNOWN: return ReflectionDecision(Outcome.FAIL_CLOSED,"R0_UNKNOWN_CRITICAL")
            if p and p.value is Tri.FALSE: return ReflectionDecision(Outcome.FAIL_CLOSED,"R0_CRITICAL_FALSE")
        for n in ("evidence_sufficient","capability_sufficient","budget_available"):
            p=by_name.get(n)
            if p and p.value is Tri.UNKNOWN: return ReflectionDecision(Outcome.HOLD,"UNKNOWN_NONCRITICAL")
        cap=by_name.get("capability_sufficient")
        if cap and cap.value is Tri.FALSE:
            if authorized_child: return ReflectionDecision(Outcome.DELEGATE,"R3","child-task")
            if escalation_allowed: return ReflectionDecision(Outcome.ESCALATE,"R4","bounded-escalation")
            return ReflectionDecision(Outcome.HOLD,"R5")
        ev=by_name.get("evidence_sufficient")
        if ev and ev.value is Tri.FALSE: return ReflectionDecision(Outcome.HOLD,"R9")
        budget=by_name.get("budget_available")
        if budget and budget.value is Tri.FALSE: return ReflectionDecision(Outcome.HOLD,"R2")
        return ReflectionDecision(Outcome.CONTINUE,"R11","AUTHORIZED:local")

class TraceService:
    def __init__(self,receipts): self.receipts=receipts
    def emit(self,kind,actor,detail,parent_span_id=None,receipt_id=None):
        rid=receipt_id or f"{kind}:{uuid4()}"; r=Receipt(rid,kind,actor.actor_id,actor.trace_id,actor.span_id,detail,parent_span_id); self.receipts.put(r); return r
    def reconcile(self,trace_id):
        rs=[r for r in self.receipts.all() if r.trace_id==trace_id]; spans={r.span_id for r in rs}
        for r in rs:
            if r.parent_span_id and r.parent_span_id not in spans: raise Conflict("ORPHAN_TRACE")
        return tuple(sorted((r.kind,r.actor_id,r.span_id,r.detail) for r in rs))

class SpawnTransactionService:
    def __init__(self,states,ledger,trace):
        self.states=states; self.ledger=ledger; self.trace=trace; self._results={}; self._request_fingerprints={}; self._results_lock=__import__("threading").RLock(); self.hook=None
    @staticmethod
    def _fingerprint(req):
        return (req.parent_actor_id,req.child_actor_id,req.child_identity_id,tuple(sorted(req.requested_scopes)),tuple(sorted(req.requested_capabilities)),tuple(sorted(req.requested_tools)),req.child_namespace,req.stop_condition_ref,req.provider_id)
    def spawn(self,req:SpawnRequest):
        fp=self._fingerprint(req)
        with self._results_lock:
            if req.request_id in self._results:
                if self._request_fingerprints[req.request_id] != fp: return SpawnResult("ABORTED",None,"REQUEST_ID_CONFLICT")
                return self._results[req.request_id]
            parent=self.states.get(req.parent_actor_id); self.states.validate_current(parent.actor_id,parent.generation,parent.fencing_epoch)
            def publish(result):
                self._request_fingerprints[req.request_id]=fp; self._results[req.request_id]=result; return result
            if parent.lifecycle in (Lifecycle.CANCELLING,Lifecycle.FENCED,Lifecycle.FAILED_CLOSED): return publish(SpawnResult("ABORTED",None,"PARENT_NOT_ACTIVE"))
            if not req.stop_condition_ref: return publish(SpawnResult("ABORTED",None,"STOP_CONDITION_REQUIRED"))
            if not req.requested_scopes.issubset(parent.authority.scopes): return publish(SpawnResult("ABORTED",None,"SCOPE_ESCAPE"))
            if not req.requested_capabilities.issubset(parent.capability.capabilities): return publish(SpawnResult("ABORTED",None,"CAPABILITY_ESCAPE"))
            if not req.requested_tools.issubset(parent.capability.tools): return publish(SpawnResult("ABORTED",None,"TOOL_ESCAPE"))
            authoritative_provider=self.ledger.provider(parent.budget_ref)
            if req.provider_id != authoritative_provider: return publish(SpawnResult("ABORTED",None,"PROVIDER_BINDING_MISMATCH"))
            try: self.ledger.reserve_spawn(parent.budget_ref)
            except Conflict as e: return publish(SpawnResult("ABORTED",None,str(e)))
            try:
                if self.hook: self.hook("AFTER_RESERVATION",parent,req)
                if self.states.get(parent.actor_id).lifecycle is Lifecycle.CANCELLING: raise Conflict("CANCELLED_DURING_SPAWN")
                child=ActorState(actor_id=req.child_actor_id,identity_id=req.child_identity_id,session_binding=parent.session_binding,mission_binding=parent.mission_binding,state_namespace=req.child_namespace,authority=AuthorityGrant(parent.authority.authority_ref,req.requested_scopes),capability=CapabilityBinding(parent.capability.capability_ref,req.requested_capabilities,req.requested_tools),budget_ref=parent.budget_ref,provider_id=authoritative_provider,trace_id=parent.trace_id,span_id=f"span:{req.child_actor_id}",generation=1,fencing_epoch=1,depth=parent.depth+1,cancellation_policy_ref=parent.cancellation_policy_ref,parent_actor_id=parent.actor_id)
                self.states.add(child,active=True)
                if self.hook: self.hook("AFTER_CHILD_STATE",parent,req)
                if self.states.get(parent.actor_id).lifecycle is Lifecycle.CANCELLING: raise Conflict("CANCELLED_DURING_SPAWN")
                with self.states.lock:
                    p=self.states.mutate(parent.actor_id); p.children=tuple(list(p.children)+[child.actor_id])
                if self.hook: self.hook("BEFORE_COMMIT",parent,req)
                if self.states.get(parent.actor_id).lifecycle is Lifecycle.CANCELLING: raise Conflict("CANCELLED_DURING_SPAWN")
                self.ledger.reconcile_spawn(parent.budget_ref); self.trace.emit("SPAN_OPEN",child,"BOUND",parent_span_id=parent.span_id); self.trace.emit("SPAWN_COMMIT",child,"COMMITTED",parent_span_id=parent.span_id)
                return publish(SpawnResult("COMMITTED",child.actor_id,"OK"))
            except Exception as e:
                with self.states.lock:
                    if req.child_actor_id in self.states._actors:
                        child=self.states._actors.pop(req.child_actor_id); self.states._namespaces.discard(child.state_namespace)
                        if self.states._active_by_identity.get(child.identity_id)==req.child_actor_id: self.states._active_by_identity.pop(child.identity_id,None)
                    p=self.states._actors[parent.actor_id]; p.children=tuple(x for x in p.children if x!=req.child_actor_id)
                self.ledger.release_spawn(parent.budget_ref); result=publish(SpawnResult("ABORTED",None,str(e))); self.trace.emit("SPAWN_ABORT",parent,result.detail); return result

class CancellationService:
    def __init__(self,states,policies,trace,journal=None): self.states=states; self.policies=policies; self.trace=trace; self.journal=journal
    def cancel(self,actor_id,reason="PARENT_CANCELS"):
        actor=self.states.get(actor_id)
        if not actor.cancellation_policy_ref or actor.cancellation_policy_ref not in self.policies:
            with self.states.lock: self.states.mutate(actor_id).lifecycle=Lifecycle.FAILED_CLOSED
            raise Conflict("UNRESOLVED_CANCELLATION_POLICY")
        targets=(actor_id,)+self.states.descendants(actor_id)
        if self.journal is not None:
            for aid in targets:
                a=self.states.get(aid); self.journal.put(JournalRecord(journal_id=f"cancel-intent:{aid}:{a.generation}:{a.fencing_epoch}",kind="CANCELLATION_INTENT",actor_id=aid,trace_id=a.trace_id,generation=a.generation,fencing_epoch=a.fencing_epoch,status="PERSISTED",payload=(("reason",reason),)))
        for aid in targets:
            with self.states.lock: self.states.mutate(aid).lifecycle=Lifecycle.CANCELLING
            self.trace.emit("CANCEL",self.states.get(aid),reason)
        return targets
    def replay(self):
        if self.journal is None: return ()
        replayed=[]
        for row in self.journal.all():
            if row["kind"] != "CANCELLATION_INTENT": continue
            aid=row["actor_id"]
            try:
                with self.states.lock: self.states.mutate(aid).lifecycle=Lifecycle.CANCELLING
                replayed.append(aid)
            except KeyError: continue
        return tuple(dict.fromkeys(replayed))

class RecoveryService:
    def __init__(self,states,checkpoints,trace,journal=None): self.states=states; self.checkpoints=checkpoints; self.trace=trace; self.journal=journal
    def checkpoint(self,actor_id,checkpoint_id):
        cp=Checkpoint(checkpoint_id,self.states.get(actor_id)); self.checkpoints.put(cp); self.trace.emit("CHECKPOINT",cp.actor,checkpoint_id); return cp
    def recover(self,predecessor_id,successor_id,crash_at=None):
        cp=self.checkpoints.latest(predecessor_id); pred=self.states.get(predecessor_id); transition_id=f"recovery:{predecessor_id}->{successor_id}:g{pred.generation+1}"
        if self.journal is not None: self.journal.put(JournalRecord(transition_id,"RECOVERY_TRANSITION",predecessor_id,pred.trace_id,pred.generation,pred.fencing_epoch,"INTENT_PERSISTED",(("successor_id",successor_id),)))
        if crash_at=="AFTER_JOURNAL_BEFORE_COMMIT": raise RuntimeError("CRASH_INJECTED_AFTER_JOURNAL")
        with self.states.lock: self.states.mutate(predecessor_id).lifecycle=Lifecycle.FENCED
        if self.journal is not None: self.journal.put(JournalRecord(transition_id+":fenced","FENCING_COMMIT",predecessor_id,pred.trace_id,pred.generation,pred.fencing_epoch,"FENCED",(("successor_id",successor_id),)))
        succ=deepcopy(cp.actor); succ.actor_id=successor_id; succ.state_namespace=f"{cp.actor.state_namespace}:g{pred.generation+1}"; succ.generation=pred.generation+1; succ.fencing_epoch=pred.fencing_epoch+1; succ.lifecycle=Lifecycle.CANCELLING if cp.actor.lifecycle is Lifecycle.CANCELLING else Lifecycle.ACTIVE
        if successor_id not in self.states._actors: self.states.add(succ,active=True)
        else: self.states.set_active(successor_id)
        self.trace.emit("FENCE",pred,f"successor={successor_id}"); self.trace.emit("RECOVERY",succ,f"from={predecessor_id}",parent_span_id=pred.span_id)
        if self.journal is not None: self.journal.put(JournalRecord(transition_id+":commit","RECOVERY_COMMIT",successor_id,succ.trace_id,succ.generation,succ.fencing_epoch,"COMMITTED",(("predecessor_id",predecessor_id),)))
        if crash_at=="AFTER_COMMIT_BEFORE_ACK": raise RuntimeError("CRASH_INJECTED_AFTER_COMMIT")
        return succ
    def replay(self):
        if self.journal is None: return ()
        rows=self.journal.all(); by_id={r["journal_id"]:r for r in rows}; repaired=[]
        for row in [r for r in rows if r["kind"]=="RECOVERY_TRANSITION"]:
            predecessor=row["actor_id"]; successor=dict(row["payload"]).get("successor_id"); base=row["journal_id"]; commit_key=base+":commit"
            if commit_key in by_id:
                if successor in self.states._actors: self.states.set_active(successor); repaired.append(successor)
                continue
            if predecessor not in self.states._actors: continue
            pred=self.states.get(predecessor)
            try: cp=self.checkpoints.latest(predecessor)
            except Exception: continue
            with self.states.lock: self.states.mutate(predecessor).lifecycle=Lifecycle.FENCED
            succ=deepcopy(cp.actor); succ.actor_id=successor; succ.state_namespace=f"{cp.actor.state_namespace}:g{pred.generation+1}"; succ.generation=pred.generation+1; succ.fencing_epoch=pred.fencing_epoch+1; succ.lifecycle=Lifecycle.CANCELLING if cp.actor.lifecycle is Lifecycle.CANCELLING else Lifecycle.ACTIVE
            if successor not in self.states._actors: self.states.add(succ,active=True)
            else: self.states.set_active(successor)
            self.journal.put(JournalRecord(commit_key,"RECOVERY_COMMIT",successor,succ.trace_id,succ.generation,succ.fencing_epoch,"COMMITTED",(("predecessor_id",predecessor),))); repaired.append(successor)
        return tuple(dict.fromkeys(repaired))

class StopEngine:
    PRECEDENCE=("FENCING_INVALID","AUTHORITY_INVALID","SAFETY_BLOCK","PARENT_CANCELS","EVIDENCE_UNAVAILABLE","BUDGET_EXHAUSTED","DEPTH_LIMIT","NO_VALID_ACTION","GOAL_SATISFIED")
    def choose(self,causes):
        for c in self.PRECEDENCE:
            if c in causes: return c
        return None

class AssuranceGate:
    def evaluate(self,actor:ActorState,*,evidence_present:bool):
        if not evidence_present: return {"assurance_satisfied":False,"promotion_authorized":False,"authority_ref":actor.authority.authority_ref}
        return {"assurance_satisfied":actor.assurance_satisfied,"promotion_authorized":actor.promotion_authorized,"authority_ref":actor.authority.authority_ref}
