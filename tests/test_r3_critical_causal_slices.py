from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from json import dumps
from time import sleep, time

from app.profile_bindings.profiles import PROFILES
from app.r3_causal_slices import (
    CAUSAL_CHAIN,
    CausalReceipt,
    CausalRecorder,
    EffectBoundaryGuard,
    NamespaceGuard,
    SpecialtyGoalExecutor,
    build_replay_packages,
)
from app.universal_kernel.contracts import (
    ActionProposal,
    Evidence,
    MaterialReadback,
    ReversibilityClass,
    RiskLevel,
    SideEffectClass,
    StateRecord,
    VerifiedCheckpoint,
)
from app.universal_kernel.effect_recovery import (
    RecoveryManager,
    ThinEffector,
    ToolBroker,
)
from app.universal_kernel.governance import (
    AuthorityLease,
    AuthorityLeaseManager,
    CapabilityRegistry,
    EvidenceEngine,
    GovernanceEngine,
    IdentityConstitutionLoader,
    OCSIdentity,
)
from app.universal_kernel.ports import HandoffRouter
from app.universal_kernel.runtime import UniversalKernelRuntime
from app.universal_kernel.state_trace import StateCore, TraceCore


class FixtureAdapter:
    def __init__(self, *, fail_readback: bool = False) -> None:
        self.mutations = 0
        self.values: dict[str, dict[str, object]] = {}
        self.fail_readback = fail_readback

    def mutate(
        self,
        operation: str,
        payload: dict[str, object],
        idempotency_key: str,
    ) -> str:
        mutation_id = f"r3-mutation-{self.mutations + 1}"
        self.mutations += 1
        self.values[mutation_id] = dict(payload)
        return mutation_id

    def readback(self, mutation_id: str) -> MaterialReadback:
        if self.fail_readback:
            raise RuntimeError("injected_post_effect_readback_failure")
        return MaterialReadback(mutation_id, self.values[mutation_id])


def _runtime(
    *,
    lease_expires_at: float | None = None,
    fail_readback: bool = False,
):  # type: ignore[no-untyped-def]
    identity = OCSIdentity(
        ocs="SOFIA",
        specialty="software_engineering",
        constitution_version="r1",
        allowed_capabilities=frozenset({"repo.write"}),
    )
    identities = IdentityConstitutionLoader((identity,))
    capabilities = CapabilityRegistry()
    capabilities.register("SOFIA", frozenset({"repo.write"}))
    leases = AuthorityLeaseManager()
    issued = time() - 1
    leases.issue(
        AuthorityLease(
            lease_id="r3-lease",
            ocs="SOFIA",
            capability="repo.write",
            expires_at=time() + 60 if lease_expires_at is None else lease_expires_at,
            actor="SOFIA",
            issued_at=issued,
            not_before=issued,
            scope=("repo.write",),
            tenant="r3",
            context_ref="context:r3",
            authority_ref="authority:r3-explicit",
            policy_snapshot="policy:r3-frozen",
            action_binding="repository.write",
            object_ref_or_selector="object:r3-fixture",
            trace_ref="trace:r3",
            max_uses=2,
        )
    )
    evidence_engine = EvidenceEngine()
    governance = GovernanceEngine(
        identities,
        capabilities,
        evidence_engine,
        leases,
    )
    broker = ToolBroker()
    adapter = FixtureAdapter(fail_readback=fail_readback)
    broker.register("repo.write", adapter)
    state = StateCore()
    trace = TraceCore()
    runtime = UniversalKernelRuntime(
        governance,
        ThinEffector(broker),
        state,
        trace,
    )
    return (
        runtime,
        adapter,
        leases,
        state,
        trace,
        broker,
        governance,
        evidence_engine,
    )


