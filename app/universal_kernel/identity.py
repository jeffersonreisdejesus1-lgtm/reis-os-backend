from __future__ import annotations

# ruff: noqa: E501, I001

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
from json import dumps, loads
from pathlib import Path
from time import time

from app.profile_bindings.profiles import PROFILES, OCSProfile


INSTITUTION = "REIS OS"


class IdentityBindingStatus(StrEnum):
    VALID = "valid"
    HOLD = "hold"


class IdentityRecheckTrigger(StrEnum):
    NEW_OCS_MENTION = "new_ocs_mention"
    AMBIGUOUS_PRONOUN = "ambiguous_pronoun"
    HANDOFF = "handoff"
    HOST_REFERENCE = "host_reference"
    CAUSAL_ATTRIBUTION = "causal_attribution"
    LONG_CONTEXT_DRIFT = "long_context_drift"
    IDENTITY_CONFLICT = "identity_conflict"
    PRE_ACTION = "pre_action"
    PRE_PERSIST = "pre_persist"
    PRE_HANDOFF = "pre_handoff"
    COLD_START = "cold_start"


@dataclass(frozen=True)
class ActiveIdentityBinding:
    run_id: str
    ocs_canonical_name: str
    ocs_id: str
    institution: str
    lineage_ref: str
    identity_ref: str
    constitution_ref: str
    csp_ref: str
    host: str
    session_context: str
    state_namespace: str
    memory_namespace: str
    authority_envelope_ref: str
    profile_version: str
    bound_at: float
    status: IdentityBindingStatus = IdentityBindingStatus.VALID
    hold_reason: str | None = None


@dataclass(frozen=True)
class IdentityRevalidationResult:
    valid: bool
    reason: str
    binding: ActiveIdentityBinding | None


@dataclass(frozen=True)
class IdentityLogEvent:
    sequence: int
    event_type: str
    run_id: str
    ocs_id: str
    binding: dict[str, object]
    details: dict[str, object]
    predecessor_hash: str | None
    event_hash: str


