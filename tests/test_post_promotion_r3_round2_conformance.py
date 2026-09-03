from __future__ import annotations

from time import time

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
)
from app.universal_kernel.effect_recovery import (
    CompensationVerifier,
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


class Round2Adapter:
    def __init__(
        self,
        *,
        fail_readback: bool = False,
        compensation_verified: bool = True,
        compensation_store: dict[str, dict[str, object]] | None = None,
    ) -> None:
        self.mutations = 0
        self.compensations = 0
        self.fail_readback = fail_readback
        self.compensation_verified = compensation_verified
        self.values: dict[str, dict[str, object]] = {}
        self.compensation_store = {} if compensation_store is None else compensation_store

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
        self.compensation_store[compensation_id] = {
            "compensated": mutation_id,
            "verified": self.compensation_verified,
        }
        return compensation_id

    def verify_compensation(
        self,
        mutation_id: str,
        readback: MaterialReadback,
    ) -> bool:
        return True


class Round2IndependentVerifier:
    def __init__(self, store: dict[str, dict[str, object]]) -> None:
        self._store = store

    def readback(self, compensation_id: str) -> MaterialReadback:
        return MaterialReadback(compensation_id, dict(self._store[compensation_id]))

    def verify(
        self,
        original_mutation_id: str,
        compensation_readback: MaterialReadback,
    ) -> bool:
        return bool(
            compensation_readback.state.get("compensated") == original_mutation_id
            and compensation_readback.state.get("verified") is True
        )


def _lease(
    *,
    lease_id: str = "lease-sofia",
    ocs: str = "SOFIA",
    actor: str = "SOFIA",
    capability: str = "repo.write",
    authority_ref: str = "authority:sofia",
    trace_ref: str = "trace:round2",
    max_uses: int = 2,
) -> AuthorityLease:
    issued = time() - 1
    return AuthorityLease(
        lease_id=lease_id,
        ocs=ocs,
        capability=capability,
        expires_at=time() + 60,
        actor=actor,
        issued_at=issued,
        not_before=issued,
        scope=(capability,),
        tenant="round2",
        context_ref="context:round2",
        authority_ref=authority_ref,
        policy_snapshot="policy:round2",
        action_binding="repository.write",
        object_ref_or_selector="object:round2",
        trace_ref=trace_ref,
        max_uses=max_uses,
    )


def _proposal(
    *,
    lease_id: str = "lease-sofia",
    actor: str = "SOFIA",
    ocs: str = "SOFIA",
    capability: str = "repo.write",
    authority_ref: str = "authority:sofia",
    trace_id: str = "trace:round2",
    evidence: tuple[Evidence, ...] | None = None,
    risk: RiskLevel = RiskLevel.LOW,
    reversibility: ReversibilityClass = ReversibilityClass.REVERSIBLE,
    action_id: str = "round2-action",
    idem: str = "round2-idem",
) -> ActionProposal:
    return ActionProposal(
        action_id=action_id,
        actor=actor,
        ocs=ocs,
        capability=capability,
        operation="write",
        payload={"value": "round2"},
        risk=risk,
        lease_id=lease_id,
        evidence=(Evidence("e:round2", True, "AGORA"),)
        if evidence is None
        else evidence,
        action_type="repository.write",
        issued_at=time(),
        csp_ref=f"csp://{ocs.lower()}/current",
        object_ref="object:round2",
        tenant="round2",
        context_ref="context:round2",
        scope=(capability,),
        authority_ref=authority_ref,
        policy_snapshot="policy:round2",
        idempotency_key=idem,
        expected_effect="repository_write",
        side_effect_class=SideEffectClass.MATERIAL,
        reversibility_class=reversibility,
        recovery_ref="recovery:round2",
        expires_at=time() + 30,
        evidence_assessment_ref="assessment:round2",
        trace_id=trace_id,
    )


def _runtime(
    *,
    adapter: Round2Adapter | None = None,
    trace: TraceCore | None = None,
    max_uses: int = 2,
    verifier: CompensationVerifier | None = None,
):  # type: ignore[no-untyped-def]
    identities = IdentityConstitutionLoader(
        (
            OCSIdentity(
                "SOFIA",
                "software_engineering",
                "round2",
                frozenset({"repo.write"}),
            ),
        )
    )
    capabilities = CapabilityRegistry()
    capabilities.register("SOFIA", frozenset({"repo.write"}))
    leases = AuthorityLeaseManager()
    leases.issue(_lease(max_uses=max_uses))
    governance = GovernanceEngine(identities, capabilities, EvidenceEngine(), leases)
    broker = ToolBroker()
    bound_adapter = Round2Adapter() if adapter is None else adapter
    broker.register("repo.write", bound_adapter, compensation_verifier=verifier)
    state = StateCore()
    bound_trace = TraceCore() if trace is None else trace
    recovery = RecoveryManager(state)
    runtime = UniversalKernelRuntime(
        governance,
        ThinEffector(broker),
        state,
        bound_trace,
        recovery=recovery,
    )
    return runtime, bound_adapter, leases, state, bound_trace, broker, governance


def test_round2_001_failed_evidence_denies_while_deficit_holds() -> None:
    runtime, adapter, _, _, _, _, governance = _runtime()
    contradicted = _proposal(evidence=(Evidence("false", False, "AGORA"),))
    denied = governance.authorize(contradicted)
    assert denied.decision is AuthorizationDecision.DENY
    assert denied.reason == "evidence_failed"
    execution = runtime.execute(contradicted)
    assert not execution.authorized
    assert execution.governance_decision is AuthorizationDecision.DENY
    assert adapter.mutations == 0

    deficit = _proposal(
        evidence=(Evidence("candidate", True, None),),
        risk=RiskLevel.HIGH,
        action_id="hold",
        idem="hold",
    )
    held = governance.authorize(deficit)
    assert held.decision is AuthorizationDecision.HOLD
    assert held.reason == "independent_assurance_required"


def test_round2_002_statecore_fails_closed_when_ownership_context_omitted() -> None:
    state = StateCore()
    record = StateRecord("s1", "SOFIA", 1, None, {"x": 1}, True)
    with pytest.raises(ValueError, match="state_actor_ocs_required"):
        state.write(record, lambda stored: stored == record)
    assert state.current("SOFIA") is None

    with pytest.raises(ValueError, match="state_namespace_violation"):
        state.write(
            record,
            lambda stored: stored == record,
            actor_ocs_id="AURI",
            target_namespace="state://SOFIA/runtime",
            state_ref="s1",
            authority_context="authority:auri",
        )
    assert state.current("SOFIA") is None


def test_round2_003_registered_adapter_mutation_requires_broker_context() -> None:
    broker = ToolBroker()
    adapter = Round2Adapter()
    broker.register("repo.write", adapter)
    with pytest.raises(ValueError, match="direct_adapter_mutation_prohibited"):
        adapter.mutate("write", {}, "direct")
    assert adapter.mutations == 0
    with pytest.raises(ValueError, match="direct_adapter_resolution_prohibited"):
        broker.adapter_for("repo.write")
    assert broker.material_boundary_claim().structural_denial is False


def test_round2_004_compensation_requires_independent_verification() -> None:
    deceptive = Round2Adapter(fail_readback=True, compensation_verified=True)
    runtime, _, _, _, _, _, _ = _runtime(adapter=deceptive)
    result = runtime.execute(_proposal())
    assert result.authorized and result.effected and not result.proven
    assert deceptive.mutations == 1
    assert deceptive.compensations == 0
    assert result.recovery_receipt is not None
    assert result.recovery_receipt.disposition == "compensation_unverified"
    assert result.recovery_receipt.material_compensated is False
    assert result.recovery_receipt.residual_effect is True

    store: dict[str, dict[str, object]] = {}
    verified = Round2Adapter(
        fail_readback=True,
        compensation_verified=True,
        compensation_store=store,
    )
    verifier = Round2IndependentVerifier(store)
    runtime2, _, _, _, _, _, _ = _runtime(adapter=verified, verifier=verifier)
    result2 = runtime2.execute(_proposal(action_id="verified", idem="verified"))
    assert result2.recovery_receipt is not None
    assert verified.compensations == 1
    assert result2.recovery_receipt.material_compensated is True
    assert result2.recovery_receipt.residual_effect is False


def test_round2_005_snapshot_preserves_usage_and_idempotency_reservations() -> None:
    _, _, leases, _, _, _, governance = _runtime(max_uses=2)
    proposal = _proposal(action_id="first", idem="same")
    authorized = governance.authorize(proposal)
    assert authorized.envelope is not None
    reserved = governance.reserve_authority(authorized.envelope)
    assert reserved.envelope is not None
    assert leases.uses_consumed("lease-sofia") == 1

    key = b"round2-regression-auth-key"
    snapshot = leases.authenticated_snapshot(key)
    reloaded = AuthorityLeaseManager.from_snapshot(snapshot, authentication_key=key)
    replay_ok, replay_reason, replay_index = reloaded.reserve_use(reserved.envelope)
    assert replay_ok
    assert replay_reason == "lease_use_already_reserved"
    assert replay_index == 1
    assert reloaded.uses_consumed("lease-sofia") == 1

    second_envelope = reserved.envelope.__class__(
        **{
            **reserved.envelope.__dict__,
            "action_id": "second",
            "idempotency_key": "second-key",
            "lease_use_index": None,
        }
    )
    second_ok, _, second_index = reloaded.reserve_use(second_envelope)
    assert second_ok and second_index == 2
    assert reloaded.uses_consumed("lease-sofia") == 2

    third_envelope = second_envelope.__class__(
        **{
            **second_envelope.__dict__,
            "action_id": "third",
            "idempotency_key": "third-key",
        }
    )
    third_ok, third_reason, _ = reloaded.reserve_use(third_envelope)
    assert not third_ok
    assert third_reason == "lease_max_uses_exhausted"


def test_round2_006_handoff_cannot_reuse_source_authority_behaviorally() -> None:
    router = HandoffRouter()
    receipt = router.close(
        receipt_id="handoff:round2",
        source_ocs="MÊTIS",
        target_ocs="SYNERGEIA",
        state_ref="state:market",
        context_refs=("context:market",),
        evidence_refs=("evidence:market",),
        source_authority_ref="authority:metis",
    )
    accepted = router.accept(receipt, receiver_ocs="SYNERGEIA")
    assert receipt.source_authority_ref == ""
    assert accepted.executable_authority_ref is None

    identities = IdentityConstitutionLoader(
        (
            OCSIdentity("MÊTIS", "strategy", "round2", frozenset({"repo.write"})),
            OCSIdentity("SYNERGEIA", "gtm", "round2", frozenset({"repo.write"})),
        )
    )
    capabilities = CapabilityRegistry()
    capabilities.register("MÊTIS", frozenset({"repo.write"}))
    capabilities.register("SYNERGEIA", frozenset({"repo.write"}))
    leases = AuthorityLeaseManager()
    leases.issue(
        _lease(
            lease_id="lease-metis",
            ocs="MÊTIS",
            actor="MÊTIS",
            authority_ref="authority:metis",
        )
    )
    governance = GovernanceEngine(identities, capabilities, EvidenceEngine(), leases)
    attempted_reuse = _proposal(
        lease_id="lease-metis",
        actor="SYNERGEIA",
        ocs="SYNERGEIA",
        authority_ref="authority:metis",
        action_id="handoff-reuse",
        idem="handoff-reuse",
    )
    denied = governance.authorize(attempted_reuse)
    assert denied.decision is AuthorizationDecision.DENY
    assert denied.reason == "lease_scope_mismatch"


def test_round2_007_preflight_failure_spends_no_authority_and_no_material_effect(
) -> None:
    trace = TraceCore()
    trace.fail_next_preflight = True
    runtime, adapter, leases, _, _, _, _ = _runtime(trace=trace, max_uses=1)
    result = runtime.execute(_proposal())
    assert result.authorized and not result.effected and not result.proven
    assert result.reason == "trace_preflight_failed"
    assert leases.uses_consumed("lease-sofia") == 0
    assert adapter.mutations == 0
