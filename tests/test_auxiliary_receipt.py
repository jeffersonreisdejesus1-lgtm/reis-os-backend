from app.ocs_instances.receipt import (
    AuxiliaryEvidenceReference,
    AuxiliaryReceipt,
    AuxiliaryReceiptState,
    create_auxiliary_receipt,
)


def make_receipt(
    *,
    evidence_references: tuple[AuxiliaryEvidenceReference, ...] = (
        AuxiliaryEvidenceReference("evidence:1", "runtime", "local"),
    ),
    execution_state: AuxiliaryReceiptState = AuxiliaryReceiptState.OBSERVED,
    result_reference: str | None = "result:1",
) -> AuxiliaryReceipt:
    return create_auxiliary_receipt(
        operation_id="operation:1",
        mission_id="mission:1",
        parent_mission_id="mission:parent",
        instance_id="instance:1",
        authority_reference="authority:1",
        executor_id="executor:1",
        capability="bounded-capability",
        payload_fingerprint="payload:hash",
        execution_state=execution_state,
        result_reference=result_reference,
        evidence_references=evidence_references,
        observed_at="2026-09-20T00:00:00Z",
    )


def test_receipt_is_deterministic_and_bound_to_operation() -> None:
    first = make_receipt()
    second = make_receipt()
    assert first.receipt_id == second.receipt_id
    assert first.operation_id == "operation:1"
    assert first.schema_version


def test_missing_evidence_is_representable() -> None:
    receipt = make_receipt(evidence_references=())
    assert receipt.evidence_references == ()
    assert receipt.execution_state is AuxiliaryReceiptState.OBSERVED


def test_unknown_state_serializes_without_claiming_success() -> None:
    receipt = make_receipt(
        execution_state=AuxiliaryReceiptState.UNKNOWN,
        result_reference=None,
    )
    encoded = receipt.to_dict()
    assert encoded["execution_state"] == "unknown"
    assert encoded["result_reference"] is None


def test_receipt_does_not_create_authority_or_effect() -> None:
    receipt = make_receipt()
    assert not hasattr(receipt, "authority_granted")
    assert not hasattr(receipt, "dispatch")
