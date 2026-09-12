from __future__ import annotations

import hmac
import json
import secrets
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from time import time
from typing import Callable

from .action_receipt import ActionCognitiveReceipt, ActionCognitiveReceiptIssuer
from .capability_fabric import CapabilityDiscoveryResult, InstitutionalCapabilityFabric


class AuthorityAwareDiscoveryError(RuntimeError):
    """Fail-closed denial raised by the COI8 authority boundary."""


@dataclass(frozen=True, slots=True)
class AuthorityGrant:
    authority_id: str
    mission_id: str
    ocs_id: str
    capability_id: str
    adapter_version: str
    operation_class: str
    policy_version: str
    authority_requirements: tuple[str, ...]
    valid_from: float
    valid_until: float
    revoked: bool = False

    def validate(self) -> None:
        required = {
            "authority_id": self.authority_id,
            "mission_id": self.mission_id,
            "ocs_id": self.ocs_id,
            "capability_id": self.capability_id,
            "adapter_version": self.adapter_version,
            "operation_class": self.operation_class,
            "policy_version": self.policy_version,
        }
        for field, value in required.items():
            if not value.strip():
                raise AuthorityAwareDiscoveryError(f"authority_{field}_required")
        if self.operation_class not in {"CLASS_0", "CLASS_1", "CLASS_2", "CLASS_3", "CLASS_4"}:
            raise AuthorityAwareDiscoveryError("authority_operation_class_invalid")
        if not self.authority_requirements or any(not item.strip() for item in self.authority_requirements):
            raise AuthorityAwareDiscoveryError("authority_requirements_required")
        if self.valid_until <= self.valid_from:
            raise AuthorityAwareDiscoveryError("authority_invalid_lifetime")


@dataclass(frozen=True, slots=True)
class AuthorityReceipt:
    receipt_id: str
    authority_id: str
    action_receipt_id: str
    mission_id: str
    ocs_id: str
    capability_id: str
    adapter_version: str
    operation_class: str
    policy_version: str
    action_digest: str
    issued_at: float
    expires_at: float
    nonce: str
    status: str
    integrity_hash: str
    signature: str

    def unsigned_payload(self) -> dict[str, object]:
        data = asdict(self)
        data.pop("integrity_hash")
        data.pop("signature")
        return data


@dataclass(frozen=True, slots=True)
class AuthorityAwareDiscoveryResult:
    capability_discovery: CapabilityDiscoveryResult
    authority_receipt: AuthorityReceipt
    authority_snapshot: str
    governed_discovery_receipt: str


class InstitutionalAuthorityRegistry:
    def __init__(self) -> None:
        self._grants: dict[str, AuthorityGrant] = {}

    def register(self, grant: AuthorityGrant) -> None:
        grant.validate()
        if grant.authority_id in self._grants:
            raise AuthorityAwareDiscoveryError("authority_duplicate_registration")
        self._grants[grant.authority_id] = grant

    def revoke(self, authority_id: str) -> None:
        grant = self._grants.get(authority_id)
        if grant is None:
            raise AuthorityAwareDiscoveryError("authority_not_registered")
        self._grants[authority_id] = replace(grant, revoked=True)

    def resolve(self, authority_id: str) -> AuthorityGrant:
        grant = self._grants.get(authority_id)
        if grant is None:
            raise AuthorityAwareDiscoveryError("authority_not_registered")
        grant.validate()
        return grant


