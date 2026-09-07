from __future__ import annotations

import pytest

from app.chat_runtime import (
    DispatchOutcome,
    DispatchRequest,
    HostExecutionReceipt,
    InvocationKind,
    OCSBinding,
    ReisOSChatRuntime,
)


class EchoHostAdapter:
    def invoke(self, request, target, correlation_id):
        return HostExecutionReceipt(
            mission_id=request.mission_id,
            target_ocs_id=target.ocs_id,
            target_instance_id=target.instance_id,
            generation=target.generation,
            host=target.host,
            correlation_id=correlation_id,
            output={"accepted": True, "target": target.ocs_id, "host": target.host},
        )


class WrongReceiptAdapter:
    def invoke(self, request, target, correlation_id):
        return HostExecutionReceipt(
            mission_id=request.mission_id,
            target_ocs_id=target.ocs_id,
            target_instance_id="wrong-instance",
            generation=target.generation,
            host=target.host,
            correlation_id=correlation_id,
            output={"accepted": True},
        )


def binding(ocs_id: str, instance_id: str, generation: int, host: str) -> OCSBinding:
    return OCSBinding(
        ocs_id=ocs_id,
        instance_id=instance_id,
        generation=generation,
        authority_ref=f"authority:{ocs_id.lower()}:chat-runtime",
        state_namespace=f"state:reis-os:{ocs_id.lower()}",
        memory_namespace=f"memory:reis-os:{ocs_id.lower()}",
        host=host,
    )


def allow_all(parent, target, kind):
    return True


def runtime(adapters=None):
    noesis = binding("NOESIS", "gpt:noesis:1", 1, "GPT")
    dedala = binding("DEDALA", "grok:dedala:1", 1, "GROK")
    return ReisOSChatRuntime(
        bindings={"NOESIS": noesis, "DEDALA": dedala},
        host_adapters=adapters or {"GPT": EchoHostAdapter(), "GROK": EchoHostAdapter()},
        authority_policy=allow_all,
    ), noesis, dedala


def test_peer_ocs_dispatch_returns_bound_receipt():
    rt, noesis, _ = runtime()
    receipt = rt.dispatch(
        DispatchRequest(
            mission_id="mission:chat:peer",
            parent=noesis,
            target_ocs_id="DEDALA",
            invocation_kind=InvocationKind.PEER_OCS,
            payload={"task": "adversarial review"},
            idempotency_key="peer-1",
        )
    )
    assert receipt.outcome is DispatchOutcome.EXECUTED
    assert receipt.target_ocs_id == "DEDALA"
    assert receipt.host == "GROK"
    assert receipt.output == {"accepted": True, "target": "DEDALA", "host": "GROK"}


def test_auxiliary_stays_inside_parent_ocs_identity():
    rt, noesis, _ = runtime()
    receipt = rt.dispatch(
        DispatchRequest(
            mission_id="mission:chat:aux",
            parent=noesis,
            target_ocs_id="NOESIS",
            invocation_kind=InvocationKind.AUXILIARY,
            payload={"task": "bounded synthesis"},
            idempotency_key="aux-1",
        )
    )
    assert receipt.outcome is DispatchOutcome.EXECUTED
    assert receipt.target_ocs_id == "NOESIS"


def test_auxiliary_cannot_impersonate_peer_ocs():
    rt, noesis, _ = runtime()
    receipt = rt.dispatch(
        DispatchRequest(
            mission_id="mission:chat:aux-denied",
            parent=noesis,
            target_ocs_id="DEDALA",
            invocation_kind=InvocationKind.AUXILIARY,
            payload={"task": "impersonate peer"},
            idempotency_key="aux-denied",
        )
    )
    assert receipt.outcome is DispatchOutcome.HOLD
    assert receipt.hold_reason == "auxiliary_cannot_become_peer_ocs"


def test_missing_host_adapter_fails_closed_without_fake_execution():
    rt, noesis, _ = runtime(adapters={"GPT": EchoHostAdapter()})
    receipt = rt.dispatch(
        DispatchRequest(
            mission_id="mission:chat:no-adapter",
            parent=noesis,
            target_ocs_id="DEDALA",
            invocation_kind=InvocationKind.PEER_OCS,
            payload={"task": "call grok"},
            idempotency_key="no-adapter",
        )
    )
    assert receipt.outcome is DispatchOutcome.HOLD
    assert receipt.hold_reason == "host_adapter_unavailable"


def test_old_parent_generation_is_fenced():
    rt, noesis, _ = runtime()
    stale_parent = OCSBinding(
        ocs_id=noesis.ocs_id,
        instance_id=noesis.instance_id,
        generation=0,
        authority_ref=noesis.authority_ref,
        state_namespace=noesis.state_namespace,
        memory_namespace=noesis.memory_namespace,
        host=noesis.host,
    )
    receipt = rt.dispatch(
        DispatchRequest(
            mission_id="mission:chat:fenced",
            parent=stale_parent,
            target_ocs_id="DEDALA",
            invocation_kind=InvocationKind.PEER_OCS,
            payload={"task": "stale call"},
            idempotency_key="fenced",
        )
    )
    assert receipt.outcome is DispatchOutcome.HOLD
    assert receipt.hold_reason == "parent_generation_or_instance_fenced"


def test_host_receipt_binding_mismatch_fails_closed():
    rt, noesis, _ = runtime(adapters={"GPT": EchoHostAdapter(), "GROK": WrongReceiptAdapter()})
    receipt = rt.dispatch(
        DispatchRequest(
            mission_id="mission:chat:bad-receipt",
            parent=noesis,
            target_ocs_id="DEDALA",
            invocation_kind=InvocationKind.PEER_OCS,
            payload={"task": "review"},
            idempotency_key="bad-receipt",
        )
    )
    assert receipt.outcome is DispatchOutcome.HOLD
    assert receipt.hold_reason == "host_receipt_binding_mismatch"


def test_idempotent_replay_returns_same_receipt_and_divergent_retry_conflicts():
    rt, noesis, _ = runtime()
    request = DispatchRequest(
        mission_id="mission:chat:idempotent",
        parent=noesis,
        target_ocs_id="DEDALA",
        invocation_kind=InvocationKind.PEER_OCS,
        payload={"task": "same"},
        idempotency_key="same-key",
    )
    first = rt.dispatch(request)
    second = rt.dispatch(request)
    assert first == second

    with pytest.raises(ValueError, match="chat_runtime_idempotency_conflict"):
        rt.dispatch(
            DispatchRequest(
                mission_id=request.mission_id,
                parent=noesis,
                target_ocs_id="DEDALA",
                invocation_kind=InvocationKind.PEER_OCS,
                payload={"task": "different"},
                idempotency_key=request.idempotency_key,
            )
        )
