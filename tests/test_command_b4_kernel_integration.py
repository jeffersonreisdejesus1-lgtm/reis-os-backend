from time import time

import pytest

from app.command.kernel_adapter import (
    CommandIntent,
    CommandKernelAdapter,
    CommandKernelContext,
)
from app.universal_kernel.contracts import AuthorizationDecision, Evidence, RiskLevel
from app.universal_kernel.governance import (
    AuthorityLease,
    AuthorityLeaseManager,
    CapabilityRegistry,
    EvidenceEngine,
    GovernanceEngine,
    IdentityConstitutionLoader,
    OCSIdentity,
)

pytestmark = pytest.mark.integration

CAPABILITY = "command.kernel.decision"


def _engine(now: float) -> GovernanceEngine:
    identities = IdentityConstitutionLoader(
        (
            OCSIdentity(
                ocs="ÁGORA",
                specialty="technical-qa-software-audit",
                constitution_version="b4-test-v1",
                allowed_capabilities=frozenset({CAPABILITY}),
            ),
        )
    )
    capabilities = CapabilityRegistry()
    capabilities.register("ÁGORA", frozenset({CAPABILITY}))
    leases = AuthorityLeaseManager()
    leases.issue(
        AuthorityLease(
            lease_id="lease-b4-001",
            ocs="ÁGORA",
            capability=CAPABILITY,
            expires_at=now + 300,
            actor="ÁGORA",
            issued_at=now - 1,
            not_before=now - 1,
            scope=("command:operation:read",),
            tenant="REIS-OS",
            context_ref="context:b4",
            authority_ref="authority:founder:b4",
            policy_snapshot="policy:b4:v1",
            action_binding="command_intent",
            object_ref_or_selector="command:operation:001",
            trace_ref="trace:b4:001",
            max_uses=1,
            single_use=True,
        )
    )
    return GovernanceEngine(identities, capabilities, EvidenceEngine(), leases)


def _intent(
    now: float,
    *,
    actor: str = "ÁGORA",
    evidence: tuple[Evidence, ...] = (Evidence("evidence:b4", True),),
) -> CommandIntent:
    return CommandIntent(
        intent_id="intent-b4-001",
        actor=actor,
        ocs="ÁGORA",
        organization="REIS-OS",
        capability=CAPABILITY,
        operation="evaluate",
        scope=("command:operation:read",),
        reason="Evaluate Command request against Kernel authority",
        expected_state_ref="state:command:42",
        expected_state_version=42,
        idempotency_key="idem-b4-001",
        correlation_id="corr-b4-001",
        causation_id="cause-b4-000",
        payload={"requested": True},
        context=CommandKernelContext(
            lease_id="lease-b4-001",
            csp_ref="csp:b4",
            object_ref="command:operation:001",
            context_ref="context:b4",
            authority_ref="authority:founder:b4",
            policy_snapshot="policy:b4:v1",
            issued_at=now,
            expires_at=now + 120,
            evidence_assessment_ref="assessment:b4",
            recovery_ref="recovery:none:b4",
            trace_id="trace:b4:001",
        ),
        evidence=evidence,
        risk=RiskLevel.LOW,
    )


def test_b4_real_kernel_allow_is_decision_only() -> None:
    now = time()
    readback = CommandKernelAdapter(_engine(now)).decide(_intent(now))

    assert readback.decision is AuthorizationDecision.ALLOW
    assert readback.envelope_issued is True
    assert readback.executed is False
    assert readback.mutation_count == 0


def test_b4_real_kernel_deny_has_zero_mutations() -> None:
    now = time()
    readback = CommandKernelAdapter(_engine(now)).decide(
        _intent(now, actor="COMMAND-HOST")
    )

    assert readback.decision is AuthorizationDecision.DENY
    assert readback.reason == "actor_ocs_mismatch"
    assert readback.envelope_issued is False
    assert readback.executed is False
    assert readback.mutation_count == 0


def test_b4_real_kernel_hold_has_zero_mutations() -> None:
    now = time()
    readback = CommandKernelAdapter(_engine(now)).decide(_intent(now, evidence=()))

    assert readback.decision is AuthorizationDecision.HOLD
    assert readback.reason == "evidence_required"
    assert readback.envelope_issued is False
    assert readback.executed is False
    assert readback.mutation_count == 0
