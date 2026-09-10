from recursive_runtime.contracts.model import *
from recursive_runtime.repositories.state import Stale

class IntegratedRuntime:
    def __init__(self, states, inspector, reflection, spawn, cancel, recovery, trace, stop_engine, assurance_gate, *, max_cycles=16):
        self.states=states; self.inspector=inspector; self.reflection=reflection
        self.spawn=spawn; self.cancel=cancel; self.recovery=recovery
        self.trace=trace; self.stop_engine=stop_engine; self.assurance_gate=assurance_gate
        self.max_cycles=max_cycles
    def run_once(self, actor_id, predicates, *, causes=()):
        a=self.states.get(actor_id)
        try:
            self.states.validate_current(a.actor_id,a.generation,a.fencing_epoch)
        except Stale:
            with self.states.lock: self.states.mutate(actor_id).lifecycle=Lifecycle.FAILED_CLOSED
            self.trace.emit("FAIL_CLOSED",a,"STALE")
            return Outcome.FAIL_CLOSED
        if a.lifecycle is Lifecycle.CANCELLING:
            self.trace.emit("HOLD",a,"PARENT_CANCELS")
            return Outcome.HOLD
        cause=self.stop_engine.choose(set(causes))
        if cause:
            with self.states.lock: self.states.mutate(actor_id).lifecycle=Lifecycle.STOPPED
            self.trace.emit("TERMINAL",a,cause)
            if cause=="PARENT_CANCELS": self.cancel.cancel(actor_id,cause)
            return Outcome.STOP
        self.inspector.inspect(actor_id)
        d=self.reflection.evaluate(predicates)
        self.trace.emit("REFLECTION",a,f"{d.outcome.value}:{d.rule}")
        return d.outcome