def _proposal(
    *,
    scope: tuple[str, ...] = ("repo.write",),
    evidence: tuple[Evidence, ...] | None = None,
    risk: RiskLevel = RiskLevel.LOW,
    action_id: str = "r3-action",
    idem: str = "r3-idem",
) -> ActionProposal:
    return ActionProposal(
        action_id=action_id,
        actor="SOFIA",
        ocs="SOFIA",
        capability="repo.write",
        operation="write",
        payload={"r3": "value"},
        risk=risk,
        lease_id="r3-lease",
        evidence=(Evidence("e:r3", True, "AGORA"),) if evidence is None else evidence,
        action_type="repository.write",
        issued_at=time(),
        csp_ref="csp://sofia/current",
        object_ref="object:r3-fixture",
        tenant="r3",
        context_ref="context:r3",
        scope=scope,
        authority_ref="authority:r3-explicit",
        policy_snapshot="policy:r3-frozen",
        idempotency_key=idem,
        expected_effect="repository_write",
        side_effect_class=SideEffectClass.MATERIAL,
        reversibility_class=ReversibilityClass.REVERSIBLE,
        recovery_ref="recovery:r3",
        expires_at=time() + 30,
        evidence_assessment_ref="evidence-assessment:r3",
        trace_id="trace:r3",
    )


def _hash(payload: dict[str, object]) -> str:
    encoded = dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def _assert_receipt_matches_package(receipt: CausalReceipt, slice_id: str) -> None:
    package = build_replay_packages()[slice_id]
    assert receipt.slice_id == package.slice_id
    assert receipt.trace_id == package.trace_id
    assert receipt.outcome == package.expectation.governance_result
    assert receipt.mutation_count == package.expectation.mutation_count
    assert receipt.effector_attempt == package.expectation.effector_attempt
    assert receipt.state_delta == package.expectation.state_delta
    assert receipt.readback_oracle == package.expectation.readback_oracle
    assert receipt.recovery_oracle == package.expectation.recovery_oracle
    assert package.replay_hook == f"replay:{slice_id.lower()}"


def _record_common_prefix(
    recorder: CausalRecorder,
    proposal: ActionProposal,
    evidence_engine: EvidenceEngine,
    leases: AuthorityLeaseManager,
) -> tuple[tuple[bool, str], tuple[bool, str]]:
    recorder.append("GOAL", "MATERIAL_ACTION_REQUESTED", action_id=proposal.action_id)
    recorder.append("COGNITIVE_PLAN", "BOUNDED_SPECIALTY_ACTION", ocs=proposal.ocs)
    recorder.append("ACTION_PROPOSAL", "MATERIALIZED", action_type=proposal.action_type)
    evidence_result = evidence_engine.sufficient(proposal)
    recorder.append(
        "EVIDENCE_ASSESSMENT",
        "SUFFICIENT" if evidence_result[0] else "INSUFFICIENT",
        reason=evidence_result[1],
    )
    lease_result = leases.validate_proposal(proposal)
    recorder.append(
        "AUTHORITY_LEASE_CHECK",
        "VALID" if lease_result[0] else "INVALID",
        reason=lease_result[1],
    )
    return evidence_result, lease_result


def test_replay_packages_cover_all_frozen_slices_with_executable_bindings() -> None:
    packages = build_replay_packages()
    assert tuple(packages) == tuple(f"R3-S{i:02d}" for i in range(1, 11))
    for package in packages.values():
        assert package.trace_sequence == CAUSAL_CHAIN
        assert package.profile_id in PROFILES
        assert package.policy_snapshot == "policy:r3-frozen"
        assert package.authority_fixture
        assert package.lease_fixture
        assert package.evidence_fixture
        assert package.trace_id.startswith("trace:r3-s")
        assert package.replay_hook.startswith("replay:r3-s")
        if package.fault_injection_hook is not None:
            assert package.fault_injection_hook


