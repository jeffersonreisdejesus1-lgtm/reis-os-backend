from __future__ import annotations

from dataclasses import replace
from time import time

import pytest

from app.universal_kernel.contracts import (
    ActionProposal,
    AuthorizationDecision,
    Evidence,
    LPEUpdate,
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
from app.universal_kernel.ports import (
    HandoffRouter,
    LPEPort,
    PIActivation,
    PIActivationRegistry,
)
from app.universal_kernel.runtime import UniversalKernelRuntime
from app.universal_kernel.state_trace import StateCore, TraceCore


class FakeAdapter:
    def __init__(self) -> None:
        self.mutations = 0
        self._mutation_by_key: dict[str, str] = {}

    def mutate(
        self,
        operation: str,
        payload: dict[str, object],
        idempotency_key: str,
    ) -> str:
        existing = self._mutation_by_key.get(idempotency_key)
        if existing is not None:
            return existing
        self.mutations += 1
        mutation_id = f"m-{self.mutations}"
        self._mutation_by_key[idempotency_key] = mutation_id
        return mutation_id

    def readback(self, mutation_id: str) -> MaterialReadback:
        return MaterialReadback(mutation_id, {"ok": True})


class ObservingBroker(ToolBroker):
    def __init__(self, leases: AuthorityLeaseManager) -> None:
        super().__init__()
        self._leases = leases
        self.reservation_seen_before_resolution = False

    def adapter_for(self, capability: str):  # type: ignore[no-untyped-def]
        self.reservation_seen_before_resolution = (
            self._leases.uses_consumed("lease-1") == 1
        )
        return super().adapter_for(capability)


def build_runtime(
    *,
    lease_expires_at: float | None = None,
    max_uses: int = 1,
    observing_broker: bool = False,
):  # type: ignore[no-untyped-def]
    identities = IdentityConstitutionLoader(
        (
            OCSIdentity(
                ocs="SOFIA",
                specialty="software_engineering",
                constitution_version="r1",
                allowed_capabilities=frozenset({"repo.write"}),
            ),
        )
    )
    capabilities = CapabilityRegistry()
    capabilities.register("SOFIA", frozenset({"repo.write"}))
    leases = AuthorityLeaseManager()
    expires_at = time() + 60 if lease_expires_at is None else lease_expires_at
    leases.issue(
        AuthorityLease(
            lease_id="lease-1",
            ocs="SOFIA",
            capability="repo.write",
            expires_at=expires_at,
            scope=("repo.write", "repo.read"),
            tenant="tenant-1",
            context_ref="context-1",
            authority_ref="authority-1",
            policy_snapshot="policy-r1",
            max_uses=max_uses,
        )
    )
    governance = GovernanceEngine(
        identities,
        capabilities,
        EvidenceEngine(),
        leases,
    )
    broker: ToolBroker = (
        ObservingBroker(leases) if observing_broker else ToolBroker()
    )
    adapter = FakeAdapter()
    broker.register("repo.write", adapter)
    state = StateCore()
    trace = TraceCore()
    runtime = UniversalKernelRuntime(
        governance,
        ThinEffector(broker),
        state,
        trace,
    )
    return runtime, adapter, leases, state, trace, broker, governance


def proposal(
    *,
    evidence: tuple[Evidence, ...] | None = None,
    risk: RiskLevel = RiskLevel.LOW,
    action_id: str = "a-1",
    idempotency_key: str = "idem-1",
    scope: tuple[str, ...] = ("repo.write",),
    expires_at: float | None = None,
) -> ActionProposal:
    bound_evidence = (
        (Evidence("e-1", True, "SYNESIS"),)
        if evidence is None
        else evidence
    )
    return ActionProposal(
        action_id=action_id,
        actor="SOFIA",
        ocs="SOFIA",
        capability="repo.write",
        operation="write",
        payload={"value": 1},
        risk=risk,
        lease_id="lease-1",
        evidence=bound_evidence,
        csp_ref="CSP_SOFIA",
        object_ref="object:r1a",
        tenant="tenant-1",
        context_ref="context-1",
        scope=scope,
        authority_ref="authority-1",
        policy_snapshot="policy-r1",
        idempotency_key=idempotency_key,
        expected_effect="repository_write",
        side_effect_class=SideEffectClass.MATERIAL,
        reversibility_class=ReversibilityClass.REVERSIBLE,
        recovery_ref="recovery:r1a",
        expires_at=time() + 30 if expires_at is None else expires_at,
        evidence_assessment_ref="assessment:r1a",
        trace_id=f"trace:{action_id}",
    )


def test_deny_causes_zero_mutation() -> None:
    runtime, adapter, _, _, _, _, _ = build_runtime()
    failed = (Evidence("e", False, "SYNESIS"),)
    result = runtime.execute(proposal(evidence=failed))
    assert not result.authorized
    assert adapter.mutations == 0


def test_incomplete_action_envelope_causes_zero_mutation() -> None:
    runtime, adapter, _, _, _, _, _ = build_runtime()
    incomplete = replace(proposal(), authority_ref=None)
    result = runtime.execute(incomplete)
    assert not result.authorized
    assert result.reason.startswith("action_envelope_incomplete")
    assert adapter.mutations == 0


def test_authorized_action_envelope_is_materially_complete() -> None:
    _, _, _, _, _, _, governance = build_runtime(max_uses=2)
    result = governance.authorize(proposal())
    assert result.decision is AuthorizationDecision.ALLOW
    assert result.envelope is not None
    envelope = result.envelope
    assert envelope.csp_ref == "CSP_SOFIA"
    assert envelope.object_ref == "object:r1a"
    assert envelope.tenant == "tenant-1"
    assert envelope.context_ref == "context-1"
    assert envelope.scope == ("repo.write",)
    assert envelope.valid_scope is True
    assert envelope.authority_ref == "authority-1"
    assert envelope.policy_snapshot == "policy-r1"
    assert envelope.idempotency_key == "idem-1"
    assert envelope.expected_effect == "repository_write"
    assert envelope.side_effect_class is SideEffectClass.MATERIAL
    assert envelope.reversibility_class is ReversibilityClass.REVERSIBLE
    assert envelope.recovery_ref == "recovery:r1a"
    assert envelope.evidence_assessment_ref == "assessment:r1a"
    assert envelope.max_uses == 2
    assert envelope.trace_id == "trace:a-1"


def test_expired_lease_causes_zero_mutation() -> None:
    runtime, adapter, _, _, _, _, _ = build_runtime(lease_expires_at=time() - 1)
    result = runtime.execute(proposal())
    assert not result.authorized
    assert result.reason == "lease_expired"
    assert adapter.mutations == 0


def test_revoked_lease_causes_zero_mutation() -> None:
    runtime, adapter, leases, _, _, _, _ = build_runtime()
    leases.revoke("lease-1")
    result = runtime.execute(proposal())
    assert not result.authorized
    assert result.reason == "lease_revoked"
    assert adapter.mutations == 0


def test_revocation_between_authorize_and_reserve_blocks_effect_path() -> None:
    _, _, leases, _, _, _, governance = build_runtime()
    authorized = governance.authorize(proposal())
    assert authorized.envelope is not None
    leases.revoke("lease-1")
    reservation = governance.reserve_authority(authorized.envelope)
    assert reservation.decision is AuthorizationDecision.DENY
    assert reservation.reason == "lease_revoked"
    assert leases.uses_consumed("lease-1") == 0


def test_scope_binding_mismatch_causes_zero_mutation() -> None:
    runtime, adapter, _, _, _, _, _ = build_runtime()
    result = runtime.execute(proposal(scope=("secrets.write",)))
    assert not result.authorized
    assert result.reason == "lease_scope_mismatch"
    assert adapter.mutations == 0


def test_lease_use_is_consumed_before_adapter_resolution() -> None:
    runtime, adapter, leases, _, _, broker, _ = build_runtime(observing_broker=True)
    result = runtime.execute(proposal())
    assert result.proven
    assert adapter.mutations == 1
    assert leases.uses_consumed("lease-1") == 1
    assert isinstance(broker, ObservingBroker)
    assert broker.reservation_seen_before_resolution is True


def test_max_uses_blocks_second_distinct_action_before_mutation() -> None:
    runtime, adapter, leases, _, _, _, _ = build_runtime(max_uses=1)
    first = runtime.execute(proposal(action_id="a-1", idempotency_key="idem-1"))
    second = runtime.execute(proposal(action_id="a-2", idempotency_key="idem-2"))
    assert first.proven
    assert not second.authorized
    assert second.reason == "lease_max_uses_exhausted"
    assert leases.uses_consumed("lease-1") == 1
    assert adapter.mutations == 1


def test_idempotent_replay_does_not_consume_or_mutate_twice() -> None:
    runtime, adapter, leases, _, _, _, _ = build_runtime(max_uses=1)
    first = runtime.execute(proposal())
    replay = runtime.execute(proposal())
    assert first == replay
    assert leases.uses_consumed("lease-1") == 1
    assert adapter.mutations == 1


def test_idempotency_key_reuse_for_different_action_is_denied() -> None:
    runtime, adapter, leases, _, _, _, _ = build_runtime(max_uses=2)
    first = runtime.execute(proposal(action_id="a-1", idempotency_key="shared"))
    conflict = runtime.execute(proposal(action_id="a-2", idempotency_key="shared"))
    assert first.proven
    assert not conflict.authorized
    assert conflict.reason == "idempotency_conflict"
    assert leases.uses_consumed("lease-1") == 1
    assert adapter.mutations == 1


def test_high_risk_evidence_failure_blocks_effect() -> None:
    runtime, adapter, _, _, _, _, _ = build_runtime()
    evidence = (Evidence("e", True),)
    result = runtime.execute(
        proposal(evidence=evidence, risk=RiskLevel.HIGH)
    )
    assert not result.authorized
    assert result.reason == "independent_assurance_required"
    assert adapter.mutations == 0


def test_self_assurance_is_denied() -> None:
    runtime, adapter, _, _, _, _, _ = build_runtime()
    evidence = (Evidence("e", True, "SOFIA"),)
    result = runtime.execute(proposal(evidence=evidence))
    assert not result.authorized
    assert result.reason == "self_assurance_denied"
    assert adapter.mutations == 0


def test_state_write_has_version_and_predecessor() -> None:
    state = StateCore()
    first = StateRecord("s1", "SOFIA", 1, None, {"v": 1}, True)
    state.write(first, lambda stored: stored == first)
    second = StateRecord("s2", "SOFIA", 2, "s1", {"v": 2}, True)
    state.write(second, lambda stored: stored == second)
    assert state.current("SOFIA") == second


def test_recovery_restores_verified_state() -> None:
    state = StateCore()
    checkpoint = VerifiedCheckpoint(
        "cp-1",
        StateRecord("old", "SOFIA", 1, None, {"safe": True}, True),
    )
    restored = RecoveryManager(state).restore(checkpoint)
    assert restored.verified
    assert restored.payload == {"safe": True}


def test_unverified_checkpoint_is_rejected() -> None:
    state = StateCore()
    checkpoint = VerifiedCheckpoint(
        "cp-1",
        StateRecord("old", "SOFIA", 1, None, {}, False),
    )
    with pytest.raises(ValueError, match="verified_checkpoint_required"):
        RecoveryManager(state).restore(checkpoint)


def test_trace_break_returns_not_proven() -> None:
    runtime, adapter, leases, _, trace, _, _ = build_runtime()
    trace.fail_next_append = True
    result = runtime.execute(proposal())
    assert not result.proven
    assert not result.effected
    assert adapter.mutations == 0
    assert leases.uses_consumed("lease-1") == 1


def test_handoff_transfers_no_authority() -> None:
    receipt = HandoffRouter().close(
        receipt_id="h-1",
        source_ocs="SOFIA",
        target_ocs="AGORA",
        state_ref="s-1",
    )
    assert receipt.target_ocs == "AGORA"
    assert receipt.authority_transferred is False


def test_lpe_cannot_expand_authority_or_constitution() -> None:
    port = LPEPort()
    with pytest.raises(ValueError, match="authority_expansion"):
        port.validate(LPEUpdate("SOFIA", "build", "x", changes_authority=True))
    with pytest.raises(ValueError, match="constitution_mutation"):
        port.validate(LPEUpdate("SOFIA", "build", "x", changes_constitution=True))


def test_cross_ocs_autobiography_import_is_prohibited() -> None:
    update = LPEUpdate(
        "SOFIA",
        "build",
        "x",
        imports_autobiography_from_ocs="IRIS",
    )
    with pytest.raises(ValueError, match="cross_ocs_autobiography"):
        LPEPort().validate(update)


def test_pi_activation_is_ocs_local() -> None:
    registry = PIActivationRegistry()
    registry.set(PIActivation("pi-1", "SOFIA", True))
    assert registry.is_active("pi-1", "SOFIA")
    assert not registry.is_active("pi-1", "IRIS")


def test_authorized_path_effects_and_readbacks() -> None:
    runtime, adapter, leases, state, trace, _, _ = build_runtime()
    result = runtime.execute(proposal())
    assert result.authorized and result.effected and result.proven
    assert adapter.mutations == 1
    assert leases.uses_consumed("lease-1") == 1
    assert result.readback is not None
    assert state.current("SOFIA") is not None
    assert trace.chain_is_valid()


def test_lateral_effect_route_exists_false() -> None:
    registry = CapabilityRegistry()
    evidence = EvidenceEngine()
    assert not hasattr(registry, "execute")
    assert not hasattr(evidence, "execute")
    assert not hasattr(HandoffRouter(), "execute")
