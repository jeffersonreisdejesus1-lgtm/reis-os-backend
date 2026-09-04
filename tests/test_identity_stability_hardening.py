from __future__ import annotations

from dataclasses import replace
from time import time

import pytest

from app.universal_kernel.context_guard import (
    ContextClass,
    ContextItem,
    ContextSanitizer,
)
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
from app.universal_kernel.handoff import HandoffIdentityGate
from app.universal_kernel.identity import (
    IdentityAuditLog,
    IdentityBindingStatus,
    IdentityKernelGuard,
    IdentityRecheckTrigger,
)
from app.universal_kernel.runtime import UniversalKernelRuntime
from app.universal_kernel.state_trace import StateCore, TraceCore


class IdentityFixtureAdapter:
    def __init__(self, *, on_mutate=None):  # type: ignore[no-untyped-def]
        self.mutations = 0
        self._on_mutate = on_mutate

    def mutate(
        self,
        operation: str,
        payload: dict[str, object],
        idempotency_key: str,
    ) -> str:
        self.mutations += 1
        if self._on_mutate is not None:
            self._on_mutate()
        return f"identity-mutation-{self.mutations}"

    def readback(self, mutation_id: str) -> MaterialReadback:
        return MaterialReadback(mutation_id, {"identity": "stable"})


def _proposal(*, ocs: str = "SOFIA") -> ActionProposal:
    return ActionProposal(
        action_id="identity-action",
        actor=ocs,
        ocs=ocs,
        capability="repo.write",
        operation="write",
        payload={"value": 1},
        risk=RiskLevel.LOW,
        lease_id="identity-lease",
        evidence=(Evidence("identity-evidence", True, "AGORA"),),
        action_type="repository.write",
        issued_at=time(),
        csp_ref="csp://sofia/current",
        object_ref="object:identity",
        tenant="identity",
        context_ref="context:identity",
        scope=("repo.write",),
        authority_ref="authority:identity",
        policy_snapshot="policy:identity",
        idempotency_key="identity-idem",
        expected_effect="repository_write",
        side_effect_class=SideEffectClass.MATERIAL,
        reversibility_class=ReversibilityClass.REVERSIBLE,
        recovery_ref="recovery:identity",
        expires_at=time() + 30,
        evidence_assessment_ref="assessment:identity",
        trace_id="trace:identity",
    )


def _runtime(*, guard: IdentityKernelGuard, adapter: IdentityFixtureAdapter):
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
            lease_id="identity-lease",
            ocs="SOFIA",
            capability="repo.write",
            expires_at=time() + 60,
            actor="SOFIA",
            issued_at=issued,
            not_before=issued,
            scope=("repo.write",),
            tenant="identity",
            context_ref="context:identity",
            authority_ref="authority:identity",
            policy_snapshot="policy:identity",
            action_binding="repository.write",
            object_ref_or_selector="object:identity",
            trace_ref="trace:identity",
            max_uses=2,
        )
    )
    governance = GovernanceEngine(
        identities,
        capabilities,
        EvidenceEngine(),
        leases,
    )
    broker = ToolBroker()
    broker.register("repo.write", adapter)
    state = StateCore()
    trace = TraceCore()
    runtime = UniversalKernelRuntime(
        governance,
        ThinEffector(broker),
        state,
        trace,
        identity_guard=guard,
        run_id="run:sofia",
        active_ocs="SOFIA",
        host="ChatGPT",
        session_context="session:identity-test",
    )
    return runtime, state


def test_boot_binds_identity_from_profile_and_revalidates() -> None:
    guard = IdentityKernelGuard()
    runtime, _ = _runtime(guard=guard, adapter=IdentityFixtureAdapter())
    binding = guard.binding_for("run:sofia")
    assert runtime.identity_guard_enabled
    assert binding is not None
    assert binding.ocs_id == "SOFIA"
    assert binding.institution == "REIS OS"
    assert binding.host == "ChatGPT"
    assert binding.state_namespace.startswith("state://sofia/")
    assert binding.memory_namespace.startswith("memory://sofia/")
    assert binding.status is IdentityBindingStatus.VALID
    assert guard.audit_log.chain_is_valid()


def test_missing_identity_binding_fails_closed() -> None:
    guard = IdentityKernelGuard()
    with pytest.raises(ValueError, match="identity_binding_required"):
        guard.require_valid(
            run_id="missing",
            expected_ocs="SOFIA",
            trigger=IdentityRecheckTrigger.PRE_ACTION,
        )


