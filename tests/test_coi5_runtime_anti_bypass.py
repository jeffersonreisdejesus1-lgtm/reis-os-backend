from __future__ import annotations

from dataclasses import replace

import pytest

from app.cognitive_validation.action_receipt import (
    ActionCognitiveReceiptIssuer,
    ActionReceiptLedger,
)
from app.cognitive_validation.bootstrap_binding import BootstrapCognitiveBinding
from app.cognitive_validation.mission_receipt import MissionCognitiveReceiptIssuer
from app.cognitive_validation.runtime_anti_bypass import (
    RuntimeAntiBypassError,
    RuntimeAntiBypassGateway,
    RuntimeExecutionContext,
)


def binding() -> BootstrapCognitiveBinding:
    return BootstrapCognitiveBinding(
        binding_id="binding:coi5-001",
        mission_id="mission-001",
        ocs_id="NOESIS",
        ocs_instance_id="noesis-runtime-001",
        generation=9,
        cognitive_entrypoint="UNIVERSAL_COGNITIVE_ENTRYPOINT",
        brain_path="AB0-AB13/canonical",
        authority_ref="authority:noesis:mission-001",
        state_namespace="state:noesis",
        memory_namespace="memory:noesis",
    )


def mission_issuer() -> MissionCognitiveReceiptIssuer:
    return MissionCognitiveReceiptIssuer(
        signing_secret=b"coi3-test-secret",
        clock=lambda: 1_700_000_000.0,
        nonce_factory=lambda: "mission-nonce",
    )


def action_issuer(*, ledger=None, clock=lambda: 1_700_000_001.0):
    return ActionCognitiveReceiptIssuer(
        signing_secret=b"coi4-test-secret",
        mission_issuer=mission_issuer(),
        ledger=ledger,
        clock=clock,
        nonce_factory=lambda: "action-nonce",
        ttl_seconds=60,
    )


def receipt(issuer):
    mission = mission_issuer().issue(
        binding(),
        intent="execute governed capability",
        state_revision="state-r44",
        state_hash="state-hash-001",
        cognition_cycle_id="cycle-001",
    )
    return issuer.issue(
        mission,
        plan_hash="plan-hash-001",
        action_digest="action-digest-001",
        capability_id="github",
        capability_version="v1",
        adapter_version="adapter-v1",
        authority_requirements=("repo:write",),
        state_hash="state-hash-001",
        policy_version="policy-v1",
    )


def context(**changes) -> RuntimeExecutionContext:
    values = dict(
        mission_id="mission-001",
        ocs_id="NOESIS",
        ocs_instance_id="noesis-runtime-001",
        generation=9,
        capability_id="github",
        capability_version="v1",
        adapter_version="adapter-v1",
        action_digest="action-digest-001",
        state_hash="state-hash-001",
        policy_version="policy-v1",
    )
    values.update(changes)
    return RuntimeExecutionContext(**values)


def test_valid_receipt_is_consumed_before_executor_runs() -> None:
    issuer = action_issuer()
    gateway = RuntimeAntiBypassGateway(action_issuer=issuer)
    r = receipt(issuer)
    observed = []

    def executor():
        observed.append(issuer.verify(r))
        return "effect"

    result = gateway.execute(r, context=context(), executor=executor)
    assert result.result == "effect"
    assert result.receipt_status == "CONSUMED"
    assert observed == [False]


def test_direct_execution_without_cognitive_receipt_is_denied_and_executor_not_called() -> None:
    gateway = RuntimeAntiBypassGateway(action_issuer=action_issuer())
    called = []
    with pytest.raises(RuntimeAntiBypassError, match="receipt_required"):
        gateway.execute(None, context=context(), executor=lambda: called.append(True))
    assert called == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mission_id", "mission-other"),
        ("ocs_id", "THEMIS"),
        ("ocs_instance_id", "other-instance"),
        ("generation", 10),
        ("capability_id", "notion"),
        ("capability_version", "v2"),
        ("adapter_version", "adapter-v2"),
        ("action_digest", "other-action"),
        ("state_hash", "changed-state"),
        ("policy_version", "policy-v2"),
    ],
)
def test_context_mismatch_is_denied_before_executor(field, value) -> None:
    issuer = action_issuer()
    gateway = RuntimeAntiBypassGateway(action_issuer=issuer)
    r = receipt(issuer)
    called = []
    with pytest.raises(RuntimeAntiBypassError, match="mismatch"):
        gateway.execute(r, context=context(**{field: value}), executor=lambda: called.append(True))
    assert called == []
    assert issuer.verify(r) is True


def test_tampered_receipt_is_denied_before_executor() -> None:
    issuer = action_issuer()
    gateway = RuntimeAntiBypassGateway(action_issuer=issuer)
    r = replace(receipt(issuer), signature="0" * 64)
    called = []
    with pytest.raises(RuntimeAntiBypassError, match="invalid_expired_or_replayed"):
        gateway.execute(r, context=context(), executor=lambda: called.append(True))
    assert called == []


def test_expired_receipt_is_denied_before_executor() -> None:
    issuer = action_issuer(clock=lambda: 1_700_000_100.0)
    gateway = RuntimeAntiBypassGateway(action_issuer=issuer)
    # Issue using a separate clock then validate using the later gateway clock.
    issuing = action_issuer(clock=lambda: 1_700_000_001.0)
    r = receipt(issuing)
    called = []
    with pytest.raises(RuntimeAntiBypassError, match="invalid_expired_or_replayed"):
        gateway.execute(r, context=context(), executor=lambda: called.append(True))
    assert called == []


def test_replay_is_denied_and_executor_runs_only_once() -> None:
    ledger = ActionReceiptLedger()
    issuer = action_issuer(ledger=ledger)
    gateway = RuntimeAntiBypassGateway(action_issuer=issuer)
    r = receipt(issuer)
    called = []
    gateway.execute(r, context=context(), executor=lambda: called.append("first"))
    with pytest.raises(RuntimeAntiBypassError, match="invalid_expired_or_replayed"):
        gateway.execute(r, context=context(), executor=lambda: called.append("replay"))
    assert called == ["first"]


def test_cognition_cannot_self_promote_to_authority_or_effect_permission() -> None:
    issuer = action_issuer()
    gateway = RuntimeAntiBypassGateway(action_issuer=issuer)
    r = receipt(issuer)
    called = []
    for promoted in (replace(r, authority_granted=True), replace(r, effects_permitted=True)):
        with pytest.raises(RuntimeAntiBypassError, match="invalid_expired_or_replayed"):
            gateway.execute(promoted, context=context(), executor=lambda: called.append(True))
    assert called == []
