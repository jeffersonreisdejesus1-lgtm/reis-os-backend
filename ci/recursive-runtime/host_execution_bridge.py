from dataclasses import dataclass
from threading import RLock
from typing import Callable, Dict, FrozenSet, Optional
import hashlib
import json
import time


@dataclass(frozen=True)
class HostExecutionCommand:
    command_id: str
    request_id: str
    provider: str
    target: str
    capability: str
    payload_ref: str
    founder_approval_ref: str
    lease_id: str
    expires_at_unix: float
    max_effects: int
    zero_spend_attestation_ref: str
    fingerprint: str


@dataclass(frozen=True)
class HostExecutionResult:
    command_id: str
    request_id: str
    provider: str
    result_ref: str
    status: str
    executed_at_unix: float
    external_receipt_ref: str


class ApprovedHostExecutorBridge:
    """Credential-isolating bridge between ProductionEffectGateway and an approved host executor.

    The runtime never receives provider credentials. It emits a scope-bound command. An approved
    host executes that command using its own connector credentials and returns a result that must
    reconcile against the exact command fingerprint before a production commit can be acknowledged.
    """

    def __init__(
        self,
        *,
        founder_approval_ref: str,
        allowed_providers: FrozenSet[str],
        allowed_target_prefixes: FrozenSet[str],
        allowed_capabilities: FrozenSet[str],
        zero_spend_verifier: Callable[[str, str, str], str],
        clock: Optional[Callable[[], float]] = None,
    ):
        self.founder_approval_ref = founder_approval_ref
        self.allowed_providers = allowed_providers
        self.allowed_target_prefixes = allowed_target_prefixes
        self.allowed_capabilities = allowed_capabilities
        self.zero_spend_verifier = zero_spend_verifier
        self.clock = clock or time.time
        self._lock = RLock()
        self._commands: Dict[str, HostExecutionCommand] = {}
        self._results: Dict[str, HostExecutionResult] = {}

    @staticmethod
    def _fingerprint(request_id, provider, target, capability, payload_ref, founder_approval_ref, lease_id):
        raw = json.dumps({
            "request_id": request_id,
            "provider": provider,
            "target": target,
            "capability": capability,
            "payload_ref": payload_ref,
            "founder_approval_ref": founder_approval_ref,
            "lease_id": lease_id,
        }, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def prepare(self, *, request_id: str, provider: str, target: str, capability: str,
                payload_ref: str, lease_id: str, expires_at_unix: float, max_effects: int):
        with self._lock:
            if not self.founder_approval_ref:
                raise RuntimeError("FOUNDER_APPROVAL_REQUIRED")
            if provider not in self.allowed_providers:
                raise RuntimeError("HOST_PROVIDER_NOT_ALLOWED")
            if capability not in self.allowed_capabilities:
                raise RuntimeError("HOST_CAPABILITY_NOT_ALLOWED")
            if not any(target.startswith(p) for p in self.allowed_target_prefixes):
                raise RuntimeError("HOST_TARGET_NOT_ALLOWED")
            if expires_at_unix <= self.clock():
                raise RuntimeError("HOST_LEASE_EXPIRED")
            if max_effects != 1:
                raise RuntimeError("HOST_CANARY_REQUIRES_SINGLE_EFFECT_LEASE")
            cost_ref = self.zero_spend_verifier(provider, target, capability)
            if not cost_ref:
                raise RuntimeError("HOST_ZERO_SPEND_NOT_VERIFIED")
            fp = self._fingerprint(request_id, provider, target, capability, payload_ref,
                                   self.founder_approval_ref, lease_id)
            command_id = f"hostcmd:{fp[:24]}"
            command = HostExecutionCommand(
                command_id=command_id,
                request_id=request_id,
                provider=provider,
                target=target,
                capability=capability,
                payload_ref=payload_ref,
                founder_approval_ref=self.founder_approval_ref,
                lease_id=lease_id,
                expires_at_unix=expires_at_unix,
                max_effects=max_effects,
                zero_spend_attestation_ref=cost_ref,
                fingerprint=fp,
            )
            existing = self._commands.get(command_id)
            if existing is not None and existing != command:
                raise RuntimeError("HOST_COMMAND_CONFLICT")
            self._commands[command_id] = command
            return command

    def reconcile(self, command: HostExecutionCommand, *, result_ref: str,
                  external_receipt_ref: str, status: str = "COMMITTED"):
        with self._lock:
            current = self._commands.get(command.command_id)
            if current != command:
                raise RuntimeError("HOST_COMMAND_NOT_PREPARED")
            expected = self._fingerprint(command.request_id, command.provider, command.target,
                                         command.capability, command.payload_ref,
                                         command.founder_approval_ref, command.lease_id)
            if command.fingerprint != expected:
                raise RuntimeError("HOST_COMMAND_FINGERPRINT_MISMATCH")
            if status != "COMMITTED":
                raise RuntimeError("HOST_EFFECT_NOT_COMMITTED")
            if not result_ref or not external_receipt_ref:
                raise RuntimeError("HOST_RESULT_EVIDENCE_REQUIRED")
            result = HostExecutionResult(
                command_id=command.command_id,
                request_id=command.request_id,
                provider=command.provider,
                result_ref=result_ref,
                status=status,
                executed_at_unix=self.clock(),
                external_receipt_ref=external_receipt_ref,
            )
            existing = self._results.get(command.command_id)
            if existing is not None:
                if existing != result:
                    raise RuntimeError("HOST_RESULT_CONFLICT")
                return existing
            self._results[command.command_id] = result
            return result

    def result_for_request(self, request_id: str):
        with self._lock:
            for result in self._results.values():
                if result.request_id == request_id:
                    return result
            return None
