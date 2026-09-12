from __future__ import annotations

from app.cognitive_validation import phase_d2_adversarial_semantic as d2


def test_phase_d2_semantic_adversarial_closure(tmp_path, monkeypatch):
    monkeypatch.setenv("COI15_QUALIFICATION_SECRET", "phase-d2-test-secret")
    monkeypatch.setattr(d2, "ARTIFACT_DIR", tmp_path)
    monkeypatch.setattr(d2, "EVIDENCE_PATH", tmp_path / "phase_d2_evidence.json")

    evidence = d2.run_phase_d2_semantic_qualification()

    assert evidence["event"] == "PHASE_D2_ADVERSARIAL_SEMANTIC_COMPLETE"
    assert evidence["scenario_count"] == 3
    assert evidence["all_semantic_scenarios_verified"] is True
    by_class = {item["attack_class"]: item for item in evidence["scenarios"]}

    revoked = by_class["REVOKED_AUTHORITY"]
    assert revoked["scenario_verified"] is True
    assert revoked["effect_delta"] == 0
    assert revoked["observations"]["pre_revoke_authority_valid"] is True
    assert revoked["observations"]["post_revoke_prior_receipt_valid"] is False
    assert revoked["observations"]["post_revoke_discovery_error"].endswith(":authority_revoked")

    concurrent = by_class["CONCURRENT_RECEIPT_CONFLICT"]
    assert concurrent["scenario_verified"] is True
    assert concurrent["effect_delta"] == 1
    assert concurrent["observations"]["participant_count"] == 2
    assert concurrent["observations"]["executed_count"] == 1
    assert concurrent["observations"]["denied_count"] == 1

    timeout = by_class["TIMEOUT_DOUBLE_EXECUTION"]
    assert timeout["scenario_verified"] is True
    assert timeout["effect_delta"] == 1
    assert timeout["observations"]["first_effect_observed_before_timeout"] is True
    assert timeout["observations"]["caller_state_after_timeout"] == "EXECUTION_UNKNOWN"
    assert timeout["observations"]["blind_retry_attempted"] is True
    assert timeout["observations"]["retry_effect_delta"] == 0
    assert timeout["observations"]["reconciliation_required"] is True

    readback = d2.read_phase_d2_evidence()
    assert readback["qualification_receipt"] == evidence["qualification_receipt"]
