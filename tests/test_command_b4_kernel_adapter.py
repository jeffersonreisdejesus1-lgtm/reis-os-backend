from app.command.kernel_adapter import (
    CommandIntent,
    CommandKernelAdapter,
    CommandKernelContext,
)
from app.universal_kernel.contracts import AuthorizationDecision, GovernanceResult


class CapturingKernel:
    def __init__(self, result: GovernanceResult) -> None:
        self.result = result
        self.proposal = None

    def authorize(self, proposal):  # type: ignore[no-untyped-def]
        self.proposal = proposal
        return self.result


def _intent() -> CommandIntent:
    return CommandIntent(
        intent_id="intent-b4-001",
        actor="ÁGORA",
        ocs="ÁGORA",
        organization="REIS-OS",
        capability="command.kernel.decision",
        operation="evaluate",
        scope=("command:operation:read",),
        reason="Founder-authorized B4 decision request",
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
            issued_at=1.0,
            expires_at=2.0,
            evidence_assessment_ref="assessment:b4",
            recovery_ref="recovery:none:b4",
            trace_id="trace:b4:001",
        ),
    )


def test_b4_contextualizes_without_executing() -> None:
    kernel = CapturingKernel(GovernanceResult(AuthorizationDecision.DENY, "test-deny"))
    readback = CommandKernelAdapter(kernel).decide(_intent())

    assert kernel.proposal is not None
    assert kernel.proposal.tenant == "REIS-OS"
    assert kernel.proposal.scope == ("command:operation:read",)
    assert kernel.proposal.payload["expected_state_version"] == 42
    assert kernel.proposal.payload["command_reason"] == (
        "Founder-authorized B4 decision request"
    )
    assert kernel.proposal.side_effect_class.value == "none"
    assert readback.decision is AuthorizationDecision.DENY
    assert readback.executed is False
    assert readback.mutation_count == 0
    assert readback.expected_state_version == 42
    assert readback.idempotency_key == "idem-b4-001"


def test_b4_rejects_incomplete_context_before_kernel() -> None:
    intent = _intent()
    invalid = CommandIntent(
        **{**intent.__dict__, "organization": ""},
    )
    kernel = CapturingKernel(GovernanceResult(AuthorizationDecision.ALLOW, "unused"))

    try:
        CommandKernelAdapter(kernel).decide(invalid)
    except ValueError as exc:
        assert str(exc) == "command_intent_incomplete:organization"
    else:
        raise AssertionError("incomplete Command intent must fail closed")

    assert kernel.proposal is None
