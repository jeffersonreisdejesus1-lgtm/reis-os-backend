import pytest

from autopoiesis_mesh import AutopoiesisEngine, SynapticMesh, SynapticSignal
from ocs_operationalization import OCSRuntimeEnforcer
from recursive_runtime.contracts.model import *
from recursive_runtime.repositories.state import *
from recursive_runtime.services.core import *
from recursive_runtime.runtime.integrated_runtime import IntegratedRuntime


def build_pair(sender_ocs="NOESIS", recipient_ocs="SOFIA"):
    states=StateRepository(); receipts=ReceiptRepository(); cps=CheckpointRepository(); ledger=BudgetLedger(); ledger.bind("B1","provider-canonical",20)
    sender=ActorState(actor_id="a",identity_id=sender_ocs,session_binding="S1",mission_binding="M1",state_namespace="ns:a",authority=AuthorityGrant("AUTH:1",frozenset({"read","delegate","write"})),capability=CapabilityBinding("CAP:1",frozenset({"analyze","delegate"}),frozenset({"tool:a"})),budget_ref="B1",provider_id="provider-canonical",trace_id="T1",span_id="span:a",generation=1,fencing_epoch=1,cancellation_policy_ref="C1")
    recipient=ActorState(actor_id="b",identity_id=recipient_ocs,session_binding="S1",mission_binding="M1",state_namespace="ns:b",authority=AuthorityGrant("AUTH:2",frozenset({"read"})),capability=CapabilityBinding("CAP:2",frozenset({"analyze"}),frozenset({"tool:a"})),budget_ref="B1",provider_id="provider-canonical",trace_id="T1",span_id="span:b",generation=1,fencing_epoch=1,cancellation_policy_ref="C1")
    states.add(sender); states.add(recipient)
    trace=TraceService(receipts); trace.emit("SPAN_OPEN",sender,"ROOT"); trace.emit("SPAN_OPEN",recipient,"PEER")
    enforcer=OCSRuntimeEnforcer(); mesh=SynapticMesh(states,trace,enforcer); auto=AutopoiesisEngine(states,trace,enforcer,mesh)
    runtime=IntegratedRuntime(states,SelfInspectionService(states),ReflectionEngine(),SpawnTransactionService(states,ledger,trace),CancellationService(states,{"C1":CancellationPolicy("C1")},trace),RecoveryService(states,cps,trace),trace,StopEngine(),AssuranceGate(),ocs_enforcer=enforcer,synaptic_mesh=mesh,autopoiesis=auto)
    return states, receipts, mesh, auto, runtime


def signal(**overrides):
    data=dict(signal_id="sig:1",sender_actor_id="a",sender_ocs_id="NOESIS",recipient_actor_id="b",recipient_ocs_id="SOFIA",kind="STATE",payload_ref="state:1",trace_id="T1",authority_ref="AUTH:1",mission_binding="M1",fencing_epoch=1)
    data.update(overrides); return SynapticSignal(**data)


def test_synaptic_signal_routes_between_authorized_ocs():
    _,_,mesh,_,runtime=build_pair()
    out=runtime.route_synaptic_signal(signal())
    assert out.signal_id == "sig:1" and len(mesh.all()) == 1

@pytest.mark.parametrize("field,value,reason",[
    ("kind","PRODUCTION_EFFECT","MESH_KIND_FORBIDDEN"),
    ("sender_ocs_id","UNKNOWN","MESH_IDENTITY_MISMATCH"),
    ("authority_ref","AUTH:OTHER","MESH_AUTHORITY_MISMATCH"),
    ("mission_binding","M2","MESH_MISSION_MISMATCH"),
    ("fencing_epoch",2,"MESH_FENCING_MISMATCH"),
])
def test_mesh_rejects_invalid_signal_boundaries(field,value,reason):
    _,_,_,_,runtime=build_pair()
    with pytest.raises(RuntimeError, match=reason):
        runtime.route_synaptic_signal(signal(**{field:value}))


def test_mesh_idempotent_same_signal():
    _,_,mesh,_,runtime=build_pair(); s=signal()
    assert runtime.route_synaptic_signal(s) == runtime.route_synaptic_signal(s)
    assert len(mesh.all()) == 1


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
