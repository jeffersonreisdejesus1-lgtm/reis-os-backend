from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
import re
from threading import Lock
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(value: object) -> str:
    data = json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    return sha256(data).hexdigest()


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    software_id: str
    version: str
    path: str
    sha256: str
    size_bytes: int
    created_at: str


class ArtifactRegistry:
    def __init__(self) -> None:
        self._records: dict[str, ArtifactRecord] = {}
        self._lock = Lock()

    def register(self, software_id: str, version: str, path: str, content: bytes) -> ArtifactRecord:
        digest = sha256(content).hexdigest()
        key = f"{software_id}:{version}:{path}"
        record = ArtifactRecord(str(uuid4()), software_id, version, path, digest, len(content), _now())
        with self._lock:
            existing = self._records.get(key)
            if existing is not None:
                if existing.sha256 != digest:
                    raise ValueError("immutable artifact conflict")
                return existing
            self._records[key] = record
        return record

    def records(self) -> list[dict[str, object]]:
        with self._lock:
            return [asdict(r) for r in self._records.values()]


@dataclass(frozen=True)
class SecurityFinding:
    finding_id: str
    severity: str
    path: str
    rule: str


@dataclass(frozen=True)
class SecurityReport:
    passed: bool
    findings: tuple[SecurityFinding, ...]
    sbom: tuple[dict[str, object], ...]


class SecurityPipeline:
    _patterns = (
        ("CRITICAL", "OPENAI_STYLE_SECRET", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}")),
        ("CRITICAL", "PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
        ("HIGH", "PASSWORD_ASSIGNMENT", re.compile(r"(?i)\bpassword\s*=\s*['\"][^'\"]{4,}['\"]")),
        ("HIGH", "TOKEN_ASSIGNMENT", re.compile(r"(?i)\b(?:api_?key|secret|token)\s*=\s*['\"][^'\"]{8,}['\"]")),
    )

    def scan(self, files: dict[str, str]) -> SecurityReport:
        findings: list[SecurityFinding] = []
        sbom: list[dict[str, object]] = []
        for path, content in sorted(files.items()):
            encoded = content.encode()
            sbom.append({"path": path, "sha256": sha256(encoded).hexdigest(), "size_bytes": len(encoded)})
            for severity, rule, pattern in self._patterns:
                if pattern.search(content):
                    findings.append(SecurityFinding(str(uuid4()), severity, path, rule))
        passed = not any(f.severity in {"CRITICAL", "HIGH"} for f in findings)
        return SecurityReport(passed, tuple(findings), tuple(sbom))


class Environment(str, Enum):
    DEV = "DEV"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"


@dataclass(frozen=True)
class EnvironmentState:
    software_id: str
    version: str
    environment: Environment
    predecessor: Environment | None
    promoted_at: str


class EnvironmentManager:
    def __init__(self) -> None:
        self._state: dict[str, EnvironmentState] = {}
        self._history: list[EnvironmentState] = []
        self._lock = Lock()

    def promote(self, software_id: str, version: str, target: Environment, *, founder_approved: bool = False) -> EnvironmentState:
        with self._lock:
            current = self._state.get(software_id)
            predecessor = current.environment if current else None
            if target is Environment.STAGING and predecessor not in {Environment.DEV, Environment.STAGING}:
                raise ValueError("staging requires dev predecessor")
            if target is Environment.PRODUCTION:
                if predecessor is not Environment.STAGING:
                    raise ValueError("production requires staging predecessor")
                if not founder_approved:
                    raise PermissionError("founder approval required")
            if target is Environment.DEV and predecessor is Environment.PRODUCTION:
                raise ValueError("cannot demote production directly to dev")
            state = EnvironmentState(software_id, version, target, predecessor, _now())
            self._state[software_id] = state
            self._history.append(state)
            return state

    def current(self, software_id: str) -> EnvironmentState | None:
        with self._lock:
            return self._state.get(software_id)

    def rollback(self, software_id: str, version: str, target: Environment) -> EnvironmentState:
        if target is Environment.PRODUCTION:
            raise ValueError("rollback target cannot self-promote to production")
        return self.promote(software_id, version, target)


@dataclass(frozen=True)
class ReleaseManifest:
    release_id: str
    software_id: str
    version: str
    source_sha: str
    artifact_hashes: tuple[str, ...]
    changelog: tuple[str, ...]
    rollback_ref: str
    manifest_hash: str
    created_at: str


class ReleaseManager:
    def create(
        self,
        software_id: str,
        version: str,
        source_sha: str,
        artifacts: list[ArtifactRecord],
        changelog: list[str],
        rollback_ref: str,
    ) -> ReleaseManifest:
        payload = {
            "software_id": software_id,
            "version": version,
            "source_sha": source_sha,
            "artifact_hashes": sorted(a.sha256 for a in artifacts),
            "changelog": changelog,
            "rollback_ref": rollback_ref,
        }
        return ReleaseManifest(
            release_id=str(uuid4()),
            software_id=software_id,
            version=version,
            source_sha=source_sha,
            artifact_hashes=tuple(payload["artifact_hashes"]),
            changelog=tuple(changelog),
            rollback_ref=rollback_ref,
            manifest_hash=_digest(payload),
            created_at=_now(),
        )


@dataclass(frozen=True)
class Observation:
    event_id: str
    event_type: str
    software_id: str
    payload_hash: str
    created_at: str


class Observability:
    def __init__(self) -> None:
        self._events: list[Observation] = []
        self._counters: dict[str, int] = {}
        self._lock = Lock()

    def emit(self, event_type: str, software_id: str, payload: object) -> Observation:
        event = Observation(str(uuid4()), event_type, software_id, _digest(payload), _now())
        with self._lock:
            self._events.append(event)
            self._counters[event_type] = self._counters.get(event_type, 0) + 1
        return event

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "events": [asdict(e) for e in self._events],
            }


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    CONTAINED = "CONTAINED"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True)
class Incident:
    incident_id: str
    software_id: str
    severity: str
    reason: str
    rollback_ref: str | None
    status: IncidentStatus
    created_at: str


class IncidentManager:
    def __init__(self) -> None:
        self._incidents: dict[str, Incident] = {}
        self._lock = Lock()

    def open(self, software_id: str, severity: str, reason: str, rollback_ref: str | None = None) -> Incident:
        incident = Incident(str(uuid4()), software_id, severity, reason, rollback_ref, IncidentStatus.OPEN, _now())
        with self._lock:
            self._incidents[incident.incident_id] = incident
        return incident

    def transition(self, incident_id: str, status: IncidentStatus) -> Incident:
        with self._lock:
            current = self._incidents[incident_id]
            updated = Incident(
                current.incident_id,
                current.software_id,
                current.severity,
                current.reason,
                current.rollback_ref,
                status,
                current.created_at,
            )
            self._incidents[incident_id] = updated
            return updated

    def list(self) -> list[dict[str, object]]:
        with self._lock:
            return [asdict(i) for i in self._incidents.values()]
