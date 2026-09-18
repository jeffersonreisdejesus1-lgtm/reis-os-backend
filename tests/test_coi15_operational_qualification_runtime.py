from app.cognitive_validation import operational_qualification_runtime as runtime


def test_operational_qualification_emits_three_material_proofs(tmp_path, monkeypatch):
    monkeypatch.setenv("COI15_QUALIFICATION_SECRET", "qualification-test-secret")
    monkeypatch.setattr(runtime, "ARTIFACT_DIR", tmp_path)
    monkeypatch.setattr(runtime, "DB_PATH", tmp_path / "learning.sqlite3")
    monkeypatch.setattr(runtime, "EVIDENCE_PATH", tmp_path / "evidence.json")
    monkeypatch.setattr(runtime, "EFFECT_PATH", tmp_path / "material_effect.jsonl")

    evidence = runtime.run_qualification()

    assert evidence["mission_n"] != evidence["mission_n1"]
    assert evidence["route_n"] == "github"
    assert evidence["learned_route"] == "software_factory"
    assert evidence["cross_mission"]["ok"] is True
    assert evidence["cross_mission"]["plan"]["mission_id"] == evidence["mission_n1"]
    assert evidence["cross_mission"]["plan"]["selected_capability_id"] == "software_factory"
    assert evidence["cross_mission"]["pid"] != evidence["runtime_pid"]
    assert evidence["adversarial"]["attack_count"] == 19
    assert len(evidence["adversarial"]["events"]) == 19
    assert all(event["effect_after"] == event["effect_before"] for event in evidence["adversarial"]["events"])
    assert evidence["mission_receipt_id"].startswith("mcr:")
    assert evidence["action_receipt_id"].startswith("acr:")
    assert evidence["authority_receipt_id"].startswith("authr:")
    assert evidence["governed_execution_receipt"]
    assert evidence["evidence_receipt"]
    assert evidence["learning_receipt"]
    assert len(evidence["lineage_receipt"]) == 64
    assert runtime.EVIDENCE_PATH.exists()
    assert runtime.EFFECT_PATH.exists()
    assert evidence["assurance_disposition_changed"] is False
    assert evidence["founder_promotion_executed"] is False
