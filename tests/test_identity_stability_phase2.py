from __future__ import annotations

from time import time

from app.universal_kernel.context_guard import ContextClass, ContextItem
from app.universal_kernel.contracts import (
    ActionProposal,
    Evidence,
    MaterialReadback,
    ReversibilityClass,
    RiskLevel,
    SideEffectClass,
)
from app.universal_kernel.effect_recovery import ThinEffector, ToolBroker
from app.universal_kernel.governance import (
    AuthorityLease,
    AuthorityLeaseManager,
    CapabilityRegistry,
    EvidenceEngine,
    GovernanceEngine,
    IdentityConstitutionLoader,
    OCSIdentity,
)
from app.universal_kernel.identity import IdentityBindingStatus, IdentityKernelGuard
from app.universal_kernel.runtime import UniversalKernelRuntime
from app.universal_kernel.state_trace import StateCore, TraceCore


class Adapter:
    def __init__(self) -> None:
        self.mutations = 0

    def mutate(
        self,
        operation: str,
        payload: dict[str, object],
        idempotency_key: str,
    ) -> str:
        self.mutations += 1
        return f"m-{self.mutations}"

    def readback(self, mutation_id: str) -> MaterialReadback:
        return MaterialReadback(mutation_id, {"ok": True})


def build_runtime() -> tuple[UniversalKernelRuntime, Adapter, IdentityKernelGuard]:
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
    issued = time() - 1
    leases.issue(
        AuthorityLease(
            lease_id="lease:identity-phase2",
            ocs="SOFIA",
            capability="repo.write",
            expires_at=time() + 60,
            actor="SOFIA",
            issued_at=issued,
            not_before=issued,
            scope=("repo.write",),
            tenant="identity",
            context_ref="context:phase2",
            authority_ref="authority:identity",
            policy_snapshot="policy:identity",
            action_binding="repository.write",
            object_ref_or_selector="object:identity",
            trace_ref="trace:identity-phase2",
            max_uses=1,
        )
    )
    governance = GovernanceEngine(
        identities,
        capabilities,
        EvidenceEngine(),
        leases,
    )
    adapter = Adapter()
    broker = ToolBroker()
    broker.register("repo.write", adapter)
    guard = IdentityKernelGuard()
    runtime = UniversalKernelRuntime(
        governance,
        ThinEffector(broker),
        StateCore(),
        TraceCore(),
        identity_guard=guard,
        run_id="run:identity-phase2",
        active_ocs="SOFIA",
        host="ChatGPT",
        session_context="session:identity-phase2",
    )
    return runtime, adapter, guard


def proposal() -> ActionProposal:
    return ActionProposal(
        action_id="action:identity-phase2",
        actor="SOFIA",
        ocs="SOFIA",
        capability="repo.write",
        operation="write",
        payload={"value": 1},
        risk=RiskLevel.LOW,
        lease_id="lease:identity-phase2",
        evidence=(Evidence("evidence:identity", True, "AGORA"),),
        action_type="repository.write",
        issued_at=time(),
        csp_ref="csp://sofia/current",
        object_ref="object:identity",
        tenant="identity",
        context_ref="context:phase2",
        scope=("repo.write",),
        authority_ref="authority:identity",
        policy_snapshot="policy:identity",
        idempotency_key="idem:identity-phase2",
        expected_effect="repository_write",
        side_effect_class=SideEffectClass.MATERIAL,
        reversibility_class=ReversibilityClass.REVERSIBLE,
        recovery_ref="recovery:identity",
        expires_at=time() + 30,
        evidence_assessment_ref="assessment:identity",
        trace_id="trace:identity-phase2",
    )


def test_foreign_autobiographical_context_blocks_effect_in_kernel() -> None:
    runtime, adapter, guard = build_runtime()
    runtime.replace_context(
        (
            ContextItem(
                context_ref="context:foreign-sofia",
                context_class=ContextClass.FOREIGN_OCS_CONTEXT,
                source_ocs="NÓESIS",
                autobiographical=True,
            ),
        )
    )
    result = runtime.execute(proposal())
    assert not result.authorized
    assert result.reason == "foreign_ocs_context_rejected"
    assert adapter.mutations == 0
    binding = guard.binding_for("run:identity-phase2")
    assert binding is not None
    assert binding.status is IdentityBindingStatus.HOLD


def test_current_run_context_allows_identity_bound_operation() -> None:
    runtime, adapter, guard = build_runtime()
    runtime.replace_context(
        (
            ContextItem(
                context_ref="context:current-sofia",
                context_class=ContextClass.CURRENT_RUN_CONTEXT,
                source_ocs="SOFIA",
            ),
        )
    )
    result = runtime.execute(proposal())
    assert result.proven
    assert adapter.mutations == 1
    assert runtime.institutional_run
    assert guard.audit_log.chain_is_valid()
    assert any(
        event.event_type == "CONTEXT_SANITATION"
        for event in guard.audit_log.events
    )


def test_unbound_runtime_is_noninstitutional_compatibility_surface() -> None:
    identities = IdentityConstitutionLoader(())
    capabilities = CapabilityRegistry()
    leases = AuthorityLeaseManager()
    runtime = UniversalKernelRuntime(
        GovernanceEngine(identities, capabilities, EvidenceEngine(), leases),
        ThinEffector(ToolBroker()),
        StateCore(),
        TraceCore(),
    )
    assert not runtime.institutional_run
