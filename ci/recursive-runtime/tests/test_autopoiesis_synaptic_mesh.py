import threading
import pytest

from autopoiesis_mesh import AutopoiesisEngine, SynapticMesh, SynapticSignal, RepairMission
from ocs_operationalization import OCSRuntimeEnforcer
from recursive_runtime.contracts.model import *
from recursive_runtime.repositories.state import *
from recursive_runtime.services.core import *
from recursive_runtime.runtime.integrated_runtime import IntegratedRuntime


def build_pair(sender_ocs="NOESIS", recipient_ocs="SOFIA", recipient_trace="T1"):
    states=StateRepository(); receipts=ReceiptRepository(); cps=CheckpointRepository(); ledger=BudgetLedger(); ledger.bind("B1","provider-canonical",20)
    sender=ActorState(actor_id="a",identity_id=sender_ocs,session_binding="S1",mission_binding="M1",state_namespace="ns:a",authority=AuthorityGrant("AUTH:1",frozenset({"read","delegate","write"})),capability=CapabilityBinding("CAP:1",frozenset({"analyze","delegate"}),frozenset({"tool:a"})),budget_ref="B1",provider_id="provider-canonical",trace_id="T1",span_id="span:a",generation=1,fencing_epoch=1,cancellation_policy_ref="C1")
    recipient=ActorState(actor_id="b",identity_id=recipient_ocs,session_binding="S1",mission_binding="M1",state_namespace="ns:b",authority=AuthorityGrant("AUTH:2",frozenset({"read"})),capability=CapabilityBinding("CAP:2",frozenset({"analyze"}),frozenset({"tool:a"})),budget_ref="B1",provider_id="provider-canonical",trace_id=recipient_trace,span_id="span:b",generation=1,fencing_epoch=1,cancellation_policy_ref="C1")
    states.add(sender); states.add(recipient)
    trace=TraceService(receipts); trace.emit("SPAN_OPEN",sender,"ROOT"); trace.emit("SPAN_OPEN",recipient,"PEER")
    enforcer=OCSRuntimeEnforcer(); mesh=SynapticMesh(states,trace,enforcer); auto=AutopoiesisEngine(states,trace,enforcer,mesh)
    runtime=IntegratedRuntime(states,SelfInspectionService(states),ReflectionEngine(),SpawnTransactionService(states,ledger,trace),CancellationService(states,{"C1":CancellationPolicy("C1")},trace),RecoveryService(states,cps,trace),trace,StopEngine(),AssuranceGate(),ocs_enforcer=enforcer,synaptic_mesh=mesh,autopoiesis=auto)
    return states, receipts, mesh, auto, runtime


def signal(**overrides):
    data=dict(signal_id="sig:1",sender_actor_id="a",sender_ocs_id="NOESIS",recipient_actor_id="b",recipient_ocs_id="SOFIA",kind="STATE",payload_ref="state:1",trace_id="T1",authority_ref="AUTH:1",mission_binding="M1",fencing_epoch=1)
    data.update(overrides); return SynapticSignal(**data)


def test_synaptic_signal_routes_between_authorized_ocs():
    _,receipts,mesh,_,runtime=build_pair()
    out=runtime.route_synaptic_signal(signal())
    assert out.signal_id == "sig:1" and len(mesh.all()) == 1
    assert any(r.kind == "SYNAPTIC_SIGNAL" and "signal=sig:1" in r.detail for r in receipts.all())


@pytest.mark.parametrize("field,value,reason",[
    ("kind","PRODUCTION_EFFECT","MESH_KIND_FORBIDDEN"),
    ("sender_ocs_id","UNKNOWN","MESH_IDENTITY_MISMATCH"),
    ("authority_ref","AUTH:OTHER","MESH_AUTHORITY_MISMATCH"),
    ("mission_binding","M2","MESH_MISSION_MISMATCH"),
    ("fencing_epoch",2,"MESH_FENCING_MISMATCH"),
    ("trace_id","FORGED","MESH_TRACE_MISMATCH"),
])
def test_mesh_rejects_invalid_signal_boundaries(field,value,reason):
    _,_,_,_,runtime=build_pair()
    with pytest.raises(RuntimeError, match=reason):
        runtime.route_synaptic_signal(signal(**{field:value}))


def test_cross_trace_handoff_forbidden_in_v1():
    _,_,_,_,runtime=build_pair(recipient_trace="T2")
    with pytest.raises(RuntimeError, match="MESH_CROSS_TRACE_FORBIDDEN_V1"):
        runtime.route_synaptic_signal(signal())


def test_mesh_idempotent_same_signal():
    _,receipts,mesh,_,runtime=build_pair(); s=signal()
    assert runtime.route_synaptic_signal(s) == runtime.route_synaptic_signal(s)
    assert len(mesh.all()) == 1
    assert len([r for r in receipts.all() if r.kind == "SYNAPTIC_SIGNAL"]) == 1


