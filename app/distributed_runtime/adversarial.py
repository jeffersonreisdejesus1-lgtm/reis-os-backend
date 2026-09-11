from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class InfraDecision(str, Enum):
    ACCEPT = "ACCEPT"
    HOLD = "HOLD"
    DENY = "DENY"
    DUPLICATE = "DUPLICATE"
    RECONCILE = "RECONCILE"


@dataclass(frozen=True, slots=True)
class AdversarialEnvelope:
    message_id: str
    mission_id: str
    source_ocs: str
    target_ocs: str
    target_generation: int
    payload: dict[str, Any]
    payload_hash: str
    idempotency_key: str
    sequence: int
    created_at: float
    expires_at: float

    @classmethod
    def build(
        cls,
        *,
        message_id: str,
        mission_id: str,
        source_ocs: str,
        target_ocs: str,
        target_generation: int,
        payload: dict[str, Any],
        idempotency_key: str,
        sequence: int,
        ttl_seconds: float = 60.0,
        now: float | None = None,
    ) -> "AdversarialEnvelope":
        now = time.time() if now is None else now
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        return cls(
            message_id=message_id,
            mission_id=mission_id,
            source_ocs=source_ocs,
            target_ocs=target_ocs,
            target_generation=target_generation,
            payload=payload,
            payload_hash=hashlib.sha256(encoded).hexdigest(),
            idempotency_key=idempotency_key,
            sequence=sequence,
            created_at=now,
            expires_at=now + ttl_seconds,
        )


@dataclass(slots=True)
class EvidenceRecord:
    event: str
    decision: InfraDecision
    detail: str


@dataclass(slots=True)
class SharedInfrastructureHarness:
    current_generation: dict[str, int]
    namespace_owner: dict[str, str]
    state_version: dict[str, int] = field(default_factory=dict)
    processed_idempotency_keys: set[str] = field(default_factory=set)
    last_sequence_by_mission: dict[str, int] = field(default_factory=dict)
    evidence: list[EvidenceRecord] = field(default_factory=list)
    authority_validator_available: bool = True
    message_bus_available: bool = True
    state_store_available: bool = True
    evidence_ledger_available: bool = True

    def _record(self, event: str, decision: InfraDecision, detail: str) -> InfraDecision:
        self.evidence.append(EvidenceRecord(event, decision, detail))
        return decision

    def receive(self, envelope: AdversarialEnvelope, *, now: float | None = None) -> InfraDecision:
        now = time.time() if now is None else now
        if not self.message_bus_available:
            return self._record("bus_outage", InfraDecision.HOLD, "cross_ocs_handoff_hold")
        if envelope.expires_at < now:
            return self._record("expired_replay", InfraDecision.DENY, "message_expired")
        if envelope.target_generation != self.current_generation.get(envelope.target_ocs):
            return self._record("stale_generation", InfraDecision.DENY, "target_generation_mismatch")
        encoded = json.dumps(envelope.payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        if hashlib.sha256(encoded).hexdigest() != envelope.payload_hash:
            return self._record("payload_mutation", InfraDecision.DENY, "payload_hash_mismatch")
        if not envelope.message_id or not envelope.idempotency_key or not envelope.mission_id:
            return self._record("queue_poisoning", InfraDecision.DENY, "invalid_envelope_identity")
        if envelope.idempotency_key in self.processed_idempotency_keys:
            return self._record("duplicate_delivery", InfraDecision.DUPLICATE, "effect_deduplicated")
        previous = self.last_sequence_by_mission.get(envelope.mission_id)
        if previous is not None and envelope.sequence <= previous:
            return self._record("message_reordering", InfraDecision.HOLD, "non_monotonic_sequence")
        self.processed_idempotency_keys.add(envelope.idempotency_key)
        self.last_sequence_by_mission[envelope.mission_id] = envelope.sequence
        return self._record("message_accept", InfraDecision.ACCEPT, "validated")

    def state_write(
        self,
        *,
        writer_ocs: str,
        target_namespace: str,
        writer_generation: int,
        expected_previous_version: int,
        authority_scope_allows: bool,
    ) -> InfraDecision:
        if not self.state_store_available:
            return self._record("state_store_outage", InfraDecision.HOLD, "state_mutation_hold")
        if self.namespace_owner.get(target_namespace) != writer_ocs:
            return self._record("cross_namespace_attack", InfraDecision.DENY, "namespace_owner_mismatch")
        if writer_generation != self.current_generation.get(writer_ocs):
            return self._record("split_brain", InfraDecision.DENY, "stale_writer_generation")
        if not authority_scope_allows:
            return self._record("authority_scope", InfraDecision.DENY, "transition_not_authorized")
        actual = self.state_version.get(target_namespace, 0)
        if expected_previous_version != actual:
            return self._record("state_write_race", InfraDecision.HOLD, "cas_version_mismatch")
        self.state_version[target_namespace] = actual + 1
        return self._record("state_write", InfraDecision.ACCEPT, "committed")

    def material_commit(self, *, authority_resolved: bool = True) -> InfraDecision:
        if not self.authority_validator_available or not authority_resolved:
            return self._record("authority_resolver_outage", InfraDecision.HOLD, "no_new_material_commits")
        if not self.evidence_ledger_available:
            return self._record("evidence_ledger_outage", InfraDecision.HOLD, "no_irreversible_effects")
        return self._record("material_commit", InfraDecision.ACCEPT, "commit_allowed")

    def external_effect_after_lost_ack(self, *, provider_readback: str) -> InfraDecision:
        if provider_readback == "confirmed_applied":
            return self._record("lost_ack", InfraDecision.ACCEPT, "reconciled_applied")
        if provider_readback == "confirmed_not_applied":
            return self._record("lost_ack", InfraDecision.ACCEPT, "safe_retry_after_readback")
        return self._record("unknown_external_effect", InfraDecision.RECONCILE, "hold_and_reconcile")
