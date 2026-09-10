import pytest

from production_effects import (
    ActivationLease,
    EffectRequest,
    ProductionEffectAdapter,
    ProductionEffectGateway,
    SandboxEffectAdapter,
)
from ocs_operationalization import OCSRuntimeEnforcer
from recursive_runtime.contracts.model import *
from recursive_runtime.repositories.state import *
from recursive_runtime.services.core import *
from recursive_runtime.runtime.integrated_runtime import IntegratedRuntime


def build_gateway(adapter=None, lease=None):
    states=StateRepository(); receipts=ReceiptRepository(); cps=CheckpointRepository(); ledger=BudgetLedger(); ledger.bind("B1","provider-canonical",20)
    actor=ActorState(actor_id="a",identity_id="NOESIS",session_binding="S1",mission_binding="M1",state_namespace="ns:a",authority=AuthorityGrant("AUTH:1",frozenset({"read","write","delegate"})),capability=CapabilityBinding("CAP:1",frozenset({"analyze","delegate","publish"}),frozenset({"tool:a"})),budget_ref="B1",provider_id="provider-canonical",trace_id="T1",span_id="span:a",generation=1,fencing_epoch=1,cancellation_policy_ref="C1")
    states.add(actor); trace=TraceService(receipts); trace.emit("SPAN_OPEN",actor,"ROOT")
    enforcer=OCSRuntimeEnforcer(); adapter=adapter or SandboxEffectAdapter(); gateway=ProductionEffectGateway(states,trace,enforcer,adapter,lease)
    runtime=IntegratedRuntime(states,SelfInspectionService(states),ReflectionEngine(),SpawnTransactionService(states,ledger,trace),CancellationService(states,{"C1":CancellationPolicy("C1")},trace),RecoveryService(states,cps,trace),trace,StopEngine(),AssuranceGate(),ocs_enforcer=enforcer,production_effect_gateway=gateway)
    return states,receipts,adapter,gateway,runtime


def req(**overrides):
    data=dict(request_id="fx:1",actor_id="a",target="qualified-target",capability="publish",payload_ref="payload:1",authority_ref="AUTH:1",mission_binding="M1",generation=1,fencing_epoch=1)
    data.update(overrides); return EffectRequest(**data)


def test_sandbox_effect_is_traceable_and_idempotent():
    _,receipts,adapter,gateway,runtime=build_gateway()
    r=runtime.execute_production_effect(req())
    assert r.status == "SIMULATED"
    assert runtime.execute_production_effect(req()) == r
    assert len(adapter.calls) == 1
    assert len(gateway.receipts()) == 1
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


def test_real_production_adapter_requires_activation_lease():
    states,_,_,_,runtime=build_gateway(adapter=ProductionEffectAdapter())
    with pytest.raises(RuntimeError, match="PRODUCTION_ACTIVATION_REQUIRED"):
        runtime.execute_production_effect(req())
    assert states.get("a").lifecycle is Lifecycle.FAILED_CLOSED


def test_real_production_adapter_still_blocked_by_canonical_ocs_policy_even_with_lease():
    lease=ActivationLease("L1","PRODUCTION",frozenset({"qualified-target"}),frozenset({"publish"}),"FOUNDER-FINAL-GATE-PENDING",True)
    states,_,_,_,runtime=build_gateway(adapter=ProductionEffectAdapter(),lease=lease)
    with pytest.raises(RuntimeError, match="PRODUCTION_EFFECT"):
        runtime.execute_production_effect(req())
    assert states.get("a").lifecycle is Lifecycle.FAILED_CLOSED


def test_lease_target_allowlist_precedes_adapter_call():
    lease=ActivationLease("L1","PRODUCTION",frozenset({"other-target"}),frozenset({"publish"}),"FOUNDER-FINAL-GATE-PENDING",True)
    with pytest.raises(RuntimeError, match="PRODUCTION_TARGET_NOT_ALLOWED"):
        build_gateway(adapter=ProductionEffectAdapter(),lease=lease)[4].execute_production_effect(req())


def test_lease_capability_allowlist_precedes_adapter_call():
    lease=ActivationLease("L1","PRODUCTION",frozenset({"qualified-target"}),frozenset({"other"}),"FOUNDER-FINAL-GATE-PENDING",True)
    with pytest.raises(RuntimeError, match="PRODUCTION_CAPABILITY_NOT_ALLOWED"):
        build_gateway(adapter=ProductionEffectAdapter(),lease=lease)[4].execute_production_effect(req())


def test_founder_approval_reference_required():
    lease=ActivationLease("L1","PRODUCTION",frozenset({"qualified-target"}),frozenset({"publish"}),"",True)
    with pytest.raises(RuntimeError, match="FOUNDER_APPROVAL_REF_REQUIRED"):
        build_gateway(adapter=ProductionEffectAdapter(),lease=lease)[4].execute_production_effect(req())


def test_gateway_missing_fails_closed_without_effect():
    states,_,_,_,runtime=build_gateway(); runtime.production_effect_gateway=None
    assert runtime.execute_production_effect(req()) is Outcome.FAIL_CLOSED
    assert states.get("a").lifecycle is Lifecycle.FAILED_CLOSED