class IdentityAuditLog:
    """Hash-chained identity log suitable as a Hazel/log recovery anchor.

    Conversation text is deliberately excluded from authority. The log stores typed
    identity facts and can optionally persist them as JSONL.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = None if path is None else Path(path)
        self._events: list[IdentityLogEvent] = []
        if self._path is not None and self._path.exists():
            self._load()

    @property
    def events(self) -> tuple[IdentityLogEvent, ...]:
        return tuple(self._events)

    @staticmethod
    def _hash_payload(payload: dict[str, object]) -> str:
        raw = dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return sha256(raw.encode("utf-8")).hexdigest()

    def append(
        self,
        event_type: str,
        binding: ActiveIdentityBinding,
        *,
        details: dict[str, object] | None = None,
    ) -> IdentityLogEvent:
        sequence = len(self._events) + 1
        predecessor_hash = self._events[-1].event_hash if self._events else None
        binding_data = asdict(binding)
        binding_data["status"] = binding.status.value
        base: dict[str, object] = {
            "sequence": sequence,
            "event_type": event_type,
            "run_id": binding.run_id,
            "ocs_id": binding.ocs_id,
            "binding": binding_data,
            "details": {} if details is None else details,
            "predecessor_hash": predecessor_hash,
        }
        digest = self._hash_payload(base)
        event = IdentityLogEvent(
            sequence=sequence,
            event_type=event_type,
            run_id=binding.run_id,
            ocs_id=binding.ocs_id,
            binding=binding_data,
            details={} if details is None else details,
            predecessor_hash=predecessor_hash,
            event_hash=digest,
        )
        self._events.append(event)
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(dumps(asdict(event), sort_keys=True, ensure_ascii=False) + "\n")
        return event

    def chain_is_valid(self) -> bool:
        predecessor: str | None = None
        for expected_sequence, event in enumerate(self._events, start=1):
            if event.sequence != expected_sequence or event.predecessor_hash != predecessor:
                return False
            base: dict[str, object] = {
                "sequence": event.sequence,
                "event_type": event.event_type,
                "run_id": event.run_id,
                "ocs_id": event.ocs_id,
                "binding": event.binding,
                "details": event.details,
                "predecessor_hash": event.predecessor_hash,
            }
            if self._hash_payload(base) != event.event_hash:
                return False
            predecessor = event.event_hash
        return True

    def recover_last_valid_binding(self, run_id: str) -> ActiveIdentityBinding | None:
        if not self.chain_is_valid():
            raise RuntimeError("identity_log_integrity_failed")
        for event in reversed(self._events):
            if event.run_id != run_id:
                continue
            raw = event.binding
            status = IdentityBindingStatus(str(raw["status"]))
            binding = ActiveIdentityBinding(
                run_id=str(raw["run_id"]),
                ocs_canonical_name=str(raw["ocs_canonical_name"]),
                ocs_id=str(raw["ocs_id"]),
                institution=str(raw["institution"]),
                lineage_ref=str(raw["lineage_ref"]),
                identity_ref=str(raw["identity_ref"]),
                constitution_ref=str(raw["constitution_ref"]),
                csp_ref=str(raw["csp_ref"]),
                host=str(raw["host"]),
                session_context=str(raw["session_context"]),
                state_namespace=str(raw["state_namespace"]),
                memory_namespace=str(raw["memory_namespace"]),
                authority_envelope_ref=str(raw["authority_envelope_ref"]),
                profile_version=str(raw["profile_version"]),
                bound_at=float(raw["bound_at"]),
                status=status,
                hold_reason=(None if raw.get("hold_reason") is None else str(raw["hold_reason"])),
            )
            if binding.status is IdentityBindingStatus.VALID:
                return binding
        return None

    def _load(self) -> None:
        assert self._path is not None
        for raw_line in self._path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            data = loads(raw_line)
            self._events.append(
                IdentityLogEvent(
                    sequence=int(data["sequence"]),
                    event_type=str(data["event_type"]),
                    run_id=str(data["run_id"]),
                    ocs_id=str(data["ocs_id"]),
                    binding=dict(data["binding"]),
                    details=dict(data["details"]),
                    predecessor_hash=data["predecessor_hash"],
                    event_hash=str(data["event_hash"]),
                )
            )
        if not self.chain_is_valid():
            raise RuntimeError("identity_log_integrity_failed")


class IdentityKernelGuard:
    def __init__(
        self,
        *,
        profiles: dict[str, OCSProfile] = PROFILES,
        audit_log: IdentityAuditLog | None = None,
    ) -> None:
        self._profiles = profiles
        self._audit_log = audit_log or IdentityAuditLog()
        self._bindings: dict[str, ActiveIdentityBinding] = {}

    @property
    def audit_log(self) -> IdentityAuditLog:
        return self._audit_log

    def binding_for(self, run_id: str) -> ActiveIdentityBinding | None:
        return self._bindings.get(run_id)

    def bind_active_identity(
        self,
        *,
        run_id: str,
        ocs_id: str,
        host: str,
        session_context: str,
    ) -> ActiveIdentityBinding:
        if not run_id or not host or not session_context:
            raise ValueError("identity_binding_fields_required")
        profile = self._profiles.get(ocs_id)
        if profile is None:
            raise ValueError("unknown_ocs_identity")
        binding = ActiveIdentityBinding(
            run_id=run_id,
            ocs_canonical_name=profile.ocs_id,
            ocs_id=profile.ocs_id,
            institution=INSTITUTION,
            lineage_ref=profile.ancestry,
            identity_ref=profile.identity,
            constitution_ref=profile.constitution_ref,
            csp_ref=profile.csp_ref,
            host=host,
            session_context=session_context,
            state_namespace=profile.state_namespace,
            memory_namespace=profile.memory_namespace,
            authority_envelope_ref=profile.authority_envelope_ref,
            profile_version=profile.version,
            bound_at=time(),
        )
        self._bindings[run_id] = binding
        self._audit_log.append("BIND_ACTIVE_IDENTITY", binding)
        return binding

    def recover_state(self, run_id: str) -> ActiveIdentityBinding:
        recovered = self._audit_log.recover_last_valid_binding(run_id)
        if recovered is None:
            raise ValueError("identity_recovery_source_missing")
        self._validate_profile_binding(recovered)
        self._bindings[run_id] = recovered
        self._audit_log.append("RECOVER_IDENTITY", recovered, details={"source": "hazel_identity_log"})
        return recovered

    def revalidate(
        self,
        *,
        run_id: str,
        expected_ocs: str,
        trigger: IdentityRecheckTrigger,
        host: str | None = None,
    ) -> IdentityRevalidationResult:
        binding = self._bindings.get(run_id)
        if binding is None:
            return IdentityRevalidationResult(False, "identity_binding_required", None)
        try:
            self._validate_profile_binding(binding)
        except ValueError as exc:
            held = self._hold(run_id, str(exc))
            return IdentityRevalidationResult(False, str(exc), held)
        if binding.status is not IdentityBindingStatus.VALID:
            return IdentityRevalidationResult(False, binding.hold_reason or "identity_hold", binding)
        if expected_ocs != binding.ocs_id:
            held = self._hold(run_id, "active_ocs_identity_mismatch")
            return IdentityRevalidationResult(False, "active_ocs_identity_mismatch", held)
        if host is not None and host != binding.host:
            held = self._hold(run_id, "host_identity_context_mismatch")
            return IdentityRevalidationResult(False, "host_identity_context_mismatch", held)
        self._audit_log.append(
            "IDENTITY_REVALIDATION",
            binding,
            details={"trigger": trigger.value, "result": "valid"},
        )
        return IdentityRevalidationResult(True, "identity_valid", binding)

    def require_valid(
        self,
        *,
        run_id: str,
        expected_ocs: str,
        trigger: IdentityRecheckTrigger,
        host: str | None = None,
    ) -> ActiveIdentityBinding:
        result = self.revalidate(
            run_id=run_id,
            expected_ocs=expected_ocs,
            trigger=trigger,
            host=host,
        )
        if not result.valid or result.binding is None:
            raise ValueError(result.reason)
        return result.binding

    def rebind(
        self,
        *,
        run_id: str,
        ocs_id: str,
        host: str,
        session_context: str,
        reason: str,
    ) -> ActiveIdentityBinding:
        previous = self._bindings.get(run_id)
        binding = self.bind_active_identity(
            run_id=run_id,
            ocs_id=ocs_id,
            host=host,
            session_context=session_context,
        )
        self._audit_log.append(
            "IDENTITY_REBIND",
            binding,
            details={
                "reason": reason,
                "previous_ocs": None if previous is None else previous.ocs_id,
            },
        )
        return binding

    def hold(self, run_id: str, reason: str) -> ActiveIdentityBinding:
        return self._hold(run_id, reason)

    def _hold(self, run_id: str, reason: str) -> ActiveIdentityBinding:
        binding = self._bindings.get(run_id)
        if binding is None:
            raise ValueError("identity_binding_required")
        held = replace(binding, status=IdentityBindingStatus.HOLD, hold_reason=reason)
        self._bindings[run_id] = held
        self._audit_log.append("IDENTITY_HOLD", held, details={"reason": reason})
        return held

    def _validate_profile_binding(self, binding: ActiveIdentityBinding) -> None:
        profile = self._profiles.get(binding.ocs_id)
        if profile is None:
            raise ValueError("unknown_ocs_identity")
        if binding.institution != INSTITUTION:
            raise ValueError("institution_identity_mismatch")
        if binding.identity_ref != profile.identity:
            raise ValueError("identity_profile_mismatch")
        if binding.lineage_ref != profile.ancestry:
            raise ValueError("identity_lineage_mismatch")
        if binding.constitution_ref != profile.constitution_ref:
            raise ValueError("identity_constitution_mismatch")
        if binding.csp_ref != profile.csp_ref:
            raise ValueError("identity_csp_mismatch")
        if binding.state_namespace != profile.state_namespace:
            raise ValueError("identity_state_namespace_mismatch")
        if binding.memory_namespace != profile.memory_namespace:
            raise ValueError("identity_memory_namespace_mismatch")
        if binding.profile_version != profile.version:
            raise ValueError("identity_profile_version_mismatch")
