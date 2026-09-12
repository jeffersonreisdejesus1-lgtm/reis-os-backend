from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from hashlib import sha256
from typing import Protocol

from .contracts import (
    DispatchOutcome,
    DispatchReceipt,
    DispatchRequest,
    HostExecutionReceipt,
    InvocationKind,
    OCSBinding,
)


class HostAdapter(Protocol):
    def invoke(self, request: DispatchRequest, target: OCSBinding, correlation_id: str) -> HostExecutionReceipt: ...


AuthorityPolicy = Callable[[OCSBinding, OCSBinding, InvocationKind], bool]


class ReisOSChatRuntime:
    """Application-level REIS OS multi-OCS dispatcher.

    This runtime proves institutional routing, binding, authority checks, idempotency,
    generation fencing, receipts and host fail-closed behavior. It does not claim that
    the ChatGPT product surface can natively spawn another model or chat instance.
    """

    def __init__(
        self,
        *,
        bindings: Mapping[str, OCSBinding],
        host_adapters: Mapping[str, HostAdapter],
        authority_policy: AuthorityPolicy,
    ) -> None:
        self._bindings = dict(bindings)
        self._host_adapters = dict(host_adapters)
        self._authority_policy = authority_policy
        self._receipts: dict[tuple[str, str], tuple[str, DispatchReceipt]] = {}

    @staticmethod
    def _payload_hash(request: DispatchRequest) -> str:
        material = {
            "mission_id": request.mission_id,
            "parent_ocs_id": request.parent.ocs_id,
            "parent_instance_id": request.parent.instance_id,
            "parent_generation": request.parent.generation,
            "target_ocs_id": request.target_ocs_id,
            "invocation_kind": request.invocation_kind.value,
            "requested_host": request.requested_host,
            "payload": request.payload,
        }
        raw = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _correlation_id(request: DispatchRequest, payload_hash: str) -> str:
        raw = f"{request.mission_id}:{request.idempotency_key}:{payload_hash}"
        return "dispatch:" + sha256(raw.encode("utf-8")).hexdigest()[:24]

    def dispatch(self, request: DispatchRequest) -> DispatchReceipt:
        payload_hash = self._payload_hash(request)
        replay_key = (request.mission_id, request.idempotency_key)
        prior = self._receipts.get(replay_key)
        if prior is not None:
            prior_hash, prior_receipt = prior
            if prior_hash != payload_hash:
                raise ValueError("chat_runtime_idempotency_conflict")
            return prior_receipt

        correlation_id = self._correlation_id(request, payload_hash)
        current_parent = self._bindings.get(request.parent.ocs_id)
        if current_parent is None:
            return self._hold(request, payload_hash, correlation_id, "parent_ocs_unknown")
        if (
            current_parent.instance_id != request.parent.instance_id
            or current_parent.generation != request.parent.generation
        ):
            return self._hold(request, payload_hash, correlation_id, "parent_generation_or_instance_fenced")
        if current_parent.authority_ref != request.parent.authority_ref:
            return self._hold(request, payload_hash, correlation_id, "parent_authority_mismatch")

        target = self._bindings.get(request.target_ocs_id)
        if target is None:
            return self._hold(request, payload_hash, correlation_id, "target_ocs_unknown")

        if request.invocation_kind is InvocationKind.AUXILIARY and target.ocs_id != request.parent.ocs_id:
            return self._hold(request, payload_hash, correlation_id, "auxiliary_cannot_become_peer_ocs")

        if not self._authority_policy(request.parent, target, request.invocation_kind):
            return self._hold(request, payload_hash, correlation_id, "authority_policy_denied")

        host = request.requested_host or target.host
        if host != target.host:
            return self._hold(request, payload_hash, correlation_id, "target_host_binding_mismatch")
        adapter = self._host_adapters.get(host)
        if adapter is None:
            return self._hold(request, payload_hash, correlation_id, "host_adapter_unavailable")

        host_receipt = adapter.invoke(request, target, correlation_id)
        if (
            host_receipt.mission_id != request.mission_id
            or host_receipt.target_ocs_id != target.ocs_id
            or host_receipt.target_instance_id != target.instance_id
            or host_receipt.generation != target.generation
            or host_receipt.host != target.host
            or host_receipt.correlation_id != correlation_id
        ):
            return self._hold(request, payload_hash, correlation_id, "host_receipt_binding_mismatch")

        receipt = DispatchReceipt(
            mission_id=request.mission_id,
            parent_ocs_id=request.parent.ocs_id,
            target_ocs_id=target.ocs_id,
            target_instance_id=target.instance_id,
            invocation_kind=request.invocation_kind,
            host=target.host,
            outcome=DispatchOutcome.EXECUTED,
            idempotency_key=request.idempotency_key,
            correlation_id=correlation_id,
            output=host_receipt.output,
        )
        self._receipts[replay_key] = (payload_hash, receipt)
        return receipt

    def _hold(
        self,
        request: DispatchRequest,
        payload_hash: str,
        correlation_id: str,
        reason: str,
    ) -> DispatchReceipt:
        receipt = DispatchReceipt(
            mission_id=request.mission_id,
            parent_ocs_id=request.parent.ocs_id,
            target_ocs_id=request.target_ocs_id,
            target_instance_id=None,
            invocation_kind=request.invocation_kind,
            host=request.requested_host,
            outcome=DispatchOutcome.HOLD,
            idempotency_key=request.idempotency_key,
            correlation_id=correlation_id,
            hold_reason=reason,
        )
        self._receipts[(request.mission_id, request.idempotency_key)] = (payload_hash, receipt)
        return receipt
