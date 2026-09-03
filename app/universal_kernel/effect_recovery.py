from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Protocol, cast

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


class CompensationVerifier(Protocol):
    def readback(self, compensation_id: str) -> MaterialReadback: ...

    def verify(
        self,
        original_mutation_id: str,
        compensation_readback: MaterialReadback,
    ) -> bool: ...


CompensateFn = Callable[[str, dict[str, object], str, str], str]


@dataclass(frozen=True)
class MaterialBoundaryClaim:
    strength: str
    structural_denial: bool
    process_isolated: bool


class MaterialEffectFailure(RuntimeError):
    def __init__(self, reason: str, mutation_id: str) -> None:
        super().__init__(reason)
        self.mutation_id = mutation_id


class ToolBroker:
    def __init__(self) -> None:
        self._adapters: dict[str, MutableAdapter] = {}
        self._compensation_verifiers: dict[str, CompensationVerifier] = {}
        self.__resolution_token = object()
        self.__active_resolution: ContextVar[object | None] = ContextVar(
            f"broker_resolution_{id(self)}",
            default=None,
        )
        self.__bound_adapter_ids: set[int] = set()

    def material_boundary_claim(self) -> MaterialBoundaryClaim:
        return MaterialBoundaryClaim(
            strength="IN_PROCESS_GUARD_ONLY",
            structural_denial=False,
            process_isolated=False,
        )

    def register(
        self,
        capability: str,
        adapter: MutableAdapter,
        *,
        compensation_verifier: CompensationVerifier | None = None,
    ) -> None:
        if id(adapter) in self.__bound_adapter_ids:
            raise ValueError("adapter_already_broker_bound")
        if compensation_verifier is adapter:
            raise ValueError("compensation_verifier_must_be_independent")
        original_mutate = adapter.mutate

        def guarded_mutate(
            operation: str,
            payload: dict[str, object],
            idempotency_key: str,
        ) -> str:
            if self.__active_resolution.get() is not self.__resolution_token:
                raise ValueError("direct_adapter_mutation_prohibited")
            return original_mutate(operation, payload, idempotency_key)

        object.__setattr__(adapter, "mutate", guarded_mutate)
        raw_compensate = getattr(adapter, "compensate", None)
        if raw_compensate is not None:
            original_compensate = cast(CompensateFn, raw_compensate)

            def guarded_compensate(
                operation: str,
                payload: dict[str, object],
                mutation_id: str,
                idempotency_key: str,
            ) -> str:
                if self.__active_resolution.get() is not self.__resolution_token:
                    raise ValueError("direct_adapter_compensation_prohibited")
                return original_compensate(
                    operation,
                    payload,
                    mutation_id,
                    idempotency_key,
                )

            object.__setattr__(adapter, "compensate", guarded_compensate)
        self.__bound_adapter_ids.add(id(adapter))
        self._adapters[capability] = adapter
        if compensation_verifier is not None:
            self._compensation_verifiers[capability] = compensation_verifier

    def has_independent_compensation_verifier(self, capability: str) -> bool:
        verifier = self._compensation_verifiers.get(capability)
        adapter = self._adapters.get(capability)
        return verifier is not None and verifier is not adapter

    def adapter_for(self, capability: str) -> MutableAdapter:
        if self.__active_resolution.get() is not self.__resolution_token:
            raise ValueError("direct_adapter_resolution_prohibited")
        try:
            return self._adapters[capability]
        except KeyError as exc:
            raise ValueError("adapter_not_registered") from exc

    def _validate_envelope(self, envelope: AuthorizedActionEnvelope) -> None:
        if envelope.capability not in envelope.scope or not envelope.valid_scope:
            raise ValueError("material_boundary_scope_invalid")
        if not envelope.authority_ref or envelope.lease_use_index is None:
            raise ValueError("material_boundary_authority_required")

    def resolve_for(self, envelope: AuthorizedActionEnvelope) -> MutableAdapter:
        self._validate_envelope(envelope)
        reset_token = self.__active_resolution.set(self.__resolution_token)
        try:
            return self.adapter_for(envelope.capability)
        finally:
            self.__active_resolution.reset(reset_token)

    def mutate_for(self, envelope: AuthorizedActionEnvelope) -> str:
        self._validate_envelope(envelope)
        reset_token = self.__active_resolution.set(self.__resolution_token)
        try:
            adapter = self.adapter_for(envelope.capability)
            return adapter.mutate(
                envelope.operation,
                envelope.payload,
                envelope.idempotency_key,
            )
        finally:
            self.__active_resolution.reset(reset_token)

    def readback_for(
        self,
        envelope: AuthorizedActionEnvelope,
        mutation_id: str,
    ) -> MaterialReadback:
        self._validate_envelope(envelope)
        reset_token = self.__active_resolution.set(self.__resolution_token)
        try:
            adapter = self.adapter_for(envelope.capability)
            return adapter.readback(mutation_id)
        finally:
            self.__active_resolution.reset(reset_token)

    def compensate_for(
        self,
        envelope: AuthorizedActionEnvelope,
        mutation_id: str,
    ) -> MaterialReadback:
        self._validate_envelope(envelope)
        verifier = self._compensation_verifiers.get(envelope.capability)
        adapter = self._adapters.get(envelope.capability)
        if verifier is None or verifier is adapter:
            raise RuntimeError("independent_compensation_verifier_required")
        reset_token = self.__active_resolution.set(self.__resolution_token)
        try:
            bound_adapter = self.adapter_for(envelope.capability)
            compensate = getattr(bound_adapter, "compensate", None)
            if compensate is None:
                raise RuntimeError("material_compensation_unavailable")
            compensation_id = compensate(
                envelope.operation,
                envelope.payload,
                mutation_id,
                f"compensate:{envelope.idempotency_key}",
            )
        finally:
            self.__active_resolution.reset(reset_token)
        external_readback = verifier.readback(compensation_id)
        if not verifier.verify(mutation_id, external_readback):
            raise RuntimeError("material_compensation_verification_failed")
        return external_readback


class ThinEffector:
    def __init__(self, broker: ToolBroker) -> None:
        self._broker = broker
        self._completed: dict[str, MaterialReadback] = {}

    def execute(self, envelope: AuthorizedActionEnvelope) -> MaterialReadback:
        cached = self._completed.get(envelope.idempotency_key)
        if cached is not None:
            return cached
        mutation_id = self._broker.mutate_for(envelope)
        try:
            readback = self._broker.readback_for(envelope, mutation_id)
        except RuntimeError as exc:
            raise MaterialEffectFailure(str(exc), mutation_id) from exc
        self._completed[envelope.idempotency_key] = readback
        return readback

    def compensate(
        self,
        envelope: AuthorizedActionEnvelope,
        mutation_id: str,
    ) -> MaterialReadback:
        return self._broker.compensate_for(envelope, mutation_id)


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
        except (RuntimeError, ValueError):
            return RecoveryReceipt(
                disposition="compensation_unverified",
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