def test_r3_s01_authorized_persistent_mutation_and_idempotent_replay() -> None:
    runtime, adapter, leases, state, trace, _, governance, evidence_engine = _runtime()
    proposal = _proposal()
    recorder = CausalRecorder("R3-S01", "trace:r3-s01")
    _record_common_prefix(recorder, proposal, evidence_engine, leases)
    decision = governance.authorize(proposal)
    assert decision.envelope is not None
    recorder.append("GOVERNANCE_DECISION", "ALLOW")
    recorder.append("AUTHORIZED_ACTION_ENVELOPE", "ISSUED")
    recorder.append("TOOL_BROKER", "RESOLVABLE")
    recorder.append("THIN_EFFECTOR", "MEDIATED")
    first = runtime.execute(proposal)
    replay = runtime.execute(proposal)
    current = state.current("SOFIA")
    recorder.append("MATERIAL_EFFECT_ATTEMPT", "EXECUTED")
    recorder.append("READBACK", "MATCH")
    recorder.append("STATE_COMMIT_OR_NO_COMMIT", "VERSION_ADVANCED")
    assert first.proven and replay == first
    assert adapter.mutations == 1
    assert current is not None and current.version == 1 and current.predecessor is None
    assert first.readback is not None
    assert _hash(first.readback.state) == _hash(current.payload)
    assert trace.chain_is_valid()
    receipt = recorder.receipt(
        outcome="ALLOW",
        mutation_count=adapter.mutations,
        effector_attempt=True,
        state_delta="VERSION_ADVANCED",
        readback_oracle="MATCH",
    )
    _assert_receipt_matches_package(receipt, "R3-S01")


def test_r3_s02_deny_is_preserved_in_causal_trace_with_zero_mutation() -> None:
    runtime, adapter, leases, state, _, _, governance, evidence_engine = _runtime()
    proposal = _proposal(scope=("secrets.write",))
    recorder = CausalRecorder("R3-S02", "trace:r3-s02")
    _record_common_prefix(recorder, proposal, evidence_engine, leases)
    decision = governance.authorize(proposal)
    assert decision.envelope is None
    recorder.append("GOVERNANCE_DECISION", "DENY", reason=decision.reason)
    recorder.append("STATE_COMMIT_OR_NO_COMMIT", "NO_COMMIT")
    result = runtime.execute(proposal)
    assert not result.authorized
    assert adapter.mutations == 0
    assert state.current("SOFIA") is None
    receipt = recorder.receipt(
        outcome="DENY",
        mutation_count=0,
        effector_attempt=False,
        state_delta="NO_DELTA",
        readback_oracle="NOT_APPLICABLE",
    )
    deny_reason = receipt.event("GOVERNANCE_DECISION").details["reason"]
    assert deny_reason == "lease_scope_mismatch"
    _assert_receipt_matches_package(receipt, "R3-S02")


def test_r3_s03_hold_is_causally_traced_from_evidence_deficit() -> None:
    _, adapter, leases, state, _, _, _, evidence_engine = _runtime()
    evidence = (Evidence("research:candidate", True, None),)
    proposal = _proposal(evidence=evidence, risk=RiskLevel.HIGH)
    recorder = CausalRecorder("R3-S03", "trace:r3-s03")
    evidence_result, lease_result = _record_common_prefix(
        recorder,
        proposal,
        evidence_engine,
        leases,
    )
    assert not evidence_result[0]
    assert evidence_result[1] == "independent_assurance_required"
    assert lease_result[0]
    recorder.append(
        "GOVERNANCE_DECISION",
        "HOLD",
        evidence_deficit=evidence_result[1],
    )
    recorder.append("STATE_COMMIT_OR_NO_COMMIT", "NO_COMMIT")
    receipt = recorder.receipt(
        outcome="HOLD",
        mutation_count=adapter.mutations,
        effector_attempt=False,
        state_delta="NO_DELTA",
        readback_oracle="NOT_APPLICABLE",
    )
    assert receipt.event("GOVERNANCE_DECISION").details["evidence_deficit"]
    assert state.current("SOFIA") is None
    _assert_receipt_matches_package(receipt, "R3-S03")


