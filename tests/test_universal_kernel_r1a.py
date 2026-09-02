from __future__ import annotations

import time
from dataclasses import replace

import pytest

from app.universal_kernel.contracts import GovernanceResult, HandoffPackage
from app.universal_kernel.governance import (
    AuthorityLease,
    AuthorityLeaseManager,
    CapabilityDescriptor,
    CapabilityRegistry,
    EvidenceEngine,
    GovernanceEngine,
)
from app.universal_kernel.material import (
    InMemoryMutationAdapter,
    ThinEffector,
    ToolBroker,
)
from app.universal_kernel.runtime import (
    CognitiveRuntimePort,
    HandoffRouter,
    LearningCandidate,
    LPEPort,
    RecoveryManager,
)
from app.universal_kernel.state import InMemoryStateManager
from app.universal_kernel.trace import TraceLedger


CAPABILITY = "cap.write"
SCOPE = "object:write"


def build_runtime(*, expires_at: int | None = None) -> tuple[
    CognitiveRuntimePort,
    CapabilityRegistry,
    EvidenceEngine,
    AuthorityLeaseManager,
    GovernanceEngine,
    ToolBroker,
    ThinEffector,
    InMemoryMutationAdapter,
    TraceLedger,
]:
    trace = TraceLedger()
    registry = CapabilityRegistry()
    registry.register(
        CapabilityDescriptor(
            capability_id=CAPABILITY,
            adapter_id="fake",
            side_effect_class="PERSISTENT_MUTATION",
            required_scope=SCOPE,
            reversibility="R1_STATE_ONLY",
            idempotency_support=True,
            readback_support=True,
        )
    )
    leases = AuthorityLeaseManager()
    expiry = expires_at if expires_at is not None else int(time.time()) + 3600
    leases.grant(
        AuthorityLease(
            lease_ref="lease-1",
            authority_ref="auth-1",
            actor="actor",
            ocs_id="sofia",
            action_type="write",
            object_ref="obj-1",
            scope=SCOPE,
            context_ref="ctx-1",
            expires_at=expiry,
            max_uses=1,
        )
    )
    governance = GovernanceEngine(registry, leases, trace)
    broker = ToolBroker(registry, leases, trace)
    adapter = InMemoryMutationAdapter(adapter_id="fake")
    broker.bind_adapter(adapter)
    return (
        CognitiveRuntimePort(),
        registry,
        EvidenceEngine(),
        leases,
        governance,
        broker,
        ThinEffector(leases, trace),
        adapter,
        trace,
    )


def proposal(
    runtime: CognitiveRuntimePort,
    *,
    evidence_refs: tuple[str, ...] = ("ev-pass",),
):
    return runtime.propose(
        proposal_id="p1",
        actor="actor",
        ocs_id="sofia",
        csp_ref="csp-sofia",
        goal_ref="goal-1",
        action_type="write",
        object_ref="obj-1",
        scope_requested=SCOPE,
        capability_ref=CAPABILITY,
        evidence_refs=evidence_refs,
        expected_effect="write state",
        side_effect_class="PERSISTENT_MUTATION",
        reversibility_class="R1_STATE_ONLY",
        context_ref="ctx-1",
        authority_ref="auth-1",
    )


def authorize(runtime_tuple):
    runtime, _, evidence, _, governance, _, _, _, _ = runtime_tuple
    p = proposal(runtime)
    assessment = evidence.assess(
        proposal=p,
        required=True,
        passing_refs={"ev-pass"},
    )
    return governance.decide(
        proposal=p,
        assessment=assessment,
        policy_snapshot="policy-v1",
        tenant="tenant-1",
        recovery_ref="recovery-1",
    )


def test_deny_causes_zero_mutation() -> None:
    runtime_tuple = build_runtime()
    runtime, _, evidence, _, governance, _, _, adapter, _ = runtime_tuple
    p = proposal(runtime, evidence_refs=("ev-fail",))
    assessment = evidence.assess(proposal=p, required=True, passing_refs=set())
    decision = governance.decide(
        proposal=p,
        assessment=assessment,
        policy_snapshot="policy-v1",
        tenant="tenant-1",
        recovery_ref="recovery-1",
    )
    assert decision.result is GovernanceResult.DENY
    assert decision.envelope is None
    assert adapter.mutation_count == 0


def test_expired_lease_causes_zero_mutation() -> None:
    runtime_tuple = build_runtime(expires_at=int(time.time()) - 1)
    decision = authorize(runtime_tuple)
    adapter = runtime_tuple[7]
    broker = runtime_tuple[5]
    assert decision.result is GovernanceResult.DENY
    assert broker.resolution_count == 0
    assert adapter.mutation_count == 0


def test_revoked_lease_causes_zero_mutation() -> None:
    runtime_tuple = build_runtime()
    decision = authorize(runtime_tuple)
    assert decision.envelope is not None
    leases = runtime_tuple[3]
    broker = runtime_tuple[5]
    adapter = runtime_tuple[7]
    leases.revoke("lease-1")
    with pytest.raises(PermissionError):
        broker.resolve(decision.envelope, CAPABILITY)
    assert adapter.mutation_count == 0


