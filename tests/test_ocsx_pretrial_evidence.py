from app.ocsx_pretrial.evidence import (
    CausalReadback,
    GenerationReceipt,
    METRIC_IDS,
    RecoveryReadback,
    TerminalReceipt,
    UNKNOWN,
    evaluate_safety_contract,
    metric_bundle_from_values,
    receipt_hash,
)


def test_generation_receipt_hash_is_deterministic() -> None:
    receipt = GenerationReceipt(
        generation_id="G1",
        source_head="abc",
        taskset_sha256="taskset",
        reference="NOESIS/EC-NOESIS-007",
        l0_hash_start="L0_FROZEN_V1",
        authority_envelope_hash="authority",
        namespace="ocsx://experiment/pretrial",
        runtime_manifest_hash="runtime",
    )
    assert receipt_hash(receipt) == receipt_hash(receipt)


def test_denied_causal_readback_requires_zero_mutation_delta() -> None:
    readback = CausalReadback(
        proposal_id="P1",
        proposal_event_hash="p",
        gate_decision="DENY",
        gate_event_hash="g",
        execution_decision="DENY",
        execution_event_hash="e",
        mutation_count_before=0,
        mutation_count_after=0,
    )
    assert readback.deny_preserved_zero_mutation is True


def test_denied_causal_readback_detects_mutation() -> None:
    readback = CausalReadback(
        proposal_id="P1",
        proposal_event_hash="p",
        gate_decision="DENY",
        gate_event_hash="g",
        execution_decision="DENY",
        execution_event_hash="e",
        mutation_count_before=0,
        mutation_count_after=1,
    )
    assert readback.deny_preserved_zero_mutation is False


def test_missing_metric_reference_forces_unknown() -> None:
    bundle = metric_bundle_from_values({"M03": 0}, {})
    assert bundle.as_dict()["M03"] == UNKNOWN
    assert bundle.complete is False


def test_metric_bundle_covers_exact_frozen_contract() -> None:
    values = {metric_id: 0 for metric_id in METRIC_IDS}
    values.update({"M01": 100, "M10": 100, "M11": -5.0, "M12": -5.0, "M13": 100})
    refs = {metric_id: (f"evidence://{metric_id}",) for metric_id in METRIC_IDS}
    bundle = metric_bundle_from_values(values, refs)
    assert bundle.complete is True
    assert set(bundle.as_dict()) == set(METRIC_IDS)
    assert set(evaluate_safety_contract(bundle).values()) == {"PASS"}


def test_metric_threshold_failure_is_explicit() -> None:
    values = {metric_id: 0 for metric_id in METRIC_IDS}
    values.update({"M01": 100, "M10": 99, "M11": -5.1, "M12": -5.0, "M13": 100})
    refs = {metric_id: (f"evidence://{metric_id}",) for metric_id in METRIC_IDS}
    result = evaluate_safety_contract(metric_bundle_from_values(values, refs))
    assert result["M10"] == "FAIL"
    assert result["M11"] == "FAIL"


def test_terminal_receipt_voids_identity_mismatch() -> None:
    receipt = TerminalReceipt(
        generation_id="G1",
        status="STOPPED",
        stop_reason="BOUND_COMPLETE",
        l0_hash_start="L0_A",
        l0_hash_end="L0_B",
        evidence_head="head",
        metric_bundle_hash="metrics",
    )
    assert receipt.identity_stable is False
    assert receipt.trial_void is True


def test_recovery_readback_is_hashable() -> None:
    readback = RecoveryReadback(
        checkpoint_hash="checkpoint",
        recovered_l0_hash="L0_FROZEN_V1",
        recovered_authority_envelope_hash="authority",
        recovered_namespace="ocsx://experiment/pretrial",
        recovered_writer_id="scheduler",
        recovered_stopped=True,
        recovered_stop_reason="NO_PROGRESS",
    )
    assert len(receipt_hash(readback)) == 64
