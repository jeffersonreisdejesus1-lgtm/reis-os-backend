from dataclasses import replace

import pytest

from app.universal_kernel.contracts import (
    ActionProposal, AuthorityLease, CapabilityDescriptor, HandoffPackage,
    ReversibilityClass, SideEffectClass, GovernanceResult,
)
from app.universal_kernel.control import ConstitutionLoader, CapabilityRegistry, EvidenceEngine, AuthorityLeaseManager, GovernanceEngine
from app.universal_kernel.kernel import UniversalKernel
from app.universal_kernel.material import InMemoryMutationAdapter, ThinEffector, ToolBroker
from app.universal_kernel.runtime_ports import CognitiveRuntimePort, HandoffRouter, LPEPort, RecoveryManager
from app.universal_kernel.state_trace import StateCore, TraceCore


def proposal():
    return ActionProposal("p1", "actor", "SOFIA", "csp", "goal", "write", "obj", ("write",), "cap", ("e1",), "value", SideEffectClass.PERSISTENT_MUTATION, ReversibilityClass.STATE_ONLY, "ctx")


def setup_kernel(expires_at=100, revoked=False):
    caps = CapabilityRegistry()
    caps.register(CapabilityDescriptor("cap", "memory", SideEffectClass.PERSISTENT_MUTATION, ("write",), ReversibilityClass.STATE_ONLY, True, True, "none"))
    leases = AuthorityLeaseManager()
    lease = AuthorityLease("l1", "actor", "SOFIA", "write", "obj", ("write",), "ctx", 0, expires_at)
    leases.issue(lease)
    if revoked:
        leases.revoke("l1")
    broker = ToolBroker()
    adapter = InMemoryMutationAdapter()
    broker.register(adapter)
    kernel = UniversalKernel(caps, EvidenceEngine(), leases, GovernanceEngine(), broker, ThinEffector(), StateCore(), TraceCore())
    constitution = ConstitutionLoader().load(constitution_ref="c", policy_version="v1", prohibitions=("self_assurance",), authority_ceiling=("write",))
    return kernel, adapter, constitution


def test_deny_causes_zero_mutation():
    kernel, adapter, constitution = setup_kernel()
    p = replace(proposal(), action_type="self_assurance")
    decision, result = kernel.execute(proposal=p, constitution=constitution, lease_ref="l1", assessment_id="a", adapter_id="memory", tenant="t", recovery_ref="r", idempotency_key="i", now=1)
    assert decision.result is GovernanceResult.DENY
    assert result.mutation_count == 0
    assert adapter.mutations == 0


def test_expired_lease_causes_zero_mutation():
    kernel, adapter, constitution = setup_kernel(expires_at=1)
    decision, result = kernel.execute(proposal=proposal(), constitution=constitution, lease_ref="l1", assessment_id="a", adapter_id="memory", tenant="t", recovery_ref="r", idempotency_key="i", now=2)
    assert decision.result is GovernanceResult.DENY
    assert result.mutation_count == adapter.mutations == 0


def test_revoked_lease_causes_zero_mutation():
    kernel, adapter, constitution = setup_kernel(revoked=True)
    decision, result = kernel.execute(proposal=proposal(), constitution=constitution, lease_ref="l1", assessment_id="a", adapter_id="memory", tenant="t", recovery_ref="r", idempotency_key="i", now=1)
    assert decision.result is GovernanceResult.DENY
    assert result.mutation_count == adapter.mutations == 0


def test_handoff_transfers_no_authority():
    router = HandoffRouter()
    package = HandoffPackage("h", "SOFIA", "AGORA", "obj", (), (), (), ("verify",), (), "receipt", False)
    assert router.route(package).authority_transfer is False
    with pytest.raises(ValueError):
        router.route(replace(package, authority_transfer=True))


def test_state_write_has_version_and_predecessor_and_recovery_verified():
    state, trace = StateCore(), TraceCore()
    trace.append(event_id="e1", trace_id="t", event_type="state_write", producer_kind="state", ocs_id="SOFIA")
    r1 = state.commit_write(namespace="state://SOFIA/v1/work", state={"x": 1}, predecessor_version=None, authority_ref="a", action_id="x", trace_ref="t", committed_at=1)
    r2 = state.commit_write(namespace="state://SOFIA/v1/work", state={"x": 2}, predecessor_version=1, authority_ref="a", action_id="y", trace_ref="t", committed_at=2)
    assert r1.version == 1 and r1.predecessor_version is None
    assert r2.version == 2 and r2.predecessor_version == 1
    state.checkpoint("state://SOFIA/v1/work", "cp2")
    state.commit_write(namespace="state://SOFIA/v1/work", state={"x": 3}, predecessor_version=2, authority_ref="a", action_id="z", trace_ref="t", committed_at=3)
    assert RecoveryManager(state, trace).recover_verified("cp2") == {"x": 2}


def test_trace_break_returns_not_proven():
    trace = TraceCore()
    trace.append(event_id="e1", trace_id="t", event_type="decision", producer_kind="gov", ocs_id="SOFIA")
    trace.events[0] = replace(trace.events[0], event_hash="broken")
    assert trace.causal_status() == "NOT_PROVEN"


def test_high_risk_evidence_failure_blocks_effect():
    p = proposal()
    constitution = ConstitutionLoader().load(constitution_ref="c", policy_version="v1", prohibitions=(), authority_ceiling=("write",))
    cap = CapabilityDescriptor("cap", "memory", SideEffectClass.PERSISTENT_MUTATION, ("write",), ReversibilityClass.STATE_ONLY, True, True, "none")
    lease = AuthorityLease("l", "actor", "SOFIA", "write", "obj", ("write",), "ctx", 0, 100)
    bad = EvidenceEngine().assess("bad", provenance=False)
    decision = GovernanceEngine().decide(decision_id="d", proposal=p, constitution=constitution, capability=cap, evidence=bad, lease=lease, now=1, high_risk=True)
    broker, adapter = ToolBroker(), InMemoryMutationAdapter()
    broker.register(adapter)
    result = broker.resolve_and_execute(decision=decision, envelope=None, adapter_id="memory", effector=ThinEffector(), now=1)
    assert decision.result is GovernanceResult.HOLD
    assert result.mutation_count == adapter.mutations == 0


def test_self_assurance_is_denied():
    kernel, adapter, constitution = setup_kernel()
    p = replace(proposal(), action_type="self_assurance")
    decision, _ = kernel.execute(proposal=p, constitution=constitution, lease_ref="l1", assessment_id="a", adapter_id="memory", tenant="t", recovery_ref="r", idempotency_key="i", now=1)
    assert decision.result is GovernanceResult.DENY
    assert adapter.mutations == 0


def test_lateral_effect_route_exists_false():
    cognition = CognitiveRuntimePort()
    caps = CapabilityRegistry()
    assert not hasattr(cognition, "effector") and not hasattr(cognition, "broker")
    assert not hasattr(caps, "effector")


def test_lpe_cannot_cross_import_or_expand_authority():
    lpe = LPEPort("SOFIA", "memory://SOFIA")
    assert not hasattr(lpe, "set_authority") and not hasattr(lpe, "set_constitution")
    with pytest.raises(PermissionError):
        lpe.import_cross_ocs_autobiography("IRIS")