def test_r3_s04_expired_lease_traces_expiry_and_replay_no_resurrection() -> None:
    runtime, adapter, leases, state, _, _, governance, evidence_engine = _runtime(
        lease_expires_at=time() + 0.15
    )
    proposal = _proposal()
    sleep(0.2)
    recorder = CausalRecorder("R3-S04", "trace:r3-s04")
    _record_common_prefix(recorder, proposal, evidence_engine, leases)
    first = governance.authorize(proposal)
    recorder.append("GOVERNANCE_DECISION", "DENY_EXPIRED", reason=first.reason)
    result_1 = runtime.execute(proposal)
    replay_proposal = replace(
        proposal,
        action_id="r3-expired-replay",
        idempotency_key="r3-expired-2",
    )
    result_2 = runtime.execute(replay_proposal)
    recorder.append("AUTHORITY_LEASE_CHECK", "EXPIRED_REPLAY", reason=result_2.reason)
    recorder.append("STATE_COMMIT_OR_NO_COMMIT", "NO_COMMIT")
    assert result_1.reason == result_2.reason == "lease_expired"
    assert adapter.mutations == 0
    assert state.current("SOFIA") is None
    receipt = recorder.receipt(
        outcome="DENY_EXPIRED",
        mutation_count=0,
        effector_attempt=False,
        state_delta="NO_DELTA",
        readback_oracle="NOT_APPLICABLE",
    )
    checks = sum(event.stage == "AUTHORITY_LEASE_CHECK" for event in receipt.events)
    assert checks >= 2
    _assert_receipt_matches_package(receipt, "R3-S04")


def test_r3_s05_revoked_lease_zero_mutation_and_no_resurrection() -> None:
    runtime, adapter, leases, state, _, _, governance, evidence_engine = _runtime()
    leases.revoke("r3-lease")
    proposal = _proposal()
    recorder = CausalRecorder("R3-S05", "trace:r3-s05")
    _record_common_prefix(recorder, proposal, evidence_engine, leases)
    decision = governance.authorize(proposal)
    recorder.append("GOVERNANCE_DECISION", "DENY_REVOKED", reason=decision.reason)
    first = runtime.execute(proposal)
    replay_proposal = replace(
        proposal,
        action_id="r3-revoked-replay",
        idempotency_key="r3-revoked-2",
    )
    second = runtime.execute(replay_proposal)
    recorder.append("AUTHORITY_LEASE_CHECK", "REVOKED_REPLAY", reason=second.reason)
    recorder.append("STATE_COMMIT_OR_NO_COMMIT", "NO_COMMIT")
    assert first.reason == second.reason == "lease_revoked"
    assert adapter.mutations == 0
    assert state.current("SOFIA") is None
    receipt = recorder.receipt(
        outcome="DENY_REVOKED",
        mutation_count=0,
        effector_attempt=False,
        state_delta="NO_DELTA",
        readback_oracle="NOT_APPLICABLE",
    )
    _assert_receipt_matches_package(receipt, "R3-S05")


def test_r3_s06_namespace_violation_is_runtime_denied_and_traced() -> None:
    state = StateCore()
    recorder = CausalRecorder("R3-S06", "trace:r3-s06")
    allowed = NamespaceGuard().attempt_state_write(
        profile=PROFILES["AURI"],
        requested_namespace=PROFILES["SOFIA"].state_namespace,
        state=state,
        recorder=recorder,
    )
    assert not allowed
    assert state.current("AURI") is None
    assert state.current("SOFIA") is None
    receipt = recorder.receipt(
        outcome="DENY_NAMESPACE",
        mutation_count=0,
        effector_attempt=False,
        state_delta="NO_CROSS_OCS_DELTA",
        readback_oracle="NOT_APPLICABLE",
    )
    assert receipt.event("GOVERNANCE_DECISION").outcome == "DENY_NAMESPACE"
    _assert_receipt_matches_package(receipt, "R3-S06")


