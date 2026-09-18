from __future__ import annotations

import hmac
import json
import secrets
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from time import time
from typing import Callable

from .bootstrap_binding import BootstrapCognitiveBinding
from .universal_entrypoint import UniversalCognitiveEntrypoint


class MissionCognitiveReceiptError(RuntimeError):
    """Fail-closed error for invalid COI3 mission cognitive receipts."""


@dataclass(frozen=True, slots=True)
class MissionCognitiveReceipt:
    receipt_id: str
    mission_id: str
    cognition_cycle_id: str
    ocs_id: str
    ocs_instance_id: str
    generation: int
    brain_version: str
    brain_state_revision: str | None
    intent_hash: str
    state_hash: str
    issued_at: float
    nonce: str
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


class MissionCognitiveReceiptIssuer:
    """COI3 issuer proving a mission traversed canonical cognition.

    This receipt is evidentiary only. It cannot authorize actions or effects.
    """

    def __init__(
        self,
        *,
        signing_secret: bytes,
        entrypoint: UniversalCognitiveEntrypoint | None = None,
        clock: Callable[[], float] = time,
        nonce_factory: Callable[[], str] | None = None,
    ) -> None:
        if not signing_secret:
            raise ValueError("mission_receipt_signing_secret_required")
        self._secret = signing_secret
        self._entrypoint = entrypoint or UniversalCognitiveEntrypoint()
        self._clock = clock
        self._nonce_factory = nonce_factory or (lambda: secrets.token_hex(16))

    def issue(
        self,
        binding: BootstrapCognitiveBinding,
        *,
        intent: str,
        state_revision: str | None = None,
        state_hash: str,
        cognition_cycle_id: str,
    ) -> MissionCognitiveReceipt:
        if not intent.strip():
            raise MissionCognitiveReceiptError("mission_receipt_intent_required")
        if not state_hash.strip():
            raise MissionCognitiveReceiptError("mission_receipt_state_hash_required")
        if not cognition_cycle_id.strip():
            raise MissionCognitiveReceiptError("mission_receipt_cycle_required")
        if not binding.cognitive_path_required:
            raise MissionCognitiveReceiptError("mission_receipt_cognitive_path_not_required")
        if binding.cognition_grants_authority or binding.cognition_permits_effects:
            raise MissionCognitiveReceiptError("mission_receipt_binding_privilege_violation")

        context = binding.mission_context(intent=intent, state_revision=state_revision)
        proposal = self._entrypoint.enter(context)
        if not proposal.cognitive_path_used:
            raise MissionCognitiveReceiptError("mission_receipt_cognitive_path_missing")
        if proposal.authority_granted or proposal.effects_permitted:
            raise MissionCognitiveReceiptError("mission_receipt_privilege_violation")

        issued_at = float(self._clock())
        nonce = self._nonce_factory()
        intent_hash = sha256(intent.encode("utf-8")).hexdigest()
        receipt_id = "mcr:" + sha256(
            f"{binding.mission_id}|{cognition_cycle_id}|{nonce}".encode("utf-8")
        ).hexdigest()[:32]
        provisional = MissionCognitiveReceipt(
            receipt_id=receipt_id,
            mission_id=binding.mission_id,
            cognition_cycle_id=cognition_cycle_id,
            ocs_id=binding.ocs_id,
            ocs_instance_id=binding.ocs_instance_id,
            generation=binding.generation,
            brain_version=proposal.brain_version,
            brain_state_revision=proposal.brain_state_revision,
            intent_hash=intent_hash,
            state_hash=state_hash,
            issued_at=issued_at,
            nonce=nonce,
            status="ISSUED",
            authority_granted=False,
            effects_permitted=False,
            integrity_hash="",
            signature="",
        )
        integrity_hash = self._integrity_hash(provisional.unsigned_payload())
        signature = hmac.new(self._secret, integrity_hash.encode("utf-8"), sha256).hexdigest()
        return replace(provisional, integrity_hash=integrity_hash, signature=signature)

    def verify(self, receipt: MissionCognitiveReceipt) -> bool:
        if receipt.status != "ISSUED":
            return False
        if receipt.authority_granted or receipt.effects_permitted:
            return False
        expected_hash = self._integrity_hash(receipt.unsigned_payload())
        if not hmac.compare_digest(receipt.integrity_hash, expected_hash):
            return False
        expected_signature = hmac.new(
            self._secret, expected_hash.encode("utf-8"), sha256
        ).hexdigest()
        return hmac.compare_digest(receipt.signature, expected_signature)

    @staticmethod
    def _integrity_hash(payload: dict[str, object]) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return sha256(encoded).hexdigest()
