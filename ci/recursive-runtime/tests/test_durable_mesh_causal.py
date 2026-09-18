from autopoiesis_mesh import AutopoiesisEngine, CausalDAG, SynapticMesh, SynapticSignal
from ocs_operationalization import OCSRuntimeEnforcer
from recursive_runtime.contracts.model import ActorState, AuthorityGrant, CapabilityBinding
from recursive_runtime.repositories.state import StateRepository, ReceiptRepository, DurableJournalRepository
from recursive_runtime.services.core import TraceService


def build(tmp_path):
    states=StateRepository(); receipts=ReceiptRepository(); trace=TraceService(receipts); enforcer=OCSRuntimeEnforcer()
    a=ActorState(actor_id="a",identity_id="NOESIS",session_binding="S1",mission_binding="M1",state_namespace="ns:a",authority=AuthorityGrant("AUTH:1",frozenset({"read","write","delegate"})),capability=CapabilityBinding("CAP:1",frozenset({"analyze","delegate"}),frozenset({"tool:a"})),budget_ref="B1",provider_id="provider-canonical",trace_id="T1",span_id="span:a",generation=1,fencing_epoch=1)
    b=ActorState(actor_id="b",identity_id="SOFIA",session_binding="S1",mission_binding="M1",state_namespace="ns:b",authority=AuthorityGrant("AUTH:2",frozenset({"read"})),capability=CapabilityBinding("CAP:2",frozenset({"analyze"}),frozenset({"tool:a"})),budget_ref="B1",provider_id="provider-canonical",trace_id="T1",span_id="span:b",generation=1,fencing_epoch=1)
    states.add(a); states.add(b); trace.emit("SPAN_OPEN",a,"ROOT"); trace.emit("SPAN_OPEN",b,"PEER")
    journal=DurableJournalRepository(tmp_path/"mesh.jsonl")
    mesh=SynapticMesh(states,trace,enforcer,journal=journal)
    auto=AutopoiesisEngine(states,trace,enforcer,mesh,journal=journal)
    return states, receipts, trace, enforcer, journal, mesh, auto


def sig(signal_id="sig:1", parent=None):
    return SynapticSignal(signal_id,"a","NOESIS","b","SOFIA","STATE","state:1","T1","AUTH:1","M1",1,parent)


def test_mesh_signal_survives_process_style_restart(tmp_path):
    states,_,trace,enforcer,journal,mesh,_=build(tmp_path)
    mesh.route(sig())
    mesh2=SynapticMesh(states,trace,enforcer,journal=DurableJournalRepository(journal.path))
    assert [s.signal_id for s in mesh2.all()] == ["sig:1"]
    assert mesh2.route(sig()).signal_id == "sig:1"


def test_repair_proposal_survives_process_style_restart(tmp_path):
    states,_,trace,enforcer,journal,mesh,auto=build(tmp_path)
    repair=auto.inspect_and_propose("a","MISSING_EVIDENCE")
    mesh2=SynapticMesh(states,trace,enforcer,journal=DurableJournalRepository(journal.path))
    auto2=AutopoiesisEngine(states,trace,enforcer,mesh2,journal=DurableJournalRepository(journal.path))
    assert [r.repair_id for r in auto2.repairs()] == [repair.repair_id]
    assert auto2.emit_repair_signal(repair.repair_id,"b").payload_ref == repair.repair_id


def test_causal_dag_parent_contract(tmp_path):
    *_, mesh, _ = build(tmp_path)
    root=sig("sig:root")
    child=sig("sig:child","sig:root")
    mesh.route(root); mesh.route(child)
    assert mesh.causal_dag.contains("sig:root")
    assert mesh.causal_dag.parent_of("sig:child") == "sig:root"


def test_causal_parent_must_exist(tmp_path):
    *_, mesh, _ = build(tmp_path)
    try:
        mesh.route(sig("sig:child","sig:missing"))
        assert False
    except RuntimeError as e:
        assert str(e) == "CAUSAL_PARENT_UNKNOWN"


def test_causal_parent_is_part_of_signal_fingerprint(tmp_path):
    *_, mesh, _ = build(tmp_path)
    mesh.route(sig("sig:root"))
    mesh.route(sig("sig:child","sig:root"))
    try:
        mesh.route(sig("sig:child",None))
        assert False
    except RuntimeError as e:
        assert str(e) == "SIGNAL_ID_CONFLICT"