class AuthorityAwareCapabilityDiscovery:
    """COI8: bind capability discovery to independent, exact authority context.

    Cognitive receipts never self-authorize. Authority is resolved from an
    external registry and cryptographically receipted for the exact action,
    mission, OCS, capability, adapter, operation class and policy context.
    """

    def __init__(
        self,
        *,
        capability_fabric: InstitutionalCapabilityFabric,
        authority_registry: InstitutionalAuthorityRegistry,
        action_issuer: ActionCognitiveReceiptIssuer,
        signing_secret: bytes,
        clock: Callable[[], float] = time,
        nonce_factory: Callable[[], str] | None = None,
        ttl_seconds: float = 180.0,
    ) -> None:
        if not signing_secret:
            raise ValueError("authority_receipt_signing_secret_required")
        if ttl_seconds <= 0:
            raise ValueError("authority_receipt_ttl_must_be_positive")
        self._fabric = capability_fabric
        self._registry = authority_registry
        self._action_issuer = action_issuer
        self._secret = signing_secret
        self._clock = clock
        self._nonce_factory = nonce_factory or (lambda: secrets.token_hex(16))
        self._ttl = float(ttl_seconds)

    def discover(
        self,
        *,
        capability_id: str,
        required_schema_version: str,
        action_receipt: ActionCognitiveReceipt,
        authority_id: str,
        operation_class: str,
    ) -> AuthorityAwareDiscoveryResult:
        if not self._action_issuer.verify(action_receipt):
            raise AuthorityAwareDiscoveryError("authority_invalid_action_receipt")
        if action_receipt.capability_id != capability_id:
            raise AuthorityAwareDiscoveryError("authority_action_capability_mismatch")
        if operation_class not in {"CLASS_0", "CLASS_1", "CLASS_2", "CLASS_3", "CLASS_4"}:
            raise AuthorityAwareDiscoveryError("authority_operation_class_invalid")

        grant = self._registry.resolve(authority_id)
        now = float(self._clock())
        if grant.revoked:
            raise AuthorityAwareDiscoveryError("authority_revoked")
        if now < grant.valid_from or now >= grant.valid_until:
            raise AuthorityAwareDiscoveryError("authority_expired_or_not_yet_valid")
        exact = {
            "mission_id": (grant.mission_id, action_receipt.mission_id),
            "ocs_id": (grant.ocs_id, action_receipt.ocs_id),
            "capability_id": (grant.capability_id, action_receipt.capability_id),
            "adapter_version": (grant.adapter_version, action_receipt.adapter_version),
            "operation_class": (grant.operation_class, operation_class),
            "policy_version": (grant.policy_version, action_receipt.policy_version),
        }
        for field, (authorized, requested) in exact.items():
            if authorized != requested:
                raise AuthorityAwareDiscoveryError(f"authority_{field}_mismatch")
        if tuple(grant.authority_requirements) != tuple(action_receipt.authority_requirements):
            raise AuthorityAwareDiscoveryError("authority_requirements_mismatch")

        discovery = self._fabric.discover(
            capability_id,
            mission_id=action_receipt.mission_id,
            required_schema_version=required_schema_version,
        )
        if discovery.selected_capability.adapter_version != grant.adapter_version:
            raise AuthorityAwareDiscoveryError("authority_discovered_adapter_mismatch")

        expires_at = min(now + self._ttl, grant.valid_until, action_receipt.expires_at)
        if expires_at <= now:
            raise AuthorityAwareDiscoveryError("authority_receipt_lifetime_exhausted")
        nonce = self._nonce_factory()
        receipt_id = "authr:" + sha256(
            f"{grant.authority_id}|{action_receipt.receipt_id}|{nonce}".encode("utf-8")
        ).hexdigest()[:32]
        provisional = AuthorityReceipt(
            receipt_id=receipt_id,
            authority_id=grant.authority_id,
            action_receipt_id=action_receipt.receipt_id,
            mission_id=action_receipt.mission_id,
            ocs_id=action_receipt.ocs_id,
            capability_id=capability_id,
            adapter_version=action_receipt.adapter_version,
            operation_class=operation_class,
            policy_version=action_receipt.policy_version,
            action_digest=action_receipt.action_digest,
            issued_at=now,
            expires_at=expires_at,
            nonce=nonce,
            status="AUTHORIZED",
            integrity_hash="",
            signature="",
        )
        integrity_hash = self._digest(provisional.unsigned_payload())
        signature = hmac.new(self._secret, integrity_hash.encode("utf-8"), sha256).hexdigest()
        receipt = replace(provisional, integrity_hash=integrity_hash, signature=signature)
        authority_snapshot = self._digest(asdict(grant))
        governed_discovery_receipt = self._digest({
            "capability_discovery_receipt": discovery.discovery_receipt,
            "authority_receipt_id": receipt.receipt_id,
            "authority_integrity_hash": receipt.integrity_hash,
            "action_receipt_id": action_receipt.receipt_id,
        })
        return AuthorityAwareDiscoveryResult(
            capability_discovery=discovery,
            authority_receipt=receipt,
            authority_snapshot=authority_snapshot,
            governed_discovery_receipt=governed_discovery_receipt,
        )

    def verify_authority_receipt(
        self,
        receipt: AuthorityReceipt,
        *,
        action_receipt: ActionCognitiveReceipt,
        now: float | None = None,
    ) -> bool:
        if receipt.status != "AUTHORIZED":
            return False
        if receipt.action_receipt_id != action_receipt.receipt_id:
            return False
        current_time = float(self._clock() if now is None else now)
        if current_time >= receipt.expires_at:
            return False
        try:
            grant = self._registry.resolve(receipt.authority_id)
        except AuthorityAwareDiscoveryError:
            return False
        if grant.revoked or current_time < grant.valid_from or current_time >= grant.valid_until:
            return False
        expected_hash = self._digest(receipt.unsigned_payload())
        if not hmac.compare_digest(receipt.integrity_hash, expected_hash):
            return False
        expected_signature = hmac.new(self._secret, expected_hash.encode("utf-8"), sha256).hexdigest()
        return hmac.compare_digest(receipt.signature, expected_signature)

    @staticmethod
    def _digest(payload: object) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=list
        ).encode("utf-8")
        return sha256(encoded).hexdigest()