def test_authorized_effect_uses_broker_and_thin_effector() -> None:
    runtime_tuple = build_runtime()
    decision = authorize(runtime_tuple)
    assert decision.result is GovernanceResult.AUTHORIZE
    assert decision.envelope is not None
    invocation = runtime_tuple[5].resolve(decision.envelope, CAPABILITY)
    result = runtime_tuple[6].execute(invocation)
    assert result.attempted is True
    assert result.mutation_count == 1
    assert result.readback_ref is not None
    assert runtime_tuple[7].mutation_count == 1


def test_handoff_transfers_no_authority() -> None:
    package = HandoffRouter().create_package(
        handoff_id="h1",
        from_ocs="sofia",
        to_ocs="agora",
        object_ref="obj",
        context_refs=("ctx",),
        evidence_refs=("ev",),
        open_findings=(),
        requested_scope="verify-only",
        prohibited_consequences=("NO_AUTHORITY_TRANSFER",),
        predecessor_receipt_ref="receipt-1",
    )
    assert package.authority_transfer is False
    with pytest.raises(ValueError):
        HandoffPackage(
            handoff_id="bad",
            from_ocs="sofia",
            to_ocs="agora",
            object_ref="obj",
            context_refs=(),
            evidence_refs=(),
            open_findings=(),
            requested_scope="scope",
            prohibited_consequences=(),
            predecessor_receipt_ref="receipt",
            authority_transfer=True,
        )


def test_state_write_has_version_and_predecessor() -> None:
    trace = TraceLedger()
    state = InMemoryStateManager(trace)
    first = state.commit_write(
        namespace="state://sofia/v1/working",
        payload={"value": "a"},
        expected_predecessor=None,
        authority_ref="auth",
        action_id="a1",
        trace_ref="t1",
    )
    second = state.commit_write(
        namespace="state://sofia/v1/working",
        payload={"value": "b"},
        expected_predecessor=1,
        authority_ref="auth",
        action_id="a2",
        trace_ref="t2",
    )
    assert first.version == 1 and first.predecessor_version is None
    assert second.version == 2 and second.predecessor_version == 1
    assert second.readback_hash == second.content_hash


def test_recovery_restores_verified_state() -> None:
    trace = TraceLedger()
    state = InMemoryStateManager(trace)
    state.commit_write(
        namespace="state://sofia/v1/working",
        payload={"value": "verified"},
        expected_predecessor=None,
        authority_ref="auth",
        action_id="a1",
        trace_ref="t1",
    )
    checkpoint = state.checkpoint("state://sofia/v1/working")
    state.commit_write(
        namespace="state://sofia/v1/working",
        payload={"value": "later"},
        expected_predecessor=1,
        authority_ref="auth",
        action_id="a2",
        trace_ref="t2",
    )
    restored = RecoveryManager(state, trace).restore_verified(checkpoint)
    assert restored.payload == {"value": "verified"}
    assert restored.verified is True


def test_trace_break_returns_not_proven() -> None:
    trace = TraceLedger()
    event = trace.append("one", {"x": "1"})
    trace._events[0] = replace(event, previous_hash="BROKEN")
    assert trace.mark_not_proven_if_broken() == "NOT_PROVEN"


def test_high_risk_evidence_failure_blocks_effect() -> None:
    runtime_tuple = build_runtime()
    runtime, _, evidence, _, governance, broker, _, adapter, _ = runtime_tuple
    p = proposal(runtime, evidence_refs=("missing",))
    assessment = evidence.assess(
        proposal=p,
        required=True,
        passing_refs={"other"},
    )
    decision = governance.decide(
        proposal=p,
        assessment=assessment,
        policy_snapshot="high-risk-v1",
        tenant="tenant-1",
        recovery_ref="recovery-1",
    )
    assert decision.result is GovernanceResult.DENY
    assert broker.resolution_count == 0
    assert adapter.mutation_count == 0


def test_self_assurance_is_denied() -> None:
    runtime_tuple = build_runtime()
    runtime, _, evidence, _, governance, _, _, _, _ = runtime_tuple
    p = proposal(runtime)
    assessment = evidence.assess(
        proposal=p,
        required=True,
        passing_refs={"ev-pass"},
        self_assurance_claimed=True,
    )
    decision = governance.decide(
        proposal=p,
        assessment=assessment,
        policy_snapshot="policy-v1",
        tenant="tenant-1",
        recovery_ref="recovery-1",
    )
    assert assessment.sufficient is False
    assert "SELF_ASSURANCE_DENIED" in decision.reason_codes
    assert decision.result is GovernanceResult.DENY


def test_lateral_effect_route_exists_false() -> None:
    runtime = CognitiveRuntimePort()
    registry = CapabilityRegistry()
    assert not hasattr(runtime, "execute")
    assert not hasattr(runtime, "adapter")
    assert not hasattr(registry, "execute")


def test_learning_cannot_expand_authority() -> None:
    port = LPEPort()
    with pytest.raises(PermissionError):
        port.consolidate(
            LearningCandidate("exp-1", "sofia", "CANDIDATE", authority_delta=1),
            verified=True,
        )