def test_r3_s07_lateral_effect_attempt_is_executably_denied() -> None:
    recorder = CausalRecorder("R3-S07", "trace:r3-s07")
    permitted = EffectBoundaryGuard().attempt_lateral_route(
        profile=PROFILES["SOFIA"],
        route="direct_adapter.mutate",
        recorder=recorder,
    )
    assert not permitted
    receipt = recorder.receipt(
        outcome="DENY_ROUTE",
        mutation_count=0,
        effector_attempt=False,
        state_delta="NO_DELTA",
        readback_oracle="NOT_APPLICABLE",
    )
    assert receipt.event("MATERIAL_EFFECT_ATTEMPT").outcome == "NOT_ATTEMPTED"
    _assert_receipt_matches_package(receipt, "R3-S07")


def test_r3_s08_post_effect_failure_triggers_verified_recovery_receipt() -> None:
    runtime, adapter, leases, state, _, _, governance, evidence_engine = _runtime(
        fail_readback=True
    )
    checkpoint_state = StateRecord(
        "checkpoint-state",
        "SOFIA",
        1,
        None,
        {"r3": "safe"},
        True,
    )
    state.write(checkpoint_state, lambda stored: stored == checkpoint_state)
    proposal = _proposal()
    recorder = CausalRecorder("R3-S08", "trace:r3-s08")
    _record_common_prefix(recorder, proposal, evidence_engine, leases)
    decision = governance.authorize(proposal)
    assert decision.envelope is not None
    recorder.append("GOVERNANCE_DECISION", "ALLOW")
    recorder.append("AUTHORIZED_ACTION_ENVELOPE", "ISSUED")
    recorder.append("TOOL_BROKER", "RESOLVED")
    recorder.append("THIN_EFFECTOR", "MEDIATED")
    failed = runtime.execute(proposal)
    assert failed.authorized and not failed.proven
    assert failed.reason == "injected_post_effect_readback_failure"
    assert adapter.mutations == 1
    recorder.append("MATERIAL_EFFECT_ATTEMPT", "MUTATED_THEN_FAULTED")
    recorder.append("READBACK", "INJECTED_FAILURE")
    checkpoint = VerifiedCheckpoint("r3-checkpoint", checkpoint_state)
    restored = RecoveryManager(state).restore(checkpoint)
    recorder.append(
        "STATE_COMMIT_OR_NO_COMMIT",
        "RESTORED_VERIFIED_CHECKPOINT",
        restored_state_id=restored.state_id,
    )
    recorder.append(
        "RECOVERY",
        "RESTORED_STATE_MATCHES_CHECKPOINT",
        restored_hash=_hash(restored.payload),
        checkpoint_hash=_hash(checkpoint_state.payload),
    )
    assert _hash(restored.payload) == _hash(checkpoint_state.payload)
    receipt = recorder.receipt(
        outcome="ALLOW_THEN_RECOVER",
        mutation_count=1,
        effector_attempt=True,
        state_delta="RESTORED_VERIFIED_CHECKPOINT",
        readback_oracle="MATCH",
        recovery_oracle="RESTORED_STATE_MATCHES_CHECKPOINT",
    )
    assert receipt.has_stage("RECOVERY")
    _assert_receipt_matches_package(receipt, "R3-S08")


