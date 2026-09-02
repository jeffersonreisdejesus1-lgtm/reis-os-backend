from __future__ import annotations

from time import time

import pytest

from app.universal_kernel.contracts import (
    ActionProposal,
    Evidence,
    LPEUpdate,
    MaterialReadback,
    RiskLevel,
    StateRecord,
    VerifiedCheckpoint,
)
from app.universal_kernel.effect_recovery import RecoveryManager, ThinEffector, ToolBroker
from app.universal_kernel.governance import (
    AuthorityLease,
    AuthorityLeaseManager,
    CapabilityRegistry,
    EvidenceEngine,
    GovernanceEngine,
    IdentityConstitutionLoader,
    OCSIdentity,
)
from app.universal_kernel.ports import HandoffRouter, LPEPort, PIActivation, PIActivationRegistry
from app.universal_kernel.runtime import UniversalKernelRuntime
from app.universal_kernel.state_trace import StateCore, TraceCore


class FakeAdapter:
    def __init__(self) -> None:
        self.mutations = 0

    def mutate(self, operation: str, payload: dict[str, object]) -> str:
        self.mutations += 1
        return f"m-{self.mutations}"

    def readback(self, mutation_id: str) -> MaterialReadback:
        return MaterialReadback(mutation_id, {"ok": True})


def build_runtime(*, lease_expires_at: float | None = None):  # type: ignore[no-untyped-def]
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
    leases.issue(
        AuthorityLease(
            lease_id="lease-1",
            ocs="SOFIA",
            capability="repo.write",
            expires_at=time() + 60 if lease_expires_at is None else lease_expires_at,
        )
    )
    governance = GovernanceEngine(identities, capabilities, EvidenceEngine(), leases)
    broker = ToolBroker()
    adapter = FakeAdapter()
    broker.register("repo.write", adapter)
    state = StateCore()
    trace = TraceCore()
    runtime = UniversalKernelRuntime(governance, ThinEffector(broker), state, trace)
    return runtime, adapter, leases, state, trace


def proposal(*, evidence: tuple[Evidence, ...] | None = None, risk: RiskLevel = RiskLevel.LOW) -> ActionProposal:
    return ActionProposal(
        action_id="a-1",
        actor="SOFIA",
        ocs="SOFIA",
        capability="repo.write",
        operation="write",
        payload={"value": 1},
        risk=risk,
        lease_id="lease-1",
        evidence=(Evidence("e-1", True, "SYNESIS"),) if evidence is None else evidence,
    )


def test_deny_causes_zero_mutation() -> None:
    runtime, adapter, _, _, _ = build_runtime()
    result = runtime.execute(proposal(evidence=(Evidence("e", False, "SYNESIS"),)))
    assert not result.authorized
    assert adapter.mutations == 0


def test_expired_lease_causes_zero_mutation() -> None:
    runtime, adapter, _, _, _ = build_runtime(lease_expires_at=time() - 1)
    result = runtime.execute(proposal())
    assert not result.authorized
    assert result.reason == "lease_expired"
    assert adapter.mutations == 0


def test_revoked_lease_causes_zero_mutation() -> None:
    runtime, adapter, leases, _, _ = build_runtime()
    leases.revoke("lease-1")
    result = runtime.execute(proposal())
    assert not result.authorized
    assert result.reason == "lease_revoked"
    assert adapter.mutations == 0


def test_high_risk_evidence_failure_blocks_effect() -> None:
    runtime, adapter, _, _, _ = build_runtime()
    result = runtime.execute(proposal(evidence=(Evidence("e", True),), risk=RiskLevel.HIGH))
    assert not result.authorized
    assert result.reason == "independent_assurance_required"
    assert adapter.mutations == 0


def test_self_assurance_is_denied() -> None:
    runtime, adapter, _, _, _ = build_runtime()
    result = runtime.execute(proposal(evidence=(Evidence("e", True, "SOFIA"),)))
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
    runtime, adapter, _, _, trace = build_runtime()
    trace.fail_next_append = True
    result = runtime.execute(proposal())
    assert not result.proven
    assert adapter.mutations == 0


def test_handoff_transfers_no_authority() -> None:
    receipt = HandoffRouter().close(
        receipt_id="h-1", source_ocs="SOFIA", target_ocs="AGORA", state_ref="s-1"
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
    with pytest.raises(ValueError, match="cross_ocs_autobiography"):
        LPEPort().validate(
            LPEUpdate("SOFIA", "build", "x", imports_autobiography_from_ocs="IRIS")
        )


def test_pi_activation_is_ocS_local() -> None:
    registry = PIActivationRegistry()
    registry.set(PIActivation("pi-1", "SOFIA", True))
    assert registry.is_active("pi-1", "SOFIA")
    assert not registry.is_active("pi-1", "IRIS")


def test_authorized_path_effects_and_readbacks() -> None:
    runtime, adapter, _, state, trace = build_runtime()
    result = runtime.execute(proposal())
    assert result.authorized and result.effected and result.proven
    assert adapter.mutations == 1
    assert result.readback is not None
    assert state.current("SOFIA") is not None
    assert trace.chain_is_valid()


def test_lateral_effect_route_exists_false() -> None:
    registry = CapabilityRegistry()
    evidence = EvidenceEngine()
    assert not hasattr(registry, "execute")
    assert not hasattr(evidence, "execute")
    assert not hasattr(HandoffRouter(), "execute")
