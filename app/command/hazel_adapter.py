from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Protocol

from app.command.kernel_adapter import KernelDecisionReadback
from app.universal_kernel.contracts import AuthorizationDecision
from app.universal_kernel.hazel_continuity import HazelIntegrationError


class HazelContinuityPort(Protocol):
    def persist_state(
        self,
        *,
        run_id: str,
        expected_ocs: str,
        host: str,
        authority_ref: str,
        state_version: int,
        predecessor_hash: str | None,
        state: dict[str, Any],
        trace_id: str,
    ) -> Any: ...

    def recover_state(
        self,
        *,
        run_id: str,
        expected_ocs: str,
        host: str,
        authority_ref: str,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class AuthorizedPersistRequest:
    run_id: str
    ocs: str
    host: str
    state_version: int
    predecessor_hash: str | None
    state: dict[str, Any]
    idempotency_key: str
    correlation_id: str
    causation_id: str | None


@dataclass(frozen=True)
class HazelPersistReadback:
    run_id: str
    decision: AuthorizationDecision
    persisted: bool
    recovered: bool
    mutation_count: int
    state_version: int | None
    event_hash: str | None
    payload_hash: str | None
    idempotent_replay: bool = False


class CommandHazelAdapter:
    """B5 adapter from an authorized Kernel decision to Hazel continuity.

    Hazel is persistence/recovery only. It never decides authority. A DENY/HOLD decision
    cannot cross the mutation boundary. Persistence is only proven after Hazel readback.
    """

    def __init__(self, hazel: HazelContinuityPort) -> None:
        self._hazel = hazel
        self._idempotency: dict[str, HazelPersistReadback] = {}

    def persist(
        self,
        decision: KernelDecisionReadback,
        request: AuthorizedPersistRequest,
    ) -> HazelPersistReadback:
        authorized = (
            decision.decision is AuthorizationDecision.ALLOW
            and decision.envelope_issued
        )
        if not authorized:
            return HazelPersistReadback(
                run_id=request.run_id,
                decision=decision.decision,
                persisted=False,
                recovered=False,
                mutation_count=0,
                state_version=None,
                event_hash=None,
                payload_hash=None,
            )
        self._validate_binding(decision, request)
        previous = self._idempotency.get(request.idempotency_key)
        if previous is not None:
            return replace(previous, mutation_count=0, idempotent_replay=True)
        self._validate_predecessor(decision, request)
        state = dict(request.state)
        state["command_causality"] = {
            "idempotency_key": request.idempotency_key,
            "correlation_id": request.correlation_id,
            "causation_id": request.causation_id,
            "expected_state_ref": decision.expected_state_ref,
            "expected_state_version": decision.expected_state_version,
        }
        persisted = self._hazel.persist_state(
            run_id=request.run_id,
            expected_ocs=request.ocs,
            host=request.host,
            authority_ref=decision.authority_ref,
            state_version=request.state_version,
            predecessor_hash=request.predecessor_hash,
            state=state,
            trace_id=decision.trace_id,
        )
        receipt = persisted.receipt
        recovered = self._hazel.recover_state(
            run_id=request.run_id,
            expected_ocs=request.ocs,
            host=request.host,
            authority_ref=decision.authority_ref,
        )
        self._validate_readback(request, receipt, recovered)
        readback = HazelPersistReadback(
            run_id=request.run_id,
            decision=decision.decision,
            persisted=True,
            recovered=True,
            mutation_count=1,
            state_version=request.state_version,
            event_hash=self._string(receipt.get("event_hash")),
            payload_hash=self._string(receipt.get("payload_hash")),
        )
        self._idempotency[request.idempotency_key] = readback
        return readback

    def recover(
        self,
        decision: KernelDecisionReadback,
        *,
        run_id: str,
        ocs: str,
        host: str,
    ) -> dict[str, Any]:
        authorized = (
            decision.decision is AuthorizationDecision.ALLOW
            and decision.envelope_issued
        )
        if not authorized:
            raise HazelIntegrationError("kernel_authorization_required")
        return self._hazel.recover_state(
            run_id=run_id,
            expected_ocs=ocs,
            host=host,
            authority_ref=decision.authority_ref,
        )

    @staticmethod
    def _validate_binding(
        decision: KernelDecisionReadback,
        request: AuthorizedPersistRequest,
    ) -> None:
        if request.idempotency_key != decision.idempotency_key:
            raise HazelIntegrationError("command_hazel_idempotency_binding_mismatch")
        if request.correlation_id != decision.correlation_id:
            raise HazelIntegrationError("command_hazel_correlation_binding_mismatch")
        if request.causation_id != decision.causation_id:
            raise HazelIntegrationError("command_hazel_causation_binding_mismatch")
        if request.state_version <= 0:
            raise HazelIntegrationError("command_hazel_state_version_invalid")

    def _validate_predecessor(
        self,
        decision: KernelDecisionReadback,
        request: AuthorizedPersistRequest,
    ) -> None:
        if request.state_version == 1:
            if request.predecessor_hash is not None:
                raise HazelIntegrationError("command_hazel_initial_predecessor_invalid")
            return
        current = self._hazel.recover_state(
            run_id=request.run_id,
            expected_ocs=request.ocs,
            host=request.host,
            authority_ref=decision.authority_ref,
        )
        if current.get("event_hash") != request.predecessor_hash:
            raise HazelIntegrationError("command_hazel_predecessor_drift")
        current_version = current.get("state_version")
        version_drift = (
            not isinstance(current_version, int)
            or current_version + 1 != request.state_version
        )
        if version_drift:
            raise HazelIntegrationError("command_hazel_version_drift")

    @staticmethod
    def _validate_readback(
        request: AuthorizedPersistRequest,
        receipt: dict[str, Any],
        recovered: dict[str, Any],
    ) -> None:
        if not receipt.get("accepted"):
            raise HazelIntegrationError("command_hazel_persist_not_accepted")
        for field in ("event_hash", "payload_hash", "state_version"):
            if recovered.get(field) != receipt.get(field):
                raise HazelIntegrationError(f"command_hazel_readback_mismatch:{field}")
        if recovered.get("state_version") != request.state_version:
            raise HazelIntegrationError("command_hazel_readback_version_mismatch")
        payload = recovered.get("payload")
        if not isinstance(payload, dict):
            raise HazelIntegrationError("command_hazel_readback_payload_invalid")
        causality = payload.get("command_causality")
        if not isinstance(causality, dict):
            raise HazelIntegrationError("command_hazel_causality_missing")
        if causality.get("idempotency_key") != request.idempotency_key:
            raise HazelIntegrationError("command_hazel_idempotency_readback_mismatch")

    @staticmethod
    def _string(value: object) -> str | None:
        return value if isinstance(value, str) else None