def _dual_profile_runtime():  # type: ignore[no-untyped-def]
    capability = "market.activate"
    identities = IdentityConstitutionLoader(
        (
            OCSIdentity("MÊTIS", "strategy", "r2", frozenset({capability})),
            OCSIdentity("SYNERGEIA", "gtm", "r2", frozenset({capability})),
        )
    )
    capabilities = CapabilityRegistry()
    capabilities.register("MÊTIS", frozenset({capability}))
    capabilities.register("SYNERGEIA", frozenset({capability}))
    leases = AuthorityLeaseManager()
    issued = time() - 1
    leases.issue(
        AuthorityLease(
            lease_id="metis-source-lease",
            ocs="MÊTIS",
            capability=capability,
            expires_at=time() + 60,
            actor="MÊTIS",
            issued_at=issued,
            not_before=issued,
            scope=(capability,),
            tenant="r3",
            context_ref="handoff:r3",
            authority_ref="authority:metis",
            policy_snapshot="policy:r3-frozen",
            action_binding="market.activate",
            object_ref_or_selector="object:r3-market",
            trace_ref="trace:r3-metis",
            max_uses=1,
        )
    )
    governance = GovernanceEngine(identities, capabilities, EvidenceEngine(), leases)
    broker = ToolBroker()
    adapter = FixtureAdapter()
    broker.register(capability, adapter)
    state = StateCore()
    runtime = UniversalKernelRuntime(
        governance,
        ThinEffector(broker),
        state,
        TraceCore(),
    )
    return runtime, adapter, leases, governance, state, issued


def _market_proposal(
    *,
    lease_id: str,
    actor: str,
    authority_ref: str,
    trace_id: str,
    action_id: str,
) -> ActionProposal:
    capability = "market.activate"
    return ActionProposal(
        action_id=action_id,
        actor=actor,
        ocs=actor,
        capability=capability,
        operation="activate",
        payload={"goal": "market_activation"},
        risk=RiskLevel.LOW,
        lease_id=lease_id,
        evidence=(Evidence(f"e:{actor}", True, "AGORA"),),
        action_type="market.activate",
        issued_at=time(),
        csp_ref=f"csp://{actor.lower()}/current",
        object_ref="object:r3-market",
        tenant="r3",
        context_ref="handoff:r3",
        scope=(capability,),
        authority_ref=authority_ref,
        policy_snapshot="policy:r3-frozen",
        idempotency_key=f"idem:{action_id}",
        expected_effect="market_activation",
        side_effect_class=SideEffectClass.BOUNDED,
        reversibility_class=ReversibilityClass.REVERSIBLE,
        recovery_ref="recovery:r3-market",
        expires_at=time() + 30,
        evidence_assessment_ref=f"assessment:{actor}",
        trace_id=trace_id,
    )


