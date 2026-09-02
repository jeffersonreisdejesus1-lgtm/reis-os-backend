from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import AuthorizedActionEnvelope, EffectAttemptResult, GovernanceDecision, GovernanceResult


class AdapterPort(Protocol):
    adapter_id: str

    def execute(self, envelope: AuthorizedActionEnvelope) -> tuple[int, str]: ...

    def readback(self, envelope: AuthorizedActionEnvelope) -> str: ...


@dataclass
class InMemoryMutationAdapter:
    adapter_id: str = "memory"
    mutations: int = 0
    value: str | None = None

    def execute(self, envelope: AuthorizedActionEnvelope) -> tuple[int, str]:
        self.mutations += 1
        self.value = envelope.expected_effect
        return 1, f"provider:{self.mutations}"

    def readback(self, envelope: AuthorizedActionEnvelope) -> str:
        return self.value or ""


class ThinEffector:
    def execute(self, envelope: AuthorizedActionEnvelope, adapter: AdapterPort, now: int) -> EffectAttemptResult:
        count, provider_ref = adapter.execute(envelope)
        readback = adapter.readback(envelope)
        return EffectAttemptResult(envelope.action_id, True, provider_ref, "success", count > 0, count, f"readback:{readback}", None, now, now, envelope.trace_id)


class ToolBroker:
    def __init__(self) -> None:
        self._adapters: dict[str, AdapterPort] = {}

    def register(self, adapter: AdapterPort) -> None:
        self._adapters[adapter.adapter_id] = adapter

    def resolve_and_execute(self, *, decision: GovernanceDecision, envelope: AuthorizedActionEnvelope | None, adapter_id: str, effector: ThinEffector, now: int) -> EffectAttemptResult:
        if decision.result is not GovernanceResult.AUTHORIZE or envelope is None:
            return EffectAttemptResult(decision.proposal_id, False, None, "denied", False, 0, None, "not_authorized", now, now, decision.trace_ref or "trace:none")
        adapter = self._adapters[adapter_id]
        return effector.execute(envelope, adapter, now)
