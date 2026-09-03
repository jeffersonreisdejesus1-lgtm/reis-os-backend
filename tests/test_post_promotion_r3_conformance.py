from __future__ import annotations

from dataclasses import replace
from time import sleep, time

import pytest

from app.universal_kernel.contracts import (
    ActionProposal,
    AuthorizationDecision,
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


class AdversarialAdapter:
    def __init__(self, *, fail_readback: bool = False) -> None:
        self.mutations = 0
        self.compensations = 0
        self.fail_readback = fail_readback
        self.values: dict[str, dict[str, object]] = {}

    def mutate(
        self,
        operation: str,
        payload: dict[str, object],
        idempotency_key: str,
    ) -> str:
        self.mutations += 1
        mutation_id = f"m-{self.mutations}"
        self.values[mutation_id] = dict(payload)
        return mutation_id

    def readback(self, mutation_id: str) -> MaterialReadback:
        if self.fail_readback and mutation_id.startswith("m-"):
            raise RuntimeError("injected_post_effect_readback_failure")
        return MaterialReadback(mutation_id, dict(self.values.get(mutation_id, {})))

    def compensate(
        self,
        operation: str,
        payload: dict[str, object],
        mutation_id: str,
        idempotency_key: str,
    ) -> str:
        self.compensations += 1
        compensation_id = f"c-{self.compensations}"
        self.values[compensation_id] = {
            "compensated": mutation_id,
            "verified": True,
        }
        return compensation_id

    def verify_compensation(
        self,
        mutation_id: str,
        readback: MaterialReadback,
    ) -> bool:
        return bool(
            readback.state.get("compensated") == mutation_id
            and readback.state.get("verified") is True
        )


class ObservingBroker(ToolBroker):
    def __init__(self) -> None:
        super().__init__()
        self.resolutions = 0

    def adapter_for(self, capability: str):  # type: ignore[no-untyped-def]
        self.resolutions += 1
        return super().adapter_for(capability)


def _lease(
    *,
    lease_id: str = "lease-sofia",
    ocs: str = "SOFIA",
    actor: str = "SOFIA",
    capability: str = "repo.write",
    authority_ref: str = "authority:sofia",
    trace_ref: str = "trace:post-r3",
    expires_at: float | None = None,
) -> AuthorityLease:
    issued = time() - 1
    return AuthorityLease(
        lease_id=lease_id,
        ocs=ocs,
        capability=capability,
        expires_at=time() + 60 if expires_at is None else expires_at,
        actor=actor,
        issued_at=issued,
        not_before=issued,
        scope=(capability,),
        tenant="post-r3",
        context_ref="context:post-r3",
        authority_ref=authority_ref,
        policy_snapshot="policy:post-r3",
        action_binding="repository.write",
        object_ref_or_selector="object:post-r3",
        trace_ref=trace_ref,
        max_uses=4,
    )


def _proposal(
    *,
    lease_id: str = "lease-sofia",
    actor: str = "SOFIA",
    ocs: str = "SOFIA",
    capability: str = "repo.write",
    authority_ref: str = "authority:sofia",
    trace_id: str = "trace:post-r3",
    evidence: tuple[Evidence, ...] | None = None,
    risk: RiskLevel = RiskLevel.LOW,
    reversibility: ReversibilityClass = ReversibilityClass.REVERSIBLE,
    action_id: str = "post-r3-action",
    idem: str = "post-r3-idem",
) -> ActionProposal:
    return ActionProposal(
        action_id=action_id,
        actor=actor,
        ocs=ocs,
        capability=capability,
        operation="write",
        payload={"value": "post-r3"},
        risk=risk,
        lease_id=lease_id,
        evidence=(Evidence("e:post-r3", True, "AGORA"),)
        if evidence is None
        else evidence,
        action_type="repository.write",
        issued_at=time(),
        csp_ref=f"csp://{ocs.lower()}/current",
        object_ref="object:post-r3",
        tenant="post-r3",
        context_ref="context:post-r3",
        scope=(capability,),
        authority_ref=authority_ref,
        policy_snapshot="policy:post-r3",
        idempotency_key=idem,
        expected_effect="repository_write",
        side_effect_class=SideEffectClass.MATERIAL,
        reversibility_class=reversibility,
        recovery_ref="recovery:post-r3",
        expires_at=time() + 30,
        evidence_assessment_ref="assessment:post-r3",
        trace_id=trace_id,
    )


def _runtime(
    *,
    adapter: AdversarialAdapter | None = None,
    trace: TraceCore | None = None,
    recovery: RecoveryManager | None = None,
):  # type: ignore[no-untyped-def]
    identities = IdentityConstitutionLoader(
        (
            OCSIdentity(
                "SOFIA",
                "software_engineering",
                "post-r3",
                frozenset({"repo.write"}),
            ),
        )
    )
    capabilities = CapabilityRegistry()
    capabilities.register("SOFIA", frozenset({"repo.write"}))
    leases = AuthorityLeaseManager()
    leases.issue(_lease())
    governance = GovernanceEngine(identities, capabilities, EvidenceEngine(), leases)
    broker = ObservingBroker()
    bound_adapter = AdversarialAdapter() if adapter is None else adapter
    broker.register("repo.write", bound_adapter)
    state = StateCore()
    bound_trace = TraceCore() if trace is None else trace
    bound_recovery = RecoveryManager(state) if recovery is None else recovery
    runtime = UniversalKernelRuntime(
        governance,
        ThinEffector(broker),
        state,
        bound_trace,
        recovery=bound_recovery,
    )
    return runtime, bound_adapter, leases, state, bound_trace, broker, governance


def test_post_001_hold_is_emitted_by_governance_from_typed_evidence() -> None:
    runtime, adapter, _, _, trace, _, governance = _runtime()
    proposal = _proposal(
        evidence=(Evidence("candidate", True, None),),
        risk=RiskLevel.HIGH,
    )
    result = governance.authorize(proposal)
    assert result.decision is AuthorizationDecision.HOLD
    assert result.envelope is None
    assert result.evidence_assessment is not None
    assert result.evidence_assessment.sufficiency is False
    assert "independent_assurance_required" in result.evidence_assessment.deficits
    execution = runtime.execute(proposal)
    assert not execution.authorized
    assert execution.governance_decision is AuthorizationDecision.HOLD
    assert adapter.mutations == 0
    assert any(
        event.stage == "GOVERNANCE_DECISION"
        and event.details.get("decision") == "hold"
        for event in trace.events
    )


def test_post_002_statecore_rejects_direct_cross_namespace_write() -> None:
    state = StateCore()
    record = StateRecord("state:sofia:1", "SOFIA", 1, None, {"x": 1}, True)
    with pytest.raises(ValueError, match="state_namespace_violation"):
        state.write(
            record,
            lambda stored: stored == record,
            actor_ocs_id="AURI",
            target_namespace="state://SOFIA/runtime",
            state_ref=record.state_id,
            authority_context="authority:auri",
        )
    assert state.current("SOFIA") is None
    state.write(
        record,
        lambda stored: stored == record,
        actor_ocs_id="SOFIA",
        target_namespace="state://SOFIA/runtime",
        state_ref=record.state_id,
        authority_context="authority:sofia",
    )
    assert state.current("SOFIA") == record


def test_post_003_direct_adapter_resolution_is_structurally_denied() -> None:
    broker = ToolBroker()
    adapter = AdversarialAdapter()
    broker.register("repo.write", adapter)
    with pytest.raises(ValueError, match="direct_adapter_resolution_prohibited"):
        broker.adapter_for("repo.write")
    with pytest.raises(ValueError, match="direct_adapter_mutation_prohibited"):
        adapter.mutate("write", {}, "direct")
    assert adapter.mutations == 0


def test_post_004_runtime_dispatches_compensation_after_post_effect_failure() -> None:
    adapter = AdversarialAdapter(fail_readback=True)
    state = StateCore()
    checkpoint_state = StateRecord("safe", "SOFIA", 1, None, {"safe": True}, True)
    state.write(
        checkpoint_state,
        lambda stored: stored == checkpoint_state,
        actor_ocs_id="SOFIA",
        target_namespace="state://SOFIA/checkpoint",
        state_ref=checkpoint_state.state_id,
        authority_context="authority:checkpoint",
    )
    recovery = RecoveryManager(state)
    recovery.register_checkpoint(
        "recovery:post-r3",
        VerifiedCheckpoint("cp:post-r3", checkpoint_state),
    )
    identities = IdentityConstitutionLoader(
        (
            OCSIdentity(
                "SOFIA",
                "software_engineering",
                "post-r3",
                frozenset({"repo.write"}),
            ),
        )
    )
    capabilities = CapabilityRegistry()
    capabilities.register("SOFIA", frozenset({"repo.write"}))
    leases = AuthorityLeaseManager()
    leases.issue(_lease())
    governance = GovernanceEngine(identities, capabilities, EvidenceEngine(), leases)
    broker = ToolBroker()
    broker.register("repo.write", adapter)
    runtime = UniversalKernelRuntime(
        governance,
        ThinEffector(broker),
        state,
        TraceCore(),
        recovery=recovery,
    )
    result = runtime.execute(_proposal())
    assert result.authorized and result.effected and not result.proven
    assert adapter.mutations == 1
    assert adapter.compensations == 1
    assert result.recovery_receipt is not None
    assert result.recovery_receipt.material_compensated is True
    assert result.recovery_receipt.residual_effect is False
    assert result.recovery_receipt.external_readback is not None

    irreversible_adapter = AdversarialAdapter(fail_readback=True)
    runtime2, _, _, _, _, _, _ = _runtime(adapter=irreversible_adapter)
    irreversible = runtime2.execute(
        _proposal(
            reversibility=ReversibilityClass.IRREVERSIBLE,
            action_id="irreversible",
            idem="irreversible-idem",
        )
    )
    assert irreversible.recovery_receipt is not None
    assert irreversible.recovery_receipt.material_compensated is False
    assert irreversible.recovery_receipt.residual_effect is True


def test_post_005_invalid_lease_does_not_resurrect_across_replay_reload(
) -> None:
    leases = AuthorityLeaseManager()
    leases.issue(_lease(lease_id="old"))
    leases.revoke("old")
    snapshot = leases.snapshot()
    reloaded = AuthorityLeaseManager.from_snapshot(snapshot)
    ok, reason = reloaded.validate("old", "SOFIA", "repo.write")
    assert not ok and reason == "lease_revoked"

    reloaded.issue(_lease(lease_id="new"))
    ok, reason = reloaded.validate("old", "SOFIA", "repo.write")
    assert not ok and reason == "lease_revoked"

    copied = replace(_lease(lease_id="copied"), actor="AURI")
    reloaded.issue(copied)
    mismatched = reloaded.validate_proposal(
        _proposal(lease_id="copied", actor="SOFIA", ocs="SOFIA")
    )
    assert mismatched == (False, "lease_actor_mismatch")

    expiring = AuthorityLeaseManager()
    expiring.issue(_lease(lease_id="expired", expires_at=time() + 0.1))
    sleep(0.15)
    for _ in range(2):
        ok, reason = expiring.validate("expired", "SOFIA", "repo.write")
        assert not ok and reason == "lease_expired"


def test_post_006_handoff_acceptance_has_context_but_no_executable_authority() -> None:
    router = HandoffRouter()
    receipt = router.close(
        receipt_id="handoff:post-r3",
        source_ocs="MÊTIS",
        target_ocs="SYNERGEIA",
        state_ref="state:market",
        context_refs=("context:market",),
        evidence_refs=("evidence:market",),
        source_authority_ref="authority:metis",
    )
    accepted = router.accept(receipt, receiver_ocs="SYNERGEIA")
    assert receipt.handoff_id == "handoff:post-r3"
    assert receipt.authority_transferred is False
    assert receipt.source_authority_ref == ""
    assert accepted.context_refs == ("context:market",)
    assert accepted.evidence_refs == ("evidence:market",)
    assert accepted.executable_authority_ref is None


def test_post_007_trace_preflight_precedes_broker_and_finalization_failure(
) -> None:
    trace = TraceCore()
    trace.fail_next_preflight = True
    runtime, adapter, leases, _, _, broker, _ = _runtime(trace=trace)
    result = runtime.execute(_proposal())
    assert result.authorized and not result.effected and not result.proven
    assert result.reason == "trace_preflight_failed"
    assert leases.uses_consumed("lease-sofia") == 0
    assert broker.resolutions == 0
    assert adapter.mutations == 0

    trace2 = TraceCore()
    trace2.fail_next_finalization = True
    runtime2, adapter2, _, _, trace2, _, _ = _runtime(trace=trace2)
    result2 = runtime2.execute(
        _proposal(action_id="finalization", idem="finalization-idem")
    )
    assert result2.authorized and result2.effected and not result2.proven
    assert result2.reason == "trace_finalization_failed"
    assert result2.readback is not None
    assert result2.residual_effect is True
    assert adapter2.mutations == 1
    stages = [event.stage for event in trace2.events]
    assert stages.index("TRACE_PREFLIGHT") < stages.index("MATERIAL_EFFECT_READBACK")