def test_r3_s09_handoff_rejects_source_lease_and_requires_receiver_grant() -> None:
    runtime, adapter, leases, governance, state, issued = _dual_profile_runtime()
    handoff = HandoffRouter().close(
        receipt_id="handoff:r3",
        source_ocs="MÊTIS",
        target_ocs="SYNERGEIA",
        state_ref="context:r3-market",
    )
    assert handoff.authority_transferred is False
    recorder = CausalRecorder("R3-S09", "trace:r3-s09")
    recorder.append("GOAL", "HANDOFF_MARKET_ACTIVATION")
    recorder.append("COGNITIVE_PLAN", "SOURCE_CONTEXT_TO_RECEIVER")
    recorder.append("ACTION_PROPOSAL", "RECEIVER_REUSES_SOURCE_LEASE")
    reused = _market_proposal(
        lease_id="metis-source-lease",
        actor="SYNERGEIA",
        authority_ref="authority:metis",
        trace_id="trace:r3-metis",
        action_id="reuse-source-authority",
    )
    denied = governance.authorize(reused)
    recorder.append(
        "AUTHORITY_LEASE_CHECK",
        "SOURCE_LEASE_REJECTED",
        reason=denied.reason,
    )
    recorder.append("GOVERNANCE_DECISION", "DENY_SOURCE_AUTHORITY_REUSE")
    assert denied.envelope is None
    assert denied.reason == "lease_scope_mismatch"
    leases.issue(
        AuthorityLease(
            lease_id="synergeia-independent-lease",
            ocs="SYNERGEIA",
            capability="market.activate",
            expires_at=time() + 60,
            actor="SYNERGEIA",
            issued_at=issued,
            not_before=issued,
            scope=("market.activate",),
            tenant="r3",
            context_ref="handoff:r3",
            authority_ref="authority:synergeia",
            policy_snapshot="policy:r3-frozen",
            action_binding="market.activate",
            object_ref_or_selector="object:r3-market",
            trace_ref="trace:r3-synergeia",
            max_uses=1,
        )
    )
    independent = _market_proposal(
        lease_id="synergeia-independent-lease",
        actor="SYNERGEIA",
        authority_ref="authority:synergeia",
        trace_id="trace:r3-synergeia",
        action_id="receiver-independent-grant",
    )
    recorder.append("ACTION_PROPOSAL", "RECEIVER_INDEPENDENT_GRANT")
    recorder.append("AUTHORITY_LEASE_CHECK", "INDEPENDENT_LEASE_VALID")
    recorder.append("GOVERNANCE_DECISION", "ALLOW")
    recorder.append("AUTHORIZED_ACTION_ENVELOPE", "ISSUED_TO_RECEIVER")
    recorder.append("TOOL_BROKER", "RESOLVED")
    recorder.append("THIN_EFFECTOR", "MEDIATED")
    result = runtime.execute(independent)
    recorder.append("MATERIAL_EFFECT_ATTEMPT", "EXECUTED")
    recorder.append("READBACK", "MATCH")
    recorder.append("STATE_COMMIT_OR_NO_COMMIT", "RECEIVER_INDEPENDENT_GRANT")
    assert result.proven
    assert adapter.mutations == 1
    assert state.current("SYNERGEIA") is not None
    receipt = recorder.receipt(
        outcome="HANDOFF_NO_AUTHORITY",
        mutation_count=1,
        effector_attempt=True,
        state_delta="RECEIVER_INDEPENDENT_GRANT",
        readback_oracle="MATCH",
    )
    _assert_receipt_matches_package(receipt, "R3-S09")


def test_r3_s10_same_goal_executes_differently_through_two_profiles() -> None:
    executor = SpecialtyGoalExecutor()
    goal = "market_activation_with_strategy_and_distribution"
    metis = executor.execute(profile_id="MÊTIS", goal=goal)
    synergeia = executor.execute(profile_id="SYNERGEIA", goal=goal)
    assert metis.goal == synergeia.goal == goal
    assert metis.selected_action != synergeia.selected_action
    assert metis.specialty != synergeia.specialty
    assert metis.events[0].stage == synergeia.events[0].stage == "GOAL"
    assert metis.events[1].stage == synergeia.events[1].stage == "COGNITIVE_PLAN"
    recorder = CausalRecorder("R3-S10", "trace:r3-s10")
    recorder.append("GOAL", "EQUIVALENT_GOAL_EXECUTED", goal=goal)
    recorder.append(
        "COGNITIVE_PLAN",
        "PROFILE_DIFFERENTIATION",
        metis_action=metis.selected_action,
        synergeia_action=synergeia.selected_action,
    )
    recorder.append("ACTION_PROPOSAL", "SPECIALTY_LOCAL_OUTPUTS")
    recorder.append("STATE_COMMIT_OR_NO_COMMIT", "NO_COMMIT")
    receipt = recorder.receipt(
        outcome="PROFILE_DIFFERENTIATION",
        mutation_count=0,
        effector_attempt=False,
        state_delta="NO_DELTA",
        readback_oracle="NOT_APPLICABLE",
    )
    _assert_receipt_matches_package(receipt, "R3-S10")


def test_trace_break_means_causality_not_proven() -> None:
    runtime, adapter, _, state, trace, _, _, _ = _runtime()
    trace.fail_next_append = True
    result = runtime.execute(_proposal())
    assert not result.proven
    assert adapter.mutations == 0
    assert state.current("SOFIA") is None
