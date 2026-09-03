from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .contracts import (
    AuthorizedActionEnvelope,
    MaterialReadback,
    RecoveryReceipt,
    ReversibilityClass,
    StateRecord,
    VerifiedCheckpoint,
)
from .state_trace import StateCore


class MutableAdapter(Protocol):
    def mutate(
        self,
        operation: str,
        payload: dict[str, object],
        idempotency_key: str,
    ) -> str: ...

    def readback(self, mutation_id: str) -> MaterialReadback: ...


class MaterialEffectFailure(RuntimeError):
    def __init__(self, reason: str, mutation_id: str) -> None:
        super().__init__(reason)
        self.mutation_id = mutation_id


class ToolBroker:
    def __init__(self) -> None:
        self._adapters: dict[str, MutableAdapter] = {}
        self._resolution_depth = 0

    def register(self, capability: str, adapter: MutableAdapter) -> None:
        self._adapters[capability] = adapter

    def adapter_for(self, capability: str) -> MutableAdapter:
        if self._resolution_depth <= 0:
            raise ValueError("direct_adapter_resolution_prohibited")
        try:
            return self._adapters[capability]
        except KeyError as exc:
            raise ValueError("adapter_not_registered") from exc

    def resolve_for(self, envelope: AuthorizedActionEnvelope) -> MutableAdapter:
        if envelope.capability not in envelope.scope or not envelope.valid_scope:
            raise ValueError("material_boundary_scope_invalid")
        if not envelope.authority_ref or envelope.lease_use_index is None:
            raise ValueError("material_boundary_authority_required")
        self._resolution_depth += 1
        try:
            return self.adapter_for(envelope.capability)
        finally:
            self._resolution_depth -= 1


class ThinEffector:
    def __init__(self, broker: ToolBroker) -> None:
        self._broker = broker
        self._completed: dict[str, MaterialReadback] = {}

    def execute(self, envelope: AuthorizedActionEnvelope) -> MaterialReadback:
        cached = self._completed.get(envelope.idempotency_key)
        if cached is not None:
            return cached
        adapter = self._broker.resolve_for(envelope)
        mutation_id = adapter.mutate(
            envelope.operation,
            envelope.payload,
            envelope.idempotency_key,
        )
        try:
            readback = adapter.readback(mutation_id)
        except RuntimeError as exc:
            raise MaterialEffectFailure(str(exc), mutation_id) from exc
        self._completed[envelope.idempotency_key] = readback
        return readback

    def compensate(
        self,
        envelope: AuthorizedActionEnvelope,
        mutation_id: str,
    ) -> MaterialReadback:
        adapter = self._broker.resolve_for(envelope)
        compensate = getattr(adapter, "compensate", None)
        if compensate is None:
            raise RuntimeError("material_compensation_unavailable")
        compensation_id = compensate(
            envelope.operation,
            envelope.payload,
            mutation_id,
            f"compensate:{envelope.idempotency_key}",
        )
        return adapter.readback(compensation_id)


@dataclass
class RecoveryManager:
    state: StateCore
    _checkpoints: dict[str, VerifiedCheckpoint] = field(default_factory=dict)

    def register_checkpoint(
        self,
        recovery_ref: str,
        checkpoint: VerifiedCheckpoint,
    ) -> None:
        if not checkpoint.state.verified:
            raise ValueError("verified_checkpoint_required")
        self._checkpoints[recovery_ref] = checkpoint

    def restore(self, checkpoint: VerifiedCheckpoint) -> StateRecord:
        return self.state.restore_verified(checkpoint)

    def recover_post_effect(
        self,
        envelope: AuthorizedActionEnvelope,
        mutation_id: str,
        effector: ThinEffector,
    ) -> RecoveryReceipt:
        checkpoint = self._checkpoints.get(envelope.recovery_ref)
        if envelope.reversibility_class is ReversibilityClass.IRREVERSIBLE:
            return RecoveryReceipt(
                disposition="incident",
                state_recovered=False,
                material_compensated=False,
                residual_effect=True,
            )
        try:
            external_readback = effector.compensate(envelope, mutation_id)
        except RuntimeError:
            return RecoveryReceipt(
                disposition="incident",
                state_recovered=False,
                material_compensated=False,
                residual_effect=True,
            )
        state_recovered = False
        if checkpoint is not None:
            current = self.state.current(checkpoint.state.ocs)
            if current is not None and current.state_id == checkpoint.state.state_id:
                state_recovered = True
            else:
                self.restore(checkpoint)
                state_recovered = True
        return RecoveryReceipt(
            disposition="recovered",
            state_recovered=state_recovered,
            material_compensated=True,
            residual_effect=False,
            external_readback=external_readback,
        )
