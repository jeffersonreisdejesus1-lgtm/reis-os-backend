from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from uuid import uuid4

from .core import (
    ArtifactRegistry,
    Environment,
    EnvironmentManager,
    IncidentManager,
    Observability,
    ReleaseManager,
    SecurityPipeline,
)
from .operations import (
    ConfigManager,
    FeatureFlagManager,
    MigrationGate,
    MigrationPlan,
    PerformanceGate,
    SLOPolicy,
)


@dataclass(frozen=True)
class BuildCandidate:
    software_id: str
    version: str
    source_sha: str
    files: dict[str, str]
    tests_total: int
    tests_failed: int
    changelog: tuple[str, ...] = ()
    rollback_ref: str = "main"
    performance_p95_ms: float = 0.0
    error_rate_pct: float = 0.0
    migration: MigrationPlan | None = None
    config: tuple[tuple[str, str], ...] = ()
    feature_flags: tuple[tuple[str, bool], ...] = ()


@dataclass(frozen=True)
class FounderGateBundle:
    bundle_id: str
    software_id: str
    version: str
    source_sha: str
    release_id: str | None
    release_manifest_hash: str | None
    security_passed: bool
    tests_passed: bool
    migration_passed: bool
    performance_passed: bool
    staging_qualified: bool
    ready_for_founder_gate: bool
    gate_status: str
    slo_policy: dict[str, float]
    reservations: tuple[str, ...]


class SoftwareFactory:
    """Autonomous V1 pipeline that stops at the final Founder gate."""

    def __init__(self) -> None:
        self.artifacts = ArtifactRegistry()
        self.security = SecurityPipeline()
        self.environments = EnvironmentManager()
        self.releases = ReleaseManager()
        self.observability = Observability()
        self.incidents = IncidentManager()
        self.config = ConfigManager()
        self.flags = FeatureFlagManager()
        self.migrations = MigrationGate()
        self.performance = PerformanceGate()
        self.slo = SLOPolicy()

    def qualify(self, candidate: BuildCandidate) -> FounderGateBundle:
        self.observability.emit("MISSION_ACCEPTED", candidate.software_id, asdict(candidate))
        self.environments.promote(candidate.software_id, candidate.version, Environment.DEV)

        for key, value in candidate.config:
            try:
                self.config.set(key, value)
            except ValueError:
                return self._hold(candidate, "CONFIG_SECRET_POLICY_FAILED")
        for name, enabled in candidate.feature_flags:
            self.flags.set(name, enabled)

        tests_passed = candidate.tests_total > 0 and candidate.tests_failed == 0
        if not tests_passed:
            self.incidents.open(candidate.software_id, "HIGH", "qualification tests failed", candidate.rollback_ref)
            self.observability.emit("QA_FAILED", candidate.software_id, {"failed": candidate.tests_failed})
            return self._bundle(candidate, False, False, True, True, False, ("QA_FAILED",))

        migration_passed, migration_reason = self.migrations.validate(candidate.migration)
        if not migration_passed:
            self.incidents.open(candidate.software_id, "HIGH", migration_reason or "migration failed", candidate.rollback_ref)
            return self._bundle(candidate, True, False, False, True, False, (migration_reason or "MIGRATION_FAILED",))

        performance_passed, perf_reasons = self.performance.validate(
            candidate.performance_p95_ms,
            candidate.error_rate_pct,
        )
        if not performance_passed:
            self.incidents.open(candidate.software_id, "HIGH", ",".join(perf_reasons), candidate.rollback_ref)
            return self._bundle(candidate, True, False, True, False, False, perf_reasons)

        security_report = self.security.scan(candidate.files)
        if not security_report.passed:
            self.incidents.open(candidate.software_id, "CRITICAL", "security gate failed", candidate.rollback_ref)
            self.observability.emit(
                "SECURITY_FAILED",
                candidate.software_id,
                [asdict(f) for f in security_report.findings],
            )
            return self._bundle(candidate, True, False, True, True, False, ("SECURITY_FAILED",))

        records = [
            self.artifacts.register(candidate.software_id, candidate.version, path, content.encode())
            for path, content in sorted(candidate.files.items())
        ]
        release = self.releases.create(
            candidate.software_id,
            candidate.version,
            candidate.source_sha,
            records,
            list(candidate.changelog),
            candidate.rollback_ref,
        )
        self.environments.promote(candidate.software_id, candidate.version, Environment.STAGING)
        self.observability.emit(
            "STAGING_QUALIFIED",
            candidate.software_id,
            {
                "release_id": release.release_id,
                "manifest_hash": release.manifest_hash,
                "artifact_count": len(records),
                "sbom_count": len(security_report.sbom),
                "slo": self.slo.as_dict(),
            },
        )
        return FounderGateBundle(
            bundle_id=str(uuid4()),
            software_id=candidate.software_id,
            version=candidate.version,
            source_sha=candidate.source_sha,
            release_id=release.release_id,
            release_manifest_hash=release.manifest_hash,
            security_passed=True,
            tests_passed=True,
            migration_passed=True,
            performance_passed=True,
            staging_qualified=True,
            ready_for_founder_gate=True,
            gate_status="FOUNDER_FINAL_GATE_REQUIRED",
            slo_policy=self.slo.as_dict(),
            reservations=(
                "PRODUCTION_PROMOTION_NOT_EXECUTED",
                "GITHUB_MERGE_NOT_EXECUTED",
                "NO_PAID_INFRA_AUTHORIZED",
            ),
        )

    def promote_after_founder(self, bundle: FounderGateBundle, *, founder_approved: bool) -> dict[str, object]:
        if not bundle.ready_for_founder_gate:
            raise ValueError("bundle is not promotable")
        state = self.environments.promote(
            bundle.software_id,
            bundle.version,
            Environment.PRODUCTION,
            founder_approved=founder_approved,
        )
        self.observability.emit("PRODUCTION_PROMOTED", bundle.software_id, asdict(state))
        return asdict(state)

    @staticmethod
    def source_fingerprint(files: dict[str, str]) -> str:
        material = "\n".join(
            f"{path}:{sha256(content.encode()).hexdigest()}"
            for path, content in sorted(files.items())
        )
        return sha256(material.encode()).hexdigest()

    def _hold(self, candidate: BuildCandidate, reason: str) -> FounderGateBundle:
        self.incidents.open(candidate.software_id, "HIGH", reason, candidate.rollback_ref)
        return self._bundle(candidate, False, False, False, False, False, (reason,))

    def _bundle(
        self,
        candidate: BuildCandidate,
        tests_passed: bool,
        security_passed: bool,
        migration_passed: bool,
        performance_passed: bool,
        staging_qualified: bool,
        reservations: tuple[str, ...],
    ) -> FounderGateBundle:
        return FounderGateBundle(
            bundle_id=str(uuid4()),
            software_id=candidate.software_id,
            version=candidate.version,
            source_sha=candidate.source_sha,
            release_id=None,
            release_manifest_hash=None,
            security_passed=security_passed,
            tests_passed=tests_passed,
            migration_passed=migration_passed,
            performance_passed=performance_passed,
            staging_qualified=staging_qualified,
            ready_for_founder_gate=False,
            gate_status="HOLD",
            slo_policy=self.slo.as_dict(),
            reservations=reservations,
        )
