import pytest

from ocs_canonical_policy import CANONICAL_OCS_POLICY, GLOBAL_FORBIDDEN, POLICY_ID, POLICY_SOURCE_REF
from ocs_operationalization import (
    OCS_RUNTIME_BINDINGS,
    OCSRuntimeEnforcer,
    assert_operationalization_invariants,
    get_binding,
)
from recursive_runtime.contracts.model import *
from recursive_runtime.repositories.state import *
from recursive_runtime.services.core import *
from recursive_runtime.runtime.integrated_runtime import IntegratedRuntime


def build_bound(ocs_id):
    states=StateRepository(); receipts=ReceiptRepository(); cps=CheckpointRepository(); ledger=BudgetLedger(); ledger.bind("B1","provider-canonical",20)
    root=ActorState(
        actor_id="root", identity_id=ocs_id, session_binding="S1", mission_binding="M1", state_namespace=f"ns:{ocs_id.lower()}",
        authority=AuthorityGrant("AUTH:BOUND",frozenset({"read","delegate","write"})),
        capability=CapabilityBinding("CAP:BOUND",frozenset({"analyze","delegate"}),frozenset({"tool:a","tool:b"})),
        budget_ref="B1", provider_id="provider-canonical", trace_id="T1", span_id="span:root", generation=1, fencing_epoch=1,
        cancellation_policy_ref="C1"
    )
    states.add(root)
    trace=TraceService(receipts); trace.emit("SPAN_OPEN",root,"ROOT")
    inspector=SelfInspectionService(states); reflection=ReflectionEngine(); spawn=SpawnTransactionService(states,ledger,trace)
    cancel=CancellationService(states,{"C1":CancellationPolicy("C1")},trace); recovery=RecoveryService(states,cps,trace)
    runtime=IntegratedRuntime(states,inspector,reflection,spawn,cancel,recovery,trace,StopEngine(),AssuranceGate(),ocs_enforcer=OCSRuntimeEnforcer())
    return states, ledger, trace, runtime


def delegate_predicates():
    return [Predicate("capability_sufficient",Tri.FALSE,PredicateSource.POLICY_DERIVED)]


def request(parent="root", scopes=frozenset({"read"}), caps=frozenset({"analyze"}), tools=frozenset({"tool:a"}), provider="provider-canonical", stop="STOP:1"):
    return SpawnRequest(
        request_id="rq:1", parent_actor_id=parent, child_actor_id="child", child_identity_id="SOFIA",
        requested_scopes=scopes, requested_capabilities=caps, requested_tools=tools,
        child_namespace="ns:child", stop_condition_ref=stop, provider_id=provider
    )


def test_all_ten_ocs_are_bound():
    assert set(OCS_RUNTIME_BINDINGS) == set(CANONICAL_OCS_POLICY) == {
        "NOESIS", "DEDALA", "SYNESIS", "SOFIA", "IRIS",
        "LYRA", "AGORA", "AURI", "METIS", "SYNERGEIA",
    }


def test_global_invariants_hold():
    assert_operationalization_invariants()


@pytest.mark.parametrize("ocs_id", OCS_RUNTIME_BINDINGS.keys())
def test_binding_matches_canonical_policy_source(ocs_id):
    binding=get_binding(ocs_id); policy=CANONICAL_OCS_POLICY[ocs_id]
    assert binding.role == policy.role
    assert binding.canonical_policy_id == POLICY_ID
    assert binding.canonical_source_ref == POLICY_SOURCE_REF
    assert ("DELEGATE" in binding.allowed_runtime_capabilities) is policy.may_delegate


@pytest.mark.parametrize("ocs_id", OCS_RUNTIME_BINDINGS.keys())
def test_no_ocs_gets_production_or_authority_expansion(ocs_id):
    binding = get_binding(ocs_id)
    assert binding.production_effects is False
    assert binding.authority_expansion is False
    assert GLOBAL_FORBIDDEN <= binding.forbidden_runtime_capabilities


def test_unknown_ocs_registry_fails_closed():
    with pytest.raises(KeyError, match="UNKNOWN_OCS"):
        get_binding("UNKNOWN")


