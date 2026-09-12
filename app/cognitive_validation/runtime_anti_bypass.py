from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from .action_receipt import (
    ActionCognitiveReceipt,
    ActionCognitiveReceiptError,
    ActionCognitiveReceiptIssuer,
)


class RuntimeAntiBypassError(RuntimeError):
    """Fail-closed denial raised by the COI5 runtime security boundary."""


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RuntimeExecutionContext:
    mission_id: str
    ocs_id: str
    ocs_instance_id: str
    generation: int
    capability_id: str
    capability_version: str
    adapter_version: str
    action_digest: str
    state_hash: str
    policy_version: str


@dataclass(frozen=True, slots=True)
class GovernedExecutionResult(Generic[T]):
    receipt_id: str
    receipt_status: str
    result: T


class RuntimeAntiBypassGateway:
    """Mandatory runtime gate between an OCS proposal and a material executor.

    The executor is never exposed through this object. A valid COI4 action receipt
    must match the exact current runtime context and is atomically consumed before
    the callback can be invoked. Cognition remains non-authorizing: COI5 proves
    cognitive anti-bypass only; independent authority enforcement remains separate.
    """

    def __init__(self, *, action_issuer: ActionCognitiveReceiptIssuer) -> None:
        self._action_issuer = action_issuer

    def execute(
        self,
        receipt: ActionCognitiveReceipt | None,
        *,
        context: RuntimeExecutionContext,
        executor: Callable[[], T],
    ) -> GovernedExecutionResult[T]:
        if receipt is None:
            raise RuntimeAntiBypassError("runtime_cognitive_receipt_required")
        self._validate_context(receipt, context)
        try:
            consumed = self._action_issuer.consume(receipt)
        except ActionCognitiveReceiptError as exc:
            raise RuntimeAntiBypassError("runtime_invalid_expired_or_replayed_receipt") from exc

        # Consumption happens before invocation: a replay can never reach executor.
        result = executor()
        return GovernedExecutionResult(
            receipt_id=consumed.receipt_id,
            receipt_status=consumed.status,
            result=result,
        )

    @staticmethod
    def _validate_context(
        receipt: ActionCognitiveReceipt,
        context: RuntimeExecutionContext,
    ) -> None:
        required = {
            "mission_id": context.mission_id,
            "ocs_id": context.ocs_id,
            "ocs_instance_id": context.ocs_instance_id,
            "capability_id": context.capability_id,
            "capability_version": context.capability_version,
            "adapter_version": context.adapter_version,
            "action_digest": context.action_digest,
            "state_hash": context.state_hash,
            "policy_version": context.policy_version,
        }
        if context.generation < 0:
            raise RuntimeAntiBypassError("runtime_generation_invalid")
        for field, expected in required.items():
            if not expected.strip():
                raise RuntimeAntiBypassError(f"runtime_{field}_required")
            if getattr(receipt, field) != expected:
                raise RuntimeAntiBypassError(f"runtime_{field}_mismatch")
        if receipt.generation != context.generation:
            raise RuntimeAntiBypassError("runtime_generation_mismatch")