def test_same_signal_id_conflicting_payload_fails_closed():
    _,_,mesh,_,runtime=build_pair(); runtime.route_synaptic_signal(signal())
    with pytest.raises(RuntimeError, match="SIGNAL_ID_CONFLICT"):
        runtime.route_synaptic_signal(signal(payload_ref="state:DIFFERENT"))
    assert len(mesh.all()) == 1


def test_concurrent_same_signal_exactly_once_publication():
    _,receipts,mesh,_,runtime=build_pair(); s=signal(); results=[]
    def run(): results.append(runtime.route_synaptic_signal(s))
    threads=[threading.Thread(target=run) for _ in range(8)]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert len(results) == 8 and all(x == s for x in results)
    assert len(mesh.all()) == 1
    assert len([r for r in receipts.all() if r.kind == "SYNAPTIC_SIGNAL"]) == 1


def test_concurrent_conflicting_signal_id_rejects_one_variant():
    _,_,mesh,_,runtime=build_pair(); errors=[]; results=[]
    variants=[signal(payload_ref="state:A"), signal(payload_ref="state:B")]
    def run(s):
        try: results.append(runtime.route_synaptic_signal(s))
        except RuntimeError as e: errors.append(str(e))
    ts=[threading.Thread(target=run,args=(s,)) for s in variants]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert len(mesh.all()) == 1
    assert len(results) == 1 and errors == ["SIGNAL_ID_CONFLICT"]


def test_autopoiesis_proposes_bounded_internal_repair():
    _,_,_,auto,runtime=build_pair()
    out=runtime.run_autopoiesis_cycle("a","MISSING_EVIDENCE","b")
    assert out is Outcome.ESCALATE
    assert len(auto.repairs()) == 1
    assert auto.repairs()[0].action == "OPEN_BOUNDED_INTERNAL_REPAIR_MISSION"


def test_autopoiesis_unrepairable_condition_holds():
    _,_,_,auto,runtime=build_pair()
    assert runtime.run_autopoiesis_cycle("a","AUTHORITY_INVALID","b") is Outcome.HOLD
    assert len(auto.repairs()) == 0


def test_autopoiesis_does_not_create_authority():
    states,_,_,auto,runtime=build_pair()
    before=states.get("a").authority
    runtime.run_autopoiesis_cycle("a","CHILD_STALL","b")
    assert states.get("a").authority == before
    assert auto.repairs()[0].authority_ref == before.authority_ref


def test_unknown_repair_provenance_rejected():
    _,_,_,auto,_=build_pair()
    fake=RepairMission("repair:fake","a","NOESIS","CHILD_STALL","OPEN_BOUNDED_INTERNAL_REPAIR_MISSION","AUTH:1","M1","T1",1,1)
    with pytest.raises(RuntimeError, match="REPAIR_PROVENANCE_UNKNOWN"):
        auto.emit_repair_signal(fake,"b")


def test_conflicting_repair_provenance_rejected():
    _,_,_,auto,_=build_pair(); real=auto.inspect_and_propose("a","CHILD_STALL")
    fake=RepairMission(real.repair_id,real.actor_id,real.ocs_id,real.anomaly_code,"TAMPERED",real.authority_ref,real.mission_binding,real.trace_id,real.generation,real.fencing_epoch)
    with pytest.raises(RuntimeError, match="REPAIR_PROVENANCE_CONFLICT"):
        auto.emit_repair_signal(fake,"b")


def test_stale_repair_provenance_rejected_after_fencing_change():
    states,_,_,auto,_=build_pair(); real=auto.inspect_and_propose("a","CHILD_STALL")
    with states.lock: states.mutate("a").fencing_epoch=2
    with pytest.raises(Exception):
        auto.emit_repair_signal(real.repair_id,"b")


def test_stale_sender_cannot_use_mesh():
    states,_,_,_,runtime=build_pair()
    with states.lock:
        states.mutate("a").fencing_epoch=2
    with pytest.raises(Exception):
        runtime.route_synaptic_signal(signal(fencing_epoch=1))


def test_runtime_without_autopoiesis_fails_closed():
    states,_,_,_,runtime=build_pair(); runtime.autopoiesis=None
    assert runtime.run_autopoiesis_cycle("a","MISSING_EVIDENCE") is Outcome.FAIL_CLOSED
    assert states.get("a").lifecycle is Lifecycle.FAILED_CLOSED


def test_autopoiesis_outcome_uses_same_ocs_authorization_path():
    class RejectEscalate(OCSRuntimeEnforcer):
        def authorize_outcome(self, actor, outcome):
            if outcome is Outcome.ESCALATE:
                return False, "TEST_POLICY_REJECTS_ESCALATE"
            return super().authorize_outcome(actor, outcome)
    states,_,_,_,runtime=build_pair()
    runtime.ocs_enforcer = RejectEscalate()
    assert runtime.run_autopoiesis_cycle("a","MISSING_EVIDENCE","b") is Outcome.FAIL_CLOSED
    assert states.get("a").lifecycle is Lifecycle.FAILED_CLOSED
