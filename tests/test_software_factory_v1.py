from app.software_factory.core import (
    ArtifactRegistry,
    Environment,
    EnvironmentManager,
    IncidentManager,
    IncidentStatus,
    Observability,
    ReleaseManager,
    SecurityPipeline,
)
from app.software_factory.operations import (
    ConfigManager,
    FeatureFlagManager,
    MigrationPlan,
    MigrationGate,
    PerformanceGate,
)
from app.software_factory.orchestrator import BuildCandidate, SoftwareFactory


def candidate(**overrides: object) -> BuildCandidate:
    data = {
        "software_id": "demo-software",
        "version": "1.0.0",
        "source_sha": "abcdef1234567890",
        "files": {"app.py": "print('ok')\n", "README.md": "demo\n"},
        "tests_total": 12,
        "tests_failed": 0,
        "changelog": ("initial release",),
        "rollback_ref": "main@previous",
        "performance_p95_ms": 120.0,
        "error_rate_pct": 0.1,
        "migration": MigrationPlan("m1", "CREATE TABLE demo(id int);", "DROP TABLE demo;"),
        "config": (("LOG_LEVEL", "INFO"), ("API_TOKEN", "ref://render/API_TOKEN")),
        "feature_flags": (("new_ui", False),),
    }
    data.update(overrides)
    return BuildCandidate(**data)


def test_end_to_end_stops_at_founder_gate() -> None:
    factory = SoftwareFactory()
    bundle = factory.qualify(candidate())
    assert bundle.ready_for_founder_gate is True
    assert bundle.gate_status == "FOUNDER_FINAL_GATE_REQUIRED"
    assert bundle.security_passed is True
    assert bundle.tests_passed is True
    assert bundle.migration_passed is True
    assert bundle.performance_passed is True
    assert bundle.staging_qualified is True
    assert bundle.release_manifest_hash is not None
    assert factory.environments.current("demo-software").environment is Environment.STAGING


def test_production_is_forbidden_without_founder() -> None:
    factory = SoftwareFactory()
    bundle = factory.qualify(candidate())
    try:
        factory.promote_after_founder(bundle, founder_approved=False)
    except PermissionError:
        pass
    else:
        raise AssertionError("production promotion must require Founder approval")


def test_production_can_follow_explicit_founder_gate() -> None:
    factory = SoftwareFactory()
    bundle = factory.qualify(candidate())
    state = factory.promote_after_founder(bundle, founder_approved=True)
    assert state["environment"] is Environment.PRODUCTION


def test_security_secret_fails_closed() -> None:
    factory = SoftwareFactory()
    bundle = factory.qualify(candidate(files={"bad.py": "token='sk-ABCDEFGHIJKLMNOPQRSTUV'"}))
    assert bundle.ready_for_founder_gate is False
    assert "SECURITY_FAILED" in bundle.reservations
    assert factory.incidents.list()[0]["severity"] == "CRITICAL"


def test_failed_tests_hold_pipeline() -> None:
    factory = SoftwareFactory()
    bundle = factory.qualify(candidate(tests_failed=1))
    assert bundle.ready_for_founder_gate is False
    assert bundle.tests_passed is False
    assert "QA_FAILED" in bundle.reservations


def test_performance_breach_holds_pipeline() -> None:
    factory = SoftwareFactory()
    bundle = factory.qualify(candidate(performance_p95_ms=1000.0))
    assert bundle.ready_for_founder_gate is False
    assert bundle.performance_passed is False
    assert "P95_LATENCY_BREACH" in bundle.reservations


def test_destructive_migration_requires_explicit_acknowledgement() -> None:
    gate = MigrationGate()
    passed, reason = gate.validate(MigrationPlan("m2", "DROP TABLE users;", "CREATE TABLE users(id int);"))
    assert passed is False
    assert reason == "DESTRUCTIVE_MIGRATION_UNACKNOWLEDGED"


def test_config_rejects_embedded_secret_and_accepts_reference() -> None:
    config = ConfigManager()
    try:
        config.set("API_TOKEN", "actual-secret-value")
    except ValueError:
        pass
    else:
        raise AssertionError("embedded secrets must be rejected")
    config.set("API_TOKEN", "ref://render/API_TOKEN")
    assert config.snapshot()["API_TOKEN"].startswith("ref://")


def test_feature_flag_defaults_off() -> None:
    flags = FeatureFlagManager()
    assert flags.enabled("unknown") is False
    flags.set("new_ui", True)
    assert flags.enabled("new_ui") is True


def test_performance_gate_accepts_bounded_metrics() -> None:
    passed, reasons = PerformanceGate().validate(200.0, 0.2)
    assert passed is True
    assert reasons == ()


def test_artifact_registry_is_immutable() -> None:
    registry = ArtifactRegistry()
    first = registry.register("x", "1", "a.txt", b"one")
    second = registry.register("x", "1", "a.txt", b"one")
    assert first.artifact_id == second.artifact_id
    try:
        registry.register("x", "1", "a.txt", b"two")
    except ValueError:
        pass
    else:
        raise AssertionError("artifact overwrite must fail")


def test_security_pipeline_emits_sbom_hashes() -> None:
    report = SecurityPipeline().scan({"a.py": "print(1)", "b.txt": "hello"})
    assert report.passed is True
    assert len(report.sbom) == 2
    assert all(len(item["sha256"]) == 64 for item in report.sbom)


def test_environment_requires_dev_before_staging() -> None:
    manager = EnvironmentManager()
    try:
        manager.promote("x", "1", Environment.STAGING)
    except ValueError:
        pass
    else:
        raise AssertionError("staging must require DEV")


def test_release_manifest_is_deterministic_for_same_inputs() -> None:
    registry = ArtifactRegistry()
    record = registry.register("x", "1", "a.txt", b"one")
    manager = ReleaseManager()
    first = manager.create("x", "1", "abc1234", [record], ["change"], "old")
    second = manager.create("x", "1", "abc1234", [record], ["change"], "old")
    assert first.manifest_hash == second.manifest_hash


def test_incident_lifecycle_and_observability() -> None:
    incidents = IncidentManager()
    incident = incidents.open("x", "HIGH", "failure", "rollback")
    contained = incidents.transition(incident.incident_id, IncidentStatus.CONTAINED)
    assert contained.status is IncidentStatus.CONTAINED
    resolved = incidents.transition(incident.incident_id, IncidentStatus.RESOLVED)
    assert resolved.status is IncidentStatus.RESOLVED

    obs = Observability()
    obs.emit("BUILD_PASS", "x", {"ok": True})
    snap = obs.snapshot()
    assert snap["counters"]["BUILD_PASS"] == 1
