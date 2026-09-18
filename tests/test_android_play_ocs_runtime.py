from datetime import datetime, timedelta, timezone

import pytest

from app.ocs.android_play import (
    CANONICAL_NAME,
    NAMESPACE,
    OCS_ID,
    AndroidPlayOCS,
    CognitiveMode,
    Disposition,
)


def make_ocs() -> AndroidPlayOCS:
    return AndroidPlayOCS("MISSION-ANDROID-PLAY-QUAL-001")


def test_canonical_identity_is_stable() -> None:
    ocs = make_ocs()
    assert ocs.ocs_id == OCS_ID == "REISOS::INST::ANDROID_PLAY::001"
    assert ocs.canonical_name == CANONICAL_NAME == "ANDROID PLAY STEWARDSHIP"
    assert ocs.namespace == NAMESPACE == "reisos/android-play"


def test_authority_is_fail_closed_for_reserved_actions() -> None:
    ocs = make_ocs()
    for action in [
        "PUBLISH_PRODUCTION",
        "CHANGE_PRICE",
        "SELF_PROMOTE",
        "EXPAND_AUTHORITY",
        "USE_PERMANENT_CREDENTIALS",
    ]:
        with pytest.raises(PermissionError):
            ocs.constitutional_precheck(action, authorized=True)
    with pytest.raises(PermissionError):
        ocs.constitutional_precheck("COGNITIVE_CYCLE", authorized=False)


def test_only_official_sources_enter_policy_ledger() -> None:
    ocs = make_ocs()
    with pytest.raises(PermissionError):
        ocs.register_evidence(
            evidence_id="E1",
            source_url="https://example.com/post",
            source_kind="THIRD_PARTY",
            claim="claim",
            raw_content="x",
        )


def test_policy_freshness_fails_closed_on_missing_or_stale_evidence() -> None:
    ocs = make_ocs()
    now = datetime.now(timezone.utc)
    with pytest.raises(RuntimeError):
        ocs.policy_freshness_gate(["PLAY-TARGET-API"], now=now)

    ocs.register_evidence(
        evidence_id="PLAY-TARGET-API",
        source_url="https://support.google.com/googleplay/android-developer/answer/11926878",
        source_kind="GOOGLE_PLAY_OFFICIAL",
        claim="target API policy",
        raw_content="api policy snapshot",
        expires_at=now - timedelta(seconds=1),
        retrieved_at=now - timedelta(days=1),
    )
    with pytest.raises(RuntimeError):
        ocs.policy_freshness_gate(["PLAY-TARGET-API"], now=now)


def test_policy_freshness_passes_for_fresh_official_evidence() -> None:
    ocs = make_ocs()
    now = datetime.now(timezone.utc)
    ocs.register_evidence(
        evidence_id="PLAY-TARGET-API",
        source_url="https://support.google.com/googleplay/android-developer/answer/11926878",
        source_kind="GOOGLE_PLAY_OFFICIAL",
        claim="target API policy",
        raw_content="api policy snapshot",
        expires_at=now + timedelta(days=7),
        retrieved_at=now,
    )
    ocs.policy_freshness_gate(["PLAY-TARGET-API"], now=now)


def test_recurrent_cycle_binds_r1_to_r7_and_emits_causal_telemetry() -> None:
    ocs = make_ocs()
    result = ocs.recurrent_cycle(
        sensory_input={
            "novelty": 0.7,
            "uncertainty": 0.6,
            "risk": 0.4,
            "cognitive_load": 0.3,
            "observed_state": {"release_ready": False},
        },
        prediction={"release_ready": True},
        candidates=[
            {
                "id": "publish",
                "goal_relevance": 1.0,
                "evidence_strength": 0.1,
                "salience": 0.2,
                "expected_value": 0.8,
                "risk": 1.0,
                "cost": 0.2,
            },
            {
                "id": "remediate",
                "goal_relevance": 0.9,
                "evidence_strength": 0.9,
                "salience": 0.7,
                "expected_value": 0.7,
                "risk": 0.1,
                "cost": 0.2,
            },
        ],
        authorized=True,
    )
    assert result["mode"] == CognitiveMode.DELIBERATIVE.value
    assert result["winner"]["id"] == "remediate"
    assert result["prediction_error"] == 1.0
    assert ocs.memory.working["workspace_winner"]["id"] == "remediate"
    assert ocs.memory.episodic
    event_types = [event.event_type for event in ocs.telemetry]
    for required in [
        "SENSE",
        "MODEL",
        "PREDICT",
        "MODULATE",
        "GATE",
        "COMPETE",
        "BROADCAST",
        "SPECIALIST_PROCESS",
        "COMPARE",
        "UPDATE",
        "LEARN_CANDIDATE",
        "HOMEOSTASIS",
    ]:
        assert required in event_types


def test_unknown_transition_is_rejected() -> None:
    ocs = make_ocs()
    with pytest.raises(ValueError):
        ocs.transition("MAGIC")


def test_scheduler_enters_recovery_under_excessive_load() -> None:
    ocs = make_ocs()
    ocs.state.cognitive_load = 0.95
    assert ocs.schedule_mode() == CognitiveMode.RECOVERY


def test_snapshot_restore_is_mission_scoped_and_fences_old_writers() -> None:
    ocs = make_ocs()
    snapshot = ocs.snapshot()
    previous_generation = ocs.state.generation
    ocs.restore(snapshot)
    assert ocs.state.generation == previous_generation + 1
    assert ocs.telemetry[-1].event_type == "RECOVER"

    other = AndroidPlayOCS("OTHER-MISSION")
    foreign_snapshot = other.snapshot()
    with pytest.raises(PermissionError):
        ocs.restore(foreign_snapshot)


def test_consolidation_promotes_only_zero_error_episodes() -> None:
    ocs = make_ocs()
    ocs.recurrent_cycle(
        sensory_input={"observed_state": {"ok": True}},
        prediction={"ok": True},
        candidates=[{"id": "safe", "goal_relevance": 1.0}],
        authorized=True,
    )
    assert ocs.consolidate() == 1
    assert ocs.memory.semantic


def test_readiness_disposition_requires_fresh_evidence_and_zero_findings() -> None:
    ocs = make_ocs()
    now = datetime.now(timezone.utc)
    assert (
        ocs.readiness_disposition(
            required_evidence_ids=["E"], unresolved_findings=[], now=now
        )
        == Disposition.HOLD
    )

    ocs.register_evidence(
        evidence_id="E",
        source_url="https://developer.android.com/topic/architecture",
        source_kind="ANDROID_OFFICIAL",
        claim="architecture guidance",
        raw_content="official snapshot",
        expires_at=now + timedelta(days=30),
        retrieved_at=now,
    )
    assert (
        ocs.readiness_disposition(
            required_evidence_ids=["E"], unresolved_findings=["missing AAB"], now=now
        )
        == Disposition.REMEDIATION_REQUIRED
    )
    assert (
        ocs.readiness_disposition(
            required_evidence_ids=["E"], unresolved_findings=[], now=now
        )
        == Disposition.PASS_CANDIDATE
    )
