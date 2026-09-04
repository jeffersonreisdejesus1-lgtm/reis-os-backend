from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import hmac
import json
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.universal_kernel.identity import (
    ActiveIdentityBinding,
    IdentityAuditLog,
    IdentityKernelGuard,
    IdentityRecheckTrigger,
)


class HazelIntegrationError(RuntimeError):
    pass


class HazelTransport(Protocol):
    def persist(self, envelope: dict[str, Any]) -> dict[str, Any]: ...
    def recover(self, request: dict[str, Any]) -> dict[str, Any]: ...


class HazelHTTPTransport:
    """Authenticated HTTP transport to Hazel Core Gateway.

    The shared secret authenticates the service boundary; it grants no REIS OS authority.
    """

    def __init__(self, *, base_url: str, shared_secret: str, timeout: float = 5.0) -> None:
        if not base_url or not shared_secret:
            raise ValueError("hazel_transport_configuration_required")
        self.base_url = base_url.rstrip("/")
        self.shared_secret = shared_secret
        self.timeout = timeout

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        signature = hmac.new(self.shared_secret.encode("utf-8"), encoded, sha256).hexdigest()
        req = Request(
            self.base_url + path,
            data=encoded,
            method="POST",
            headers={"Content-Type": "application/json", "X-Hazel-Signature": signature},
        )
        try:
            with urlopen(req, timeout=self.timeout) as response:  # noqa: S310 - fixed configured service URL
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise HazelIntegrationError(f"hazel_http_{exc.code}:{detail}") from exc
        except URLError as exc:
            raise HazelIntegrationError("hazel_unavailable") from exc
        if not isinstance(payload, dict):
            raise HazelIntegrationError("hazel_invalid_response")
        return payload

    def persist(self, envelope: dict[str, Any]) -> dict[str, Any]:
        return self._post("/v1/continuity/persist", envelope)

    def recover(self, request: dict[str, Any]) -> dict[str, Any]:
        return self._post("/v1/continuity/recover", request)


@dataclass(frozen=True)
class HazelPersistResult:
    receipt: dict[str, Any]
    binding: ActiveIdentityBinding


class HazelBoundContinuity:
    """Kernel-bound continuity path.

    KERNEL -> Hazel writes are admitted only after PRE_PERSIST identity validation and
    an exact authority-reference match. Hazel recovery is admitted only after local
    identity recovery and COLD_START revalidation. Hazel never creates identity,
    authority or a foreign OCS namespace.
    """

    def __init__(self, *, guard: IdentityKernelGuard, transport: HazelTransport) -> None:
        self.guard = guard
        self.transport = transport

    @staticmethod
    def _binding_hash(binding: ActiveIdentityBinding) -> str:
        return IdentityAuditLog.binding_hash(binding)

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
    ) -> HazelPersistResult:
        binding = self.guard.require_valid(
            run_id=run_id,
            expected_ocs=expected_ocs,
            trigger=IdentityRecheckTrigger.PRE_PERSIST,
            host=host,
        )
        if authority_ref != binding.authority_envelope_ref:
            raise HazelIntegrationError("authority_ref_mismatch")
        envelope = {
            "run_id": binding.run_id,
            "ocs_id": binding.ocs_id,
            "state_namespace": binding.state_namespace,
            "memory_namespace": binding.memory_namespace,
            "profile_version": binding.profile_version,
            "binding_hash": self._binding_hash(binding),
            "predecessor_hash": predecessor_hash,
            "authority_ref": authority_ref,
            "state_version": state_version,
            "payload": state,
            "trace_id": trace_id,
        }
        receipt = self.transport.persist(envelope)
        if not receipt.get("accepted"):
            raise HazelIntegrationError("hazel_persist_not_accepted")
        if receipt.get("ocs_id") != binding.ocs_id or receipt.get("state_namespace") != binding.state_namespace:
            raise HazelIntegrationError("hazel_receipt_namespace_mismatch")
        self.guard.audit_log.append(
            "HAZEL_PERSIST_RECEIPT",
            binding,
            details={
                "trace_id": trace_id,
                "event_hash": receipt.get("event_hash"),
                "payload_hash": receipt.get("payload_hash"),
                "state_version": state_version,
            },
        )
        return HazelPersistResult(receipt=receipt, binding=binding)

    def recover_state(
        self,
        *,
        run_id: str,
        expected_ocs: str,
        host: str,
        authority_ref: str,
    ) -> dict[str, Any]:
        binding = self.guard.binding_for(run_id)
        if binding is None:
            binding = self.guard.recover_state(run_id)
        binding = self.guard.require_valid(
            run_id=run_id,
            expected_ocs=expected_ocs,
            trigger=IdentityRecheckTrigger.COLD_START,
            host=host,
        )
        if authority_ref != binding.authority_envelope_ref:
            raise HazelIntegrationError("authority_ref_mismatch")
        request = {
            "run_id": binding.run_id,
            "ocs_id": binding.ocs_id,
            "state_namespace": binding.state_namespace,
            "memory_namespace": binding.memory_namespace,
            "authority_ref": authority_ref,
            "binding_hash": self._binding_hash(binding),
        }
        recovered = self.transport.recover(request)
        if recovered.get("ocs_id") != binding.ocs_id:
            raise HazelIntegrationError("recovery_ocs_mismatch")
        if recovered.get("state_namespace") != binding.state_namespace:
            raise HazelIntegrationError("recovery_namespace_mismatch")
        if recovered.get("memory_namespace") != binding.memory_namespace:
            raise HazelIntegrationError("recovery_memory_namespace_mismatch")
        if recovered.get("authority_ref") != binding.authority_envelope_ref:
            raise HazelIntegrationError("recovery_authority_mismatch")
        if recovered.get("binding_hash") != self._binding_hash(binding):
            raise HazelIntegrationError("recovery_binding_mismatch")
        payload = recovered.get("payload")
        if not isinstance(payload, dict):
            raise HazelIntegrationError("recovery_payload_invalid")
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if sha256(canonical.encode("utf-8")).hexdigest() != recovered.get("payload_hash"):
            raise HazelIntegrationError("recovery_payload_integrity_failure")
        self.guard.audit_log.append(
            "HAZEL_RECOVERY_ACCEPTED",
            binding,
            details={
                "trace_id": recovered.get("trace_id"),
                "event_hash": recovered.get("event_hash"),
                "state_version": recovered.get("state_version"),
            },
        )
        return recovered