def test_wrong_ocs_context_is_denied_before_material_effect() -> None:
    guard = IdentityKernelGuard()
    adapter = IdentityFixtureAdapter()
    runtime, state = _runtime(guard=guard, adapter=adapter)
    result = runtime.execute(_proposal(ocs="ÁGORA"))
    assert not result.authorized
    assert result.reason == "active_ocs_identity_mismatch"
    assert adapter.mutations == 0
    assert state.current("ÁGORA") is None
    binding = guard.binding_for("run:sofia")
    assert binding is not None and binding.status is IdentityBindingStatus.HOLD


def test_host_substitution_creates_identity_hold() -> None:
    guard = IdentityKernelGuard()
    guard.bind_active_identity(
        run_id="run:host",
        ocs_id="NÓESIS",
        host="ChatGPT",
        session_context="session:host",
    )
    result = guard.revalidate(
        run_id="run:host",
        expected_ocs="NÓESIS",
        trigger=IdentityRecheckTrigger.HOST_REFERENCE,
        host="Claude",
    )
    assert not result.valid
    assert result.reason == "host_identity_context_mismatch"
    assert result.binding is not None
    assert result.binding.status is IdentityBindingStatus.HOLD


def test_foreign_autobiographical_context_is_rejected_not_imported() -> None:
    sanitizer = ContextSanitizer()
    assessment = sanitizer.assess(
        "NÓESIS",
        (
            ContextItem(
                "ctx:foreign",
                ContextClass.FOREIGN_OCS_CONTEXT,
                source_ocs="SOFIA",
                autobiographical=True,
            ),
            ContextItem(
                "ctx:current",
                ContextClass.CURRENT_RUN_CONTEXT,
                source_ocs="NÓESIS",
            ),
        ),
    )
    assert assessment.accepted_refs == ("ctx:current",)
    assert assessment.rejected_refs == ("ctx:foreign",)
    assert assessment.identity_conflict
    assert "foreign_ocs_context_rejected" in assessment.reasons


def test_conversational_context_without_identity_metadata_is_noncanonical() -> None:
    sanitizer = ContextSanitizer()
    classification = sanitizer.classify(
        active_ocs="NÓESIS",
        source_ocs=None,
    )
    assert classification is ContextClass.NON_CANONICAL_CONVERSATIONAL_CONTEXT


def test_identity_drift_after_effect_blocks_persist_and_marks_residual_effect() -> None:
    guard = IdentityKernelGuard()

    def drift_after_effect() -> None:
        guard.hold("run:sofia", "injected_long_context_drift")

    adapter = IdentityFixtureAdapter(on_mutate=drift_after_effect)
    runtime, state = _runtime(guard=guard, adapter=adapter)
    result = runtime.execute(_proposal())
    assert result.authorized
    assert result.effected
    assert not result.proven
    assert result.residual_effect
    assert result.reason == "injected_long_context_drift"
    assert adapter.mutations == 1
    assert state.current("SOFIA") is None


def test_identity_log_is_hash_chained_and_cold_start_recoverable(tmp_path) -> None:
    path = tmp_path / "hazel-identity.jsonl"
    first_log = IdentityAuditLog(path)
    first_guard = IdentityKernelGuard(audit_log=first_log)
    original = first_guard.bind_active_identity(
        run_id="run:recover",
        ocs_id="AURI",
        host="ChatGPT",
        session_context="session:recover",
    )
    assert first_log.chain_is_valid()

    second_log = IdentityAuditLog(path)
    second_guard = IdentityKernelGuard(audit_log=second_log)
    recovered = second_guard.recover_state("run:recover")
    assert recovered.ocs_id == original.ocs_id
    assert recovered.identity_ref == original.identity_ref
    assert recovered.state_namespace == original.state_namespace
    assert recovered.memory_namespace == original.memory_namespace
    assert second_log.chain_is_valid()


def test_identity_hold_cannot_be_bypassed_by_cold_start_recovery(tmp_path) -> None:
    path = tmp_path / "hazel-held-identity.jsonl"
    log = IdentityAuditLog(path)
    guard = IdentityKernelGuard(audit_log=log)
    guard.bind_active_identity(
        run_id="run:held",
        ocs_id="NÓESIS",
        host="ChatGPT",
        session_context="session:held",
    )
    guard.hold("run:held", "identity_conflict")

    recovered_log = IdentityAuditLog(path)
    recovered_guard = IdentityKernelGuard(audit_log=recovered_log)
    with pytest.raises(ValueError, match="identity_hold_rebind_required"):
        recovered_guard.recover_state("run:held")


