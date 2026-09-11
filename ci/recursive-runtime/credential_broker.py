from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Dict, FrozenSet, Tuple
import hashlib
import json
import time

from orchestrator_effect_bridge import PreparedEffect


AI_ACTOR_CLASSES = frozenset({
    "AI", "OCS", "CHATGPT", "CODEX", "CLAUDE", "GEMINI", "GROK",
    "COPILOT", "REPLIT_AGENT", "CUSTOM_AGENT", "MODEL_RUNTIME",
})

FOUNDER_ONLY_CAPABILITIES = frozenset({
    "GITHUB_MERGE_PR",
    "PROMOTE_PRODUCTION",
    "DELETE_CANONICAL_RESOURCE",
    "EXPAND_AUTHORITY",
    "CHANGE_INSTITUTIONAL_POLICY",
})


@dataclass(frozen=True)
class ProviderIsolationAttestation:
    provider: str
    credential_owner: str
    direct_ai_write_access_removed: bool
    alternate_write_paths_reviewed: bool
    evidence_ref: str
    observed_at_unix: float
    valid_until_unix: float


@dataclass(frozen=True)
class ExecutionGrant:
    grant_id: str
    request_id: str
    provider: str
    target: str
    capability: str
    payload_ref: str
    host_executor_id: str
    expires_at_unix: float
    fingerprint: str


@dataclass(frozen=True)
class BrokerAuditEvent:
    event_id: str
    kind: str
    actor_class: str
    actor_id: str
    provider: str
    target: str
    capability: str
    decision: str
    reason: str


