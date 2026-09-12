from __future__ import annotations

import hmac
import json
import secrets
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from threading import Lock
from time import time
from typing import Callable

from .mission_receipt import MissionCognitiveReceipt, MissionCognitiveReceiptIssuer


class ActionCognitiveReceiptError(RuntimeError):
    """Fail-closed error for invalid COI4 action receipts."""


@dataclass(frozen=True, slots=True)
class ActionCognitiveReceipt:
    receipt_id: str
    mission_receipt_ref: str
    mission_id: str
    cognition_cycle_id: str
    ocs_id: str
    ocs_instance_id: str
    generation: int
    brain_version: str
    brain_state_revision: str | None
    intent_hash: str
    plan_hash: str
    action_digest: str
    capability_id: str
    capability_version: str
    adapter_version: str
    authority_requirements: tuple[str, ...]
    state_hash: str
    policy_version: str
    issued_at: float
    expires_at: float
    nonce: str
    previous_receipt_hash: str | None
    status: str
    authority_granted: bool
    effects_permitted: bool
    integrity_hash: str
    signature: str

    def unsigned_payload(self) -> dict[str, object]:
        data = asdict(self)
        data.pop("integrity_hash")
        data.pop("signature")
        return data


class ActionReceiptLedger:
    """Atomic in-process anti-replay ledger for COI4 receipt consumption."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._consumed: set[str] = set()

    def consume_once(self, receipt_id: str) -> bool:
        with self._lock:
            if receipt_id in self._consumed:
                return False
            self._consumed.add(receipt_id)
            return True

    def is_consumed(self, receipt_id: str) -> bool:
        with self._lock:
            return receipt_id in self._consumed


class ActionCognitiveReceiptIssuer:
    """COI4 action receipt bound to mission cognition and exact action context.

    The receipt proves cognitive evaluation only. It never grants execution authority.
    """

    def __init__(
        self,
        *,
        signing_secret: bytes,
        mission_issuer: MissionCognitiveReceiptIssuer,
        ledger: ActionReceiptLedger | None = None,
        clock: Callable[[], float] = time,
        nonce_factory: Callable[[], str] | None = None,
        ttl_seconds: float = 300.0,
    ) -> None:
        if not signing_secret:
            raise ValueError("action_receipt_signing_secret_required")
        if ttl_seconds <= 0:
            raise ValueError("action_receipt_ttl_must_be_positive")
        self._secret = signing_secret
        self._mission_issuer = mission_issuer
        self._ledger = ledger or ActionReceiptLedger()
        self._clock = clock
        self._nonce_factory = nonce_factory or (lambda: secrets.token_hex(16))
        self._ttl = float(ttl_seconds)

    def issue(
        self,
        mission_receipt: MissionCognitiveReceipt,
        *,
        plan_hash: str,
        action_digest: str,
        capability_id: str,
        capability_version: str,
        adapter_version: str,
        authority_requirements: tuple[str, ...],
        state_hash: str,
        policy_version: str,
        previous_receipt_hash: str | None = None,
    ) -> ActionCognitiveReceipt:
        if not self._mission_issuer.verify(mission_receipt):
            raise ActionCognitiveReceiptError("action_receipt_invalid_mission_receipt")
        required = {
            "plan_hash": plan_hash,
            "action_digest": action_digest,
            "capability_id": capability_id,
            "capability_version": capability_version,
            "adapter_version": adapter_version,
            "state_hash": state_hash,
            "policy_version": policy_version,
        }
        for field, value in required.items():
            if not value.strip():
                raise ActionCognitiveReceiptError(f"action_receipt_{field}_required")
        if state_hash != mission_receipt.state_hash:
            raise ActionCognitiveReceiptError("action_receipt_stale_or_mismatched_state")
        if not authority_requirements or any(not item.strip() for item in authority_requirements):
            raise ActionCognitiveReceiptError("action_receipt_authority_requirements_required")

        issued_at = float(self._clock())
        expires_at = issued_at + self._ttl
        nonce = self._nonce_factory()
        receipt_id = "acr:" + sha256(
            f"{mission_receipt.receipt_id}|{action_digest}|{nonce}".encode("utf-8")
        ).hexdigest()[:32]
        provisional = ActionCognitiveReceipt(
            receipt_id=receipt_id,
            mission_receipt_ref=mission_receipt.receipt_id,
            mission_id=mission_receipt.mission_id,
            cognition_cycle_id=mission_receipt.cognition_cycle_id,
            ocs_id=mission_receipt.ocs_id,
            ocs_instance_id=mission_receipt.ocs_instance_id,
            generation=mission_receipt.generation,
            brain_version=mission_receipt.brain_version,
            brain_state_revision=mission_receipt.brain_state_revision,
            intent_hash=mission_receipt.intent_hash,
            plan_hash=plan_hash,
            action_digest=action_digest,
            capability_id=capability_id,
            capability_version=capability_version,
            adapter_version=adapter_version,
            authority_requirements=tuple(authority_requirements),
            state_hash=state_hash,
            policy_version=policy_version,
            issued_at=issued_at,
            expires_at=expires_at,
            nonce=nonce,
            previous_receipt_hash=previous_receipt_hash,
            status="ISSUED",
            authority_granted=False,
            effects_permitted=False,
            integrity_hash="",
            signature="",
        )
        integrity_hash = self._integrity_hash(provisional.unsigned_payload())
        signature = hmac.new(self._secret, integrity_hash.encode("utf-8"), sha256).hexdigest()
        return replace(provisional, integrity_hash=integrity_hash, signature=signature)

    def verify(self, receipt: ActionCognitiveReceipt, *, now: float | None = None) -> bool:
        if receipt.status != "ISSUED":
            return False
        if receipt.authority_granted or receipt.effects_permitted:
            return False
        if self._ledger.is_consumed(receipt.receipt_id):
            return False
        current_time = float(self._clock() if now is None else now)
        if current_time >= receipt.expires_at or receipt.expires_at <= receipt.issued_at:
            return False
        expected_hash = self._integrity_hash(receipt.unsigned_payload())
        if not hmac.compare_digest(receipt.integrity_hash, expected_hash):
            return False
        expected_signature = hmac.new(
            self._secret, expected_hash.encode("utf-8"), sha256
        ).hexdigest()
        return hmac.compare_digest(receipt.signature, expected_signature)

    def consume(self, receipt: ActionCognitiveReceipt, *, now: float | None = None) -> ActionCognitiveReceipt:
        if not self.verify(receipt, now=now):
            raise ActionCognitiveReceiptError("action_receipt_invalid_expired_or_consumed")
        if not self._ledger.consume_once(receipt.receipt_id):
            raise ActionCognitiveReceiptError("action_receipt_replay_denied")
        return replace(receipt, status="CONSUMED")

    @staticmethod
    def _integrity_hash(payload: dict[str, object]) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return sha256(encoded).hexdigest()
