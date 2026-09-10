from recursive_runtime.contracts.model import *
from recursive_runtime.repositories.state import Stale

class IntegratedRuntime:
    def __init__(self, states, inspector, reflection, spawn, cancel, recovery, trace, stop_engine, assurance_gate, *, max_cycles=16, ocs_enforcer=None):
        self.states=states; self.inspector=inspector; self.reflection=reflection
        self.spawn=spawn; self.cancel=cancel; self.recovery=recovery
        self.trace=trace; self.stop_engine=stop_engine; self.assurance_gate=assurance_gate
        self.max_cycles=max_cycles; self.ocs_enforcer=ocs_enforcer

    def _fail_closed(self, actor_id, actor, detail):
        with self.states.lock:
            self.states.mutate(actor_id).lifecycle=Lifecycle.FAILED_CLOSED
        self.trace.emit("FAIL_CLOSED",actor,detail)
        return Outcome.FAIL_CLOSED

    def _authorize_outcome(self, actor_id, actor, outcome):
        if self.ocs_enforcer is None:
            return outcome
        try:
            ok, detail = self.ocs_enforcer.authorize_outcome(actor, outcome)
        except Exception as e:
            return self._fail_closed(actor_id, actor, f"OCS_BINDING_INVALID:{e}")
        if not ok:
            return self._fail_closed(actor_id, actor, detail)
        return outcome

    def run_once(self, actor_id, predicates, *, causes=()):
        a=self.states.get(actor_id)
        try:
            self.states.validate_current(a.actor_id,a.generation,a.fencing_epoch)
        except Stale:
            return self._fail_closed(actor_id,a,"STALE")
        if self.ocs_enforcer is not None:
            try:
                self.ocs_enforcer.binding_for_actor(a)
            except Exception as e:
                return self._fail_closed(actor_id,a,f"OCS_BINDING_INVALID:{e}")
        if a.lifecycle is Lifecycle.CANCELLING:
            self.trace.emit("HOLD",a,"PARENT_CANCELS")
            return self._authorize_outcome(actor_id,a,Outcome.HOLD)
        cause=self.stop_engine.choose(set(causes))
        if cause:
            with self.states.lock: self.states.mutate(actor_id).lifecycle=Lifecycle.STOPPED
            self.trace.emit("TERMINAL",a,cause)
            if cause=="PARENT_CANCELS": self.cancel.cancel(actor_id,cause)
            return self._authorize_outcome(actor_id,a,Outcome.STOP)
        self.inspector.inspect(actor_id)
        d=self.reflection.evaluate(predicates)
        self.trace.emit("REFLECTION",a,f"{d.outcome.value}:{d.rule}")
        return self._authorize_outcome(actor_id,a,d.outcome)

    def spawn_child(self, request):
        parent=self.states.get(request.parent_actor_id)
        if self.ocs_enforcer is not None:
            try:
                ok, detail=self.ocs_enforcer.authorize_delegate_request(parent,request)
            except Exception as e:
                self._fail_closed(parent.actor_id,parent,f"OCS_BINDING_INVALID:{e}")
                return SpawnResult("ABORTED",None,f"OCS_BINDING_INVALID:{e}")
            if not ok:
                self.trace.emit("SPAWN_ABORT",parent,detail)
                return SpawnResult("ABORTED",None,detail)
        return self.spawn.spawn(request)