class CredentialBroker:
    """Credential isolation boundary.

    It never returns provider credentials. AI actors may submit an already-authorized
    PreparedEffect, but only an approved non-AI host executor may consume the resulting
    one-shot opaque grant. Activation requires provider-side isolation attestation.
    """

    def __init__(self, *, approved_host_executors: FrozenSet[str], clock=None):
        if not approved_host_executors:
            raise RuntimeError("APPROVED_HOST_EXECUTOR_REQUIRED")
        self.approved_host_executors = approved_host_executors
        self.clock = clock or time.time
        self._lock = RLock()
        self._attestations: Dict[str, ProviderIsolationAttestation] = {}
        self._grants: Dict[str, ExecutionGrant] = {}
        self._consumed: set[str] = set()
        self._audit: list[BrokerAuditEvent] = []

    def _audit_event(self, *, kind, actor_class, actor_id, provider, target,
                     capability, decision, reason):
        raw = f"{kind}|{actor_class}|{actor_id}|{provider}|{target}|{capability}|{decision}|{reason}|{len(self._audit)}"
        event_id = "audit:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
        self._audit.append(BrokerAuditEvent(
            event_id, kind, actor_class, actor_id, provider, target,
            capability, decision, reason,
        ))

    def register_isolation_attestation(self, attestation: ProviderIsolationAttestation):
        now = self.clock()
        if not attestation.evidence_ref:
            raise RuntimeError("ISOLATION_EVIDENCE_REQUIRED")
        if not attestation.direct_ai_write_access_removed:
            raise RuntimeError("DIRECT_AI_WRITE_ACCESS_STILL_PRESENT")
        if not attestation.alternate_write_paths_reviewed:
            raise RuntimeError("ALTERNATE_WRITE_PATHS_NOT_REVIEWED")
        if attestation.valid_until_unix <= now:
            raise RuntimeError("ISOLATION_ATTESTATION_EXPIRED")
        if attestation.credential_owner not in self.approved_host_executors:
            raise RuntimeError("CREDENTIAL_OWNER_NOT_APPROVED_HOST")
        self._attestations[attestation.provider] = attestation
        return attestation

    def request_raw_credential(self, *, actor_class: str, actor_id: str, provider: str):
        actor_class = actor_class.upper()
        self._audit_event(
            kind="RAW_CREDENTIAL_REQUEST", actor_class=actor_class, actor_id=actor_id,
            provider=provider, target="", capability="RAW_CREDENTIAL", decision="DENY",
            reason="RAW_CREDENTIAL_EXPORT_FORBIDDEN",
        )
        raise RuntimeError("RAW_CREDENTIAL_EXPORT_FORBIDDEN")

    @staticmethod
    def _fingerprint(prepared: PreparedEffect, provider: str, host_executor_id: str):
        raw = json.dumps({
            "request_id": prepared.request.request_id,
            "provider": provider,
            "target": prepared.request.target,
            "capability": prepared.request.capability,
            "payload_ref": prepared.request.payload_ref,
            "authority_ref": prepared.request.authority_ref,
            "mission_binding": prepared.request.mission_binding,
            "lease_id": prepared.lease.lease_id,
            "host_executor_id": host_executor_id,
            "expires_at": prepared.lease.expires_at_unix,
        }, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def issue_grant(self, *, actor_class: str, actor_id: str, provider: str,
                    host_executor_id: str, prepared: PreparedEffect) -> ExecutionGrant:
        with self._lock:
            now = self.clock()
            actor_class = actor_class.upper()
            attestation = self._attestations.get(provider)
            if attestation is None:
                self._audit_event(kind="GRANT_REQUEST", actor_class=actor_class, actor_id=actor_id,
                                  provider=provider, target=prepared.request.target,
                                  capability=prepared.request.capability, decision="DENY",
                                  reason="PROVIDER_ISOLATION_NOT_ATTESTED")
                raise RuntimeError("PROVIDER_ISOLATION_NOT_ATTESTED")
            if attestation.valid_until_unix <= now:
                raise RuntimeError("ISOLATION_ATTESTATION_EXPIRED")
            if host_executor_id not in self.approved_host_executors:
                raise RuntimeError("HOST_EXECUTOR_NOT_APPROVED")
            if prepared.request.capability in FOUNDER_ONLY_CAPABILITIES:
                raise RuntimeError("FOUNDER_ONLY_CAPABILITY_FORBIDDEN")
            if prepared.lease.max_effects != 1:
                raise RuntimeError("ONE_SHOT_LEASE_REQUIRED")
            if prepared.lease.expires_at_unix <= now:
                raise RuntimeError("LEASE_EXPIRED")
            if prepared.policy.allow_github_merge:
                raise RuntimeError("MERGE_POLICY_FORBIDDEN")
            fp = self._fingerprint(prepared, provider, host_executor_id)
            grant_id = "grant:" + fp[:24]
            grant = ExecutionGrant(
                grant_id=grant_id,
                request_id=prepared.request.request_id,
                provider=provider,
                target=prepared.request.target,
                capability=prepared.request.capability,
                payload_ref=prepared.request.payload_ref,
                host_executor_id=host_executor_id,
                expires_at_unix=prepared.lease.expires_at_unix,
                fingerprint=fp,
            )
            existing = self._grants.get(grant_id)
            if existing is not None and existing != grant:
                raise RuntimeError("GRANT_CONFLICT")
            self._grants[grant_id] = grant
            self._audit_event(kind="GRANT_REQUEST", actor_class=actor_class, actor_id=actor_id,
                              provider=provider, target=grant.target, capability=grant.capability,
                              decision="ALLOW", reason="ONE_SHOT_OPAQUE_GRANT")
            return grant

    def consume_grant(self, *, grant: ExecutionGrant, host_executor_id: str) -> ExecutionGrant:
        with self._lock:
            now = self.clock()
            current = self._grants.get(grant.grant_id)
            if current != grant:
                raise RuntimeError("UNKNOWN_OR_TAMPERED_GRANT")
            if host_executor_id != grant.host_executor_id or host_executor_id not in self.approved_host_executors:
                raise RuntimeError("HOST_EXECUTOR_MISMATCH")
            if grant.expires_at_unix <= now:
                raise RuntimeError("GRANT_EXPIRED")
            if grant.grant_id in self._consumed:
                raise RuntimeError("GRANT_REPLAY_DENIED")
            self._consumed.add(grant.grant_id)
            self._audit_event(kind="GRANT_CONSUME", actor_class="NON_AI_HOST", actor_id=host_executor_id,
                              provider=grant.provider, target=grant.target, capability=grant.capability,
                              decision="ALLOW", reason="GRANT_CONSUMED")
            return grant

    def audit_events(self) -> Tuple[BrokerAuditEvent, ...]:
        with self._lock:
            return tuple(self._audit)
