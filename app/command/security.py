from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.memberships.domain.enums import MembershipRole
from app.profile_bindings.profiles import PROFILES


class CommandSecurityDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class CommandSecurityRequest:
    request_id: str
    organization_id: str
    expected_organization_id: str
    role: MembershipRole
    ocs_id: str
    namespace: str
    idempotency_key: str
    payload: dict[str, Any]
    founder_sensitive: bool = False


@dataclass(frozen=True)
class CommandSecurityReadback:
    request_id: str
    decision: CommandSecurityDecision
    reason: str
    mutation_count: int
    idempotent_replay: bool
    audit: dict[str, Any]


class CommandSecurityGuard:
    """Fail-closed Command request guard with no authority creation.

    The guard validates organization, role, OCS namespace and replay semantics.
    It never expands a capability into authority and never executes the request.
    """

    _READ_ROLES = frozenset({MembershipRole.OWNER, MembershipRole.ADMIN})
    _SECRET_MARKERS = (
        "authorization",
        "password",
        "secret",
        "token",
        "api_key",
        "apikey",
    )

    def __init__(self) -> None:
        self._replay_fingerprints: dict[str, str] = {}

    def evaluate(self, request: CommandSecurityRequest) -> CommandSecurityReadback:
        validation_error = self._validate_required(request)
        if validation_error is not None:
            return self._deny(request, validation_error)
        if request.organization_id != request.expected_organization_id:
            return self._deny(request, "command_security_organization_mismatch")
        if request.role not in self._READ_ROLES:
            return self._deny(request, "command_security_role_forbidden")
        if request.founder_sensitive and request.role is not MembershipRole.OWNER:
            return self._deny(request, "command_security_founder_role_required")

        profile = PROFILES.get(request.ocs_id)
        if profile is None:
            return self._deny(request, "command_security_unknown_ocs")
        allowed_namespaces = {profile.state_namespace, profile.memory_namespace}
        if request.namespace not in allowed_namespaces:
            return self._deny(request, "command_security_namespace_mismatch")

        fingerprint = self._fingerprint(request)
        previous = self._replay_fingerprints.get(request.idempotency_key)
        if previous is not None:
            if previous != fingerprint:
                return self._deny(request, "command_security_idempotency_conflict")
            return self._allow(request, idempotent_replay=True)

        self._replay_fingerprints[request.idempotency_key] = fingerprint
        return self._allow(request, idempotent_replay=False)

    @staticmethod
    def _validate_required(request: CommandSecurityRequest) -> str | None:
        required = {
            "request_id": request.request_id,
            "organization_id": request.organization_id,
            "expected_organization_id": request.expected_organization_id,
            "ocs_id": request.ocs_id,
            "namespace": request.namespace,
            "idempotency_key": request.idempotency_key,
        }
        missing = sorted(name for name, value in required.items() if not value)
        if missing:
            return f"command_security_request_incomplete:{','.join(missing)}"
        return None

    def _allow(
        self,
        request: CommandSecurityRequest,
        *,
        idempotent_replay: bool,
    ) -> CommandSecurityReadback:
        return CommandSecurityReadback(
            request_id=request.request_id,
            decision=CommandSecurityDecision.ALLOW,
            reason=(
                "command_security_idempotent_replay"
                if idempotent_replay
                else "command_security_validated"
            ),
            mutation_count=0,
            idempotent_replay=idempotent_replay,
            audit=self._audit(request, CommandSecurityDecision.ALLOW),
        )

    def _deny(
        self,
        request: CommandSecurityRequest,
        reason: str,
    ) -> CommandSecurityReadback:
        return CommandSecurityReadback(
            request_id=request.request_id,
            decision=CommandSecurityDecision.DENY,
            reason=reason,
            mutation_count=0,
            idempotent_replay=False,
            audit=self._audit(request, CommandSecurityDecision.DENY, reason=reason),
        )

    def _audit(
        self,
        request: CommandSecurityRequest,
        decision: CommandSecurityDecision,
        *,
        reason: str | None = None,
    ) -> dict[str, Any]:
        return {
            "request_id": request.request_id,
            "organization_id": request.organization_id,
            "role": request.role.value,
            "ocs_id": request.ocs_id,
            "namespace": request.namespace,
            "idempotency_key_hash": self._hash_text(request.idempotency_key),
            "founder_sensitive": request.founder_sensitive,
            "decision": decision.value,
            "reason": reason,
            "payload": self.redact(request.payload),
        }

    @classmethod
    def redact(cls, value: Any) -> Any:
        if isinstance(value, dict):
            result: dict[str, Any] = {}
            for key, item in value.items():
                normalized = key.casefold()
                if any(marker in normalized for marker in cls._SECRET_MARKERS):
                    result[key] = "[REDACTED]"
                else:
                    result[key] = cls.redact(item)
            return result
        if isinstance(value, list):
            return [cls.redact(item) for item in value]
        if isinstance(value, tuple):
            return [cls.redact(item) for item in value]
        return value

    @staticmethod
    def _fingerprint(request: CommandSecurityRequest) -> str:
        material = {
            "organization_id": request.organization_id,
            "role": request.role.value,
            "ocs_id": request.ocs_id,
            "namespace": request.namespace,
            "payload": request.payload,
            "founder_sensitive": request.founder_sensitive,
        }
        raw = json.dumps(
            material,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_text(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()


def command_security_posture() -> dict[str, Any]:
    return {
        "authentication": "required",
        "institutional_organization_binding": "required",
        "role_enforcement": "owner_or_admin",
        "founder_sensitive_role": "owner_only",
        "namespace_isolation": "profile_bound",
        "request_validation": "fail_closed",
        "replay_idempotency_protection": "implemented_in_guard",
        "secret_handling": "audit_redaction",
        "auditability": "structured_readback_not_durable_audit_log",
        "device_session_binding": "not_materialized",
        "authority_bypass": "forbidden",
        "cross_ocs_write": "forbidden",
    }
