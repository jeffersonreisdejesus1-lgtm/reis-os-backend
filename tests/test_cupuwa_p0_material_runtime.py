from app.cupuwa_multi_ocs.p0_material_runtime import P0MaterialOrchestrator


def test_p0_material_runtime_produces_bounded_artifact() -> None:
    artifact = P0MaterialOrchestrator().execute()

    assert artifact.mission_id == "CUPUWA-P0-CORE-FINANCE-MATERIAL-001"
    assert artifact.artifact_type == "CUPUWA_P0_GOVERNED_CANDIDATE"
    assert artifact.selected_ocs
    assert artifact.artifact_digest
    assert all(receipt.status == "OBSERVED" for receipt in artifact.worker_receipts)
    assert all(not receipt.authority_granted for receipt in artifact.worker_receipts)
    assert all(
        not receipt.material_effect_claim for receipt in artifact.worker_receipts
    )


def test_p0_material_runtime_is_deterministic() -> None:
    first = P0MaterialOrchestrator().execute()
    second = P0MaterialOrchestrator().execute()

    assert first == second
