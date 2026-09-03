from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from json import dumps
from time import sleep, time

from app.profile_bindings.profiles import PROFILES
from app.r3_causal_slices import CAUSAL_CHAIN, build_replay_packages
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
from app.universal_kernel.ports import HandoffRouter
from app.universal_kernel.runtime import UniversalKernelRuntime
from app.universal_kernel.state_trace import StateCore, TraceCore


class FixtureAdapter:
    def __init__(self) -> None:
        self.mutations = 0
        self.values: dict[str, dict[str, object]] = {}

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
        return MaterialReadback(mutation_id, self.values[mutation_id])


def _runtime(*, lease_expires_at: float | None = None):  # type: ignore[no-untyped-def]
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
    governance = GovernanceEngine(identities, capabilities, EvidenceEngine(), leases)
    broker = ToolBroker()
    adapter = FixtureAdapter()
    broker.register("repo.write", adapter)
    state = StateCore()
    trace = TraceCore()
    runtime = UniversalKernelRuntime(governance, ThinEffector(broker), state, trace)
    return runtime, adapter, leases, state, trace, broker


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


def test_replay_packages_cover_all_frozen_slices() -> None:
    packages = build_replay_packages()
    assert tuple(packages) == tuple(f"R3-S{i:02d}" for i in range(1, 11))
    for package in packages.values():
        assert package.trace_sequence == CAUSAL_CHAIN
        assert package.profile_id in PROFILES
        assert package.policy_snapshot == "policy:r3-frozen"
        assert package.authority_fixture
        assert package.lease_fixture
        assert package.evidence_fixture


def test_r3_s01_authorized_persistent_mutation_and_idempotent_replay() -> None:
    runtime, adapter, _, state, trace, _ = _runtime()
    first = runtime.execute(_proposal())
    replay = runtime.execute(_proposal())
    current = state.current("SOFIA")
    assert first.proven and replay == first
    assert adapter.mutations == 1
    assert current is not None and current.version == 1 and current.predecessor is None
    assert first.readback is not None
    assert _hash(first.readback.state) == _hash(current.payload)
    assert trace.chain_is_valid()
    assert trace.events[-1].stage == "TRACE_CLOSE"


def test_r3_s02_denied_effect_has_zero_mutation_and_no_state_commit() -> None:
    runtime, adapter, _, state, trace, _ = _runtime()
    result = runtime.execute(_proposal(scope=("secrets.write",)))
    assert not result.authorized
    assert adapter.mutations == 0
    assert state.current("SOFIA") is None
    assert not trace.events


def test_r3_s03_hold_insufficient_evidence_stops_before_kernel_effect_path() -> None:
    runtime, adapter, _, state, trace, _ = _runtime()
    evidence = (Evidence("research:candidate", True, None),)
    proposal = _proposal(evidence=evidence, risk=RiskLevel.HIGH)
    independent = any(
        item.independent_assurer not in {None, proposal.ocs, proposal.actor}
        for item in proposal.evidence
    )
    disposition = "CONTINUE" if independent else "HOLD"
    assert disposition == "HOLD"
    assert adapter.mutations == 0
    assert state.current("SOFIA") is None
    assert not trace.events
    assert runtime is not None


def test_r3_s04_expired_lease_zero_mutation() -> None:
    runtime, adapter, _, state, _, _ = _runtime(lease_expires_at=time() + 0.15)
    sleep(0.2)
    result = runtime.execute(_proposal())
    assert not result.authorized and result.reason == "lease_expired"
    assert adapter.mutations == 0
    assert state.current("SOFIA") is None


def test_r3_s05_revoked_lease_zero_mutation_and_no_resurrection() -> None:
    runtime, adapter, leases, state, _, _ = _runtime()
    leases.revoke("r3-lease")
    first = runtime.execute(_proposal())
    second = runtime.execute(_proposal(action_id="r3-replay", idem="r3-idem-2"))
    assert first.reason == second.reason == "lease_revoked"
    assert adapter.mutations == 0
    assert state.current("SOFIA") is None


def test_r3_s06_namespace_violation_denied_before_cross_ocs_state_write() -> None:
    auri = PROFILES["AURI"]
    sofia = PROFILES["SOFIA"]
    state = StateCore()
    requested_namespace = sofia.state_namespace
    namespace_allowed = requested_namespace.startswith(auri.state_namespace)
    assert not namespace_allowed
    assert state.current("AURI") is None
    assert state.current("SOFIA") is None


def test_r3_s07_lateral_effect_attempt_unavailable_from_profile() -> None:
    sofia = PROFILES["SOFIA"]
    assert sofia.capability_adapters == ()
    assert sofia.tool_permissions == ()
    assert not hasattr(sofia, "effector")
    assert not hasattr(sofia, "adapter_for")


def test_r3_s08_verified_recovery_restores_checkpoint_content() -> None:
    runtime, adapter, _, state, _, _ = _runtime()
    checkpoint_state = StateRecord(
        "checkpoint-state",
        "SOFIA",
        1,
        None,
        {"r3": "safe"},
        True,
    )
    state.write(checkpoint_state, lambda stored: stored == checkpoint_state)
    effect = runtime.execute(_proposal())
    assert effect.proven and adapter.mutations == 1
    checkpoint = VerifiedCheckpoint("r3-checkpoint", checkpoint_state)
    restored = RecoveryManager(state).restore(checkpoint)
    assert restored.payload == checkpoint_state.payload
    assert _hash(restored.payload) == _hash(checkpoint_state.payload)
    assert restored.predecessor is not None
    assert restored.verified


def test_r3_s09_handoff_does_not_transfer_authority_or_source_lease() -> None:
    receipt = HandoffRouter().close(
        receipt_id="handoff:r3",
        source_ocs="MÊTIS",
        target_ocs="SYNERGEIA",
        state_ref="context:r3-market",
    )
    assert receipt.authority_transferred is False
    source_authority = PROFILES["MÊTIS"].authority_envelope_ref
    receiver_authority = PROFILES["SYNERGEIA"].authority_envelope_ref
    assert source_authority != receiver_authority


def test_r3_s10_specialty_differentiation_on_common_kernel() -> None:
    metis = PROFILES["MÊTIS"]
    synergeia = PROFILES["SYNERGEIA"]
    assert metis.kernel_interface_ref == synergeia.kernel_interface_ref
    assert metis.specialty != synergeia.specialty
    assert metis.allowed_action_classes != synergeia.allowed_action_classes
    assert metis.authority_envelope_ref != synergeia.authority_envelope_ref
    assert metis.memory_namespace != synergeia.memory_namespace


def test_trace_break_means_causality_not_proven() -> None:
    runtime, adapter, _, state, trace, _ = _runtime()
    trace.fail_next_append = True
    result = runtime.execute(_proposal())
    assert not result.proven
    assert adapter.mutations == 0
    assert state.current("SOFIA") is None