def test_handoff_requires_sender_binding_and_receiver_gets_fresh_identity() -> None:
    sender_guard = IdentityKernelGuard()
    sender_guard.bind_active_identity(
        run_id="run:sender",
        ocs_id="NÓESIS",
        host="ChatGPT",
        session_context="session:sender",
    )
    gate = HandoffIdentityGate()
    receipt = gate.issue(
        guard=sender_guard,
        run_id="run:sender",
        handoff_id="handoff:1",
        sender_ocs="NÓESIS",
        sender_host="ChatGPT",
        receiver_ocs="SOFIA",
        receiver_host_if_known="ChatGPT",
        object_ref="object:handoff",
        authorized_next_scope=("software_implementation",),
        authority_ref="authority:source-only",
    )
    assert not receipt.identity_transfer
    assert not receipt.authority_transfer
    assert not receipt.cross_ocs_memory_import

    receiver_guard = IdentityKernelGuard()
    acceptance = gate.accept(
        receipt,
        sender_audit_log=sender_guard.audit_log,
        receiver_guard=receiver_guard,
        receiver_run_id="run:receiver",
        receiver_ocs="SOFIA",
        receiver_host="ChatGPT",
        session_context="session:receiver",
    )
    assert acceptance.receiver_binding.ocs_id == "SOFIA"
    assert acceptance.receiver_binding.ocs_id != receipt.sender_ocs_id
    assert acceptance.executable_authority_ref is None
    assert acceptance.source_authority_ref == "authority:source-only"


def test_forged_handoff_sender_binding_hash_is_rejected() -> None:
    sender_guard = IdentityKernelGuard()
    sender_guard.bind_active_identity(
        run_id="run:sender-forged",
        ocs_id="NÓESIS",
        host="ChatGPT",
        session_context="session:sender-forged",
    )
    gate = HandoffIdentityGate()
    receipt = gate.issue(
        guard=sender_guard,
        run_id="run:sender-forged",
        handoff_id="handoff:forged",
        sender_ocs="NÓESIS",
        sender_host="ChatGPT",
        receiver_ocs="SOFIA",
        receiver_host_if_known="ChatGPT",
        object_ref="object:handoff",
        authorized_next_scope=("software_implementation",),
        authority_ref="authority:source-only",
    )
    forged = replace(receipt, sender_identity_binding_hash="0" * 64)
    with pytest.raises(ValueError, match="handoff_sender_identity_provenance_mismatch"):
        gate.accept(
            forged,
            sender_audit_log=sender_guard.audit_log,
            receiver_guard=IdentityKernelGuard(),
            receiver_run_id="run:receiver-forged",
            receiver_ocs="SOFIA",
            receiver_host="ChatGPT",
            session_context="session:receiver-forged",
        )


def test_handoff_wrong_receiver_or_host_is_invalid() -> None:
    sender_guard = IdentityKernelGuard()
    sender_guard.bind_active_identity(
        run_id="run:sender",
        ocs_id="NÓESIS",
        host="ChatGPT",
        session_context="session:sender",
    )
    receipt = HandoffIdentityGate().issue(
        guard=sender_guard,
        run_id="run:sender",
        handoff_id="handoff:2",
        sender_ocs="NÓESIS",
        sender_host="ChatGPT",
        receiver_ocs="ÁGORA",
        receiver_host_if_known="ChatGPT",
        object_ref="object:handoff",
        authorized_next_scope=("technical_verification",),
        authority_ref="authority:source-only",
    )
    with pytest.raises(ValueError, match="handoff_receiver_mismatch"):
        HandoffIdentityGate().accept(
            receipt,
            sender_audit_log=sender_guard.audit_log,
            receiver_guard=IdentityKernelGuard(),
            receiver_run_id="run:wrong",
            receiver_ocs="SOFIA",
            receiver_host="ChatGPT",
            session_context="session:wrong",
        )
    with pytest.raises(ValueError, match="handoff_receiver_host_mismatch"):
        HandoffIdentityGate().accept(
            receipt,
            sender_audit_log=sender_guard.audit_log,
            receiver_guard=IdentityKernelGuard(),
            receiver_run_id="run:host-wrong",
            receiver_ocs="ÁGORA",
            receiver_host="Claude",
            session_context="session:wrong-host",
        )


def test_long_context_revalidation_is_logged() -> None:
    guard = IdentityKernelGuard()
    guard.bind_active_identity(
        run_id="run:long",
        ocs_id="MÊTIS",
        host="ChatGPT",
        session_context="session:long",
    )
    result = guard.revalidate(
        run_id="run:long",
        expected_ocs="MÊTIS",
        trigger=IdentityRecheckTrigger.LONG_CONTEXT_DRIFT,
        host="ChatGPT",
    )
    assert result.valid
    assert any(
        event.event_type == "IDENTITY_REVALIDATION"
        and event.details.get("trigger") == "long_context_drift"
        for event in guard.audit_log.events
    )
