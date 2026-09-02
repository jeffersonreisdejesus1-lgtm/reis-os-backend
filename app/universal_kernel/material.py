from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Protocol

from .contracts import AuthorizedActionEnvelope, EffectAttemptResult
from .governance import AuthorityLeaseManager, CapabilityRegistry
from .trace import TraceLedger


class MaterialAdapter(Protocol):
    adapter_id: str

    def execute(self, envelope: AuthorizedActionEnvelope) -> tuple[int, str]: ...

    def readback(self, envelope: AuthorizedActionEnvelope) -> str: ...


@dataclass
class InMemoryMutationAdapter:
    adapter_id: str
    mutation_count: int = 0
    last_action_id: str | None = None

    def execute(self, envelope: AuthorizedActionEnvelope) -> tuple[int, str]:
        self.mutation_count += 1
        self.last_action_id = envelope.action_id
        return 1, f"provider://{self.adapter_id}/{envelope.action_id}"

    def readback(self, envelope: AuthorizedActionEnvelope) -> str:
        return f"readback://{self.adapter_id}/{envelope.action_id}/{self.mutation_count}"


@dataclass(frozen=True)
class EffectorInvocation:
    envelope: AuthorizedActionEnvelope
    adapter: MaterialAdapter


class ToolBroker:
    def __init__(
        self,
        registry: CapabilityRegistry,
        leases: AuthorityLeaseManager,
        trace: TraceLedger,
    ) -> None:
        self._registry = registry
        self._leases = leases
        self._trace = trace
        self._adapters: dict[str, MaterialAdapter] = {}
        self.resolution_count = 0

    def bind_adapter(self, adapter: MaterialAdapter) -> None:
        self._adapters[adapter.adapter_id] = adapter

    def resolve(self, envelope: AuthorizedActionEnvelope, capability_ref: str) -> EffectorInvocation:
        descriptor = self._registry.describe(capability_ref)
        lease = self._leases.get(envelope.lease_ref)
        if not lease.active:
            raise PermissionError("inactive lease blocks adapter resolution")
        if descriptor.required_scope != envelope.valid_scope:
            raise PermissionError("scope mismatch blocks adapter resolution")
        adapter = self._adapters[descriptor.adapter_id]
        self.resolution_count += 1
        self._trace.append(
            "tool_broker_resolution",
            {"action_id": envelope.action_id, "adapter_id": descriptor.adapter_id},
        )
        return EffectorInvocation(envelope=envelope, adapter=adapter)


class ThinEffector:
    def __init__(self, leases: AuthorityLeaseManager, trace: TraceLedger) -> None:
        self._leases = leases
        self._trace = trace

    def execute(self, invocation: EffectorInvocation) -> EffectAttemptResult:
        started = int(time.time())
        envelope = invocation.envelope
        try:
            self._leases.consume(envelope.lease_ref)
        except PermissionError as exc:
            event = self._trace.append(
                "effect_blocked",
                {"action_id": envelope.action_id, "reason": str(exc)},
            )
            return EffectAttemptResult(
                action_id=envelope.action_id,
                attempted=False,
                provider_ref=None,
                result_class="DENIED",
                mutation_observed=False,
                mutation_count=0,
                readback_ref=None,
                error_ref="lease_inactive",
                started_at=started,
                ended_at=int(time.time()),
                trace_ref=event.event_hash,
            )

        mutation_count, provider_ref = invocation.adapter.execute(envelope)
        readback_ref = invocation.adapter.readback(envelope)
        event = self._trace.append(
            "material_effect",
            {
                "action_id": envelope.action_id,
                "provider_ref": provider_ref,
                "readback_ref": readback_ref,
                "mutation_count": str(mutation_count),
            },
        )
        return EffectAttemptResult(
            action_id=envelope.action_id,
            attempted=True,
            provider_ref=provider_ref,
            result_class="SUCCESS",
            mutation_observed=mutation_count > 0,
            mutation_count=mutation_count,
            readback_ref=readback_ref,
            error_ref=None,
            started_at=started,
            ended_at=int(time.time()),
            trace_ref=event.event_hash,
        )