def test_unknown_ocs_integrated_runtime_fails_closed():
    states,_,_,runtime=build_bound("UNKNOWN")
    assert runtime.run_once("root",[]) is Outcome.FAIL_CLOSED
    assert states.get("root").lifecycle is Lifecycle.FAILED_CLOSED


@pytest.mark.parametrize("ocs_id", OCS_RUNTIME_BINDINGS.keys())
@pytest.mark.parametrize("effect", ["PRODUCTION_EFFECT","AUTHORITY_EXPANSION","SELF_PROMOTE","FOUNDER_GATE_BYPASS","ASSURANCE_BYPASS","MULTI_PROVIDER_EXPANSION"])
def test_forbidden_effects_fail_closed_through_integrated_runtime(ocs_id,effect):
    states,_,_,runtime=build_bound(ocs_id)
    assert runtime.attempt_effect("root",effect) is False
    assert states.get("root").lifecycle is Lifecycle.FAILED_CLOSED


@pytest.mark.parametrize("ocs_id", [k for k,v in CANONICAL_OCS_POLICY.items() if v.may_delegate])
def test_authorized_ocs_can_reach_delegate_outcome(ocs_id):
    states,_,_,runtime=build_bound(ocs_id)
    assert runtime.run_once("root",delegate_predicates()) is Outcome.DELEGATE
    assert states.get("root").lifecycle is Lifecycle.ACTIVE


def test_synesis_cannot_delegate_through_integrated_runtime():
    states,_,_,runtime=build_bound("SYNESIS")
    assert runtime.run_once("root",delegate_predicates()) is Outcome.FAIL_CLOSED
    assert states.get("root").lifecycle is Lifecycle.FAILED_CLOSED


@pytest.mark.parametrize("ocs_id", [k for k,v in CANONICAL_OCS_POLICY.items() if v.may_delegate])
def test_authorized_ocs_spawn_path_enforces_parent_bounds(ocs_id):
    states,ledger,_,runtime=build_bound(ocs_id)
    out=runtime.spawn_child(request())
    assert out.status == "COMMITTED"
    child=states.get("child")
    parent=states.get("root")
    assert child.authority.scopes <= parent.authority.scopes
    assert child.capability.capabilities <= parent.capability.capabilities
    assert child.capability.tools <= parent.capability.tools
    assert child.provider_id == parent.provider_id
    assert child.depth == parent.depth + 1
    assert ledger.snapshot("B1") == (0,1)


def test_synesis_spawn_path_rejects_delegation():
    states,_,_,runtime=build_bound("SYNESIS")
    out=runtime.spawn_child(request())
    assert out.status == "ABORTED"
    assert out.detail == "OCS_CAPABILITY_UNBOUND:DELEGATE"
    assert "child" not in states._actors


@pytest.mark.parametrize("mutation,detail", [
    ({"scopes":frozenset({"admin"})},"OCS_SCOPE_ESCAPE"),
    ({"caps":frozenset({"root-admin"})},"OCS_CAPABILITY_ESCAPE"),
    ({"tools":frozenset({"tool:forbidden"})},"OCS_TOOL_ESCAPE"),
    ({"provider":"provider-other"},"OCS_PROVIDER_MISMATCH"),
    ({"stop":""},"OCS_STOP_CONDITION_REQUIRED"),
])
def test_delegation_request_enforces_scope_capability_tool_provider_and_stop(mutation,detail):
    states,ledger,_,runtime=build_bound("NOESIS")
    out=runtime.spawn_child(request(**mutation))
    assert out.status == "ABORTED"
    assert out.detail == detail
    assert "child" not in states._actors
    assert ledger.snapshot("B1") == (0,0)


def test_continue_outcome_is_allowed_for_all_ocs():
    for ocs_id in OCS_RUNTIME_BINDINGS:
        states,_,_,runtime=build_bound(ocs_id)
        assert runtime.run_once("root",[]) is Outcome.CONTINUE
        assert states.get("root").lifecycle is Lifecycle.ACTIVE
