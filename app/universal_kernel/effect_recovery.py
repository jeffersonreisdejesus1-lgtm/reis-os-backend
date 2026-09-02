from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import (
    AuthorizedActionEnvelope,
    MaterialReadback,
    StateRecord,
    VerifiedCheckpoint,
)
from .state_trace import StateCore


class MutableAdapter(Protocol):
    def mutate(self, operation: str, payload: dict[str, object]) -> str: ...

    def readback(self, mutation_id: str) -> MaterialReadback: ...


class ToolBroker:
    def __init__(self) -> None:
        self._adapters: dict[str, MutableAdapter] = {}

    def register(self, capability: str, adapter: MutableAdapter) -> None:
        self._adapters[capability] = adapter

    def adapter_for(self, capability: str) -> MutableAdapter:
        try:
            return self._adapters[capability]
        except KeyError as exc:
            raise ValueError("adapter_not_registered") from exc


class ThinEffector:
    def __init__(self, broker: ToolBroker) -> None:
        self._broker = broker

    def execute(self, envelope: AuthorizedActionEnvelope) -> MaterialReadback:
        adapter = self._broker.adapter_for(envelope.capability)
        mutation_id = adapter.mutate(envelope.operation, envelope.payload)
        return adapter.readback(mutation_id)


@dataclass
class RecoveryManager:
    state: StateCore

    def restore(self, checkpoint: VerifiedCheckpoint) -> StateRecord:
        return self.state.restore_verified(checkpoint)
