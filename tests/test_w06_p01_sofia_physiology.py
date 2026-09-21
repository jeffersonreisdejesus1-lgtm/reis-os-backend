from __future__ import annotations

import pytest

from app.cognitive_physiology.sofia_p01 import (
    SofiaBindingError,
    SofiaExecutionState,
    SofiaMissionRequest,
    SofiaP01Executor,
)

CAPABILITY = "software_implementation_code_incremental_integration"
AUTHORITY = "authority://sofia/current"


def request(**changes: object) -> SofiaMissionRequest:
    return SofiaMissionRequest(
        mission_id=str(changes.get("mission_id", "mission:p01")),
        operation_id=str(changes.get("operation_id", "operation:p01:001")),
        capability=str(changes.get("capability", CAPABILITY)),
        authority_ref=changes.get("authority_ref", AUTHORITY),  # type: ignore[arg-type]
        handoff_id=changes.get("handoff_id", "handoff:p01"),  # type: ignore[arg-type]
        payload=changes.get("payload", {"bounded_task": "implementation"}),  # type: ignore[arg-type]
    )


def test_p01_s01_identity_is_sofia() -> None:
    result = SofiaP01Executor().execute(request())
    assert result.ocs_id == "SOFIA"
    assert result.identity_ref == "identity://sofia"


def test_p01_s02_namespaces_are_distinct_and_owned() -> None:
    result = SofiaP01Executor().execute(request())
    assert result.state_namespace == "state://sofia/r2-v0.1.0"
    assert result.memory_namespace == "memory://sofia/r2-v0.1.0"
    assert result.state_namespace != result.memory_namespace


def test_p01_s03_capability_matches_specialty() -> None:
    result = SofiaP01Executor().execute(request())
    assert result.capability == CAPABILITY
    assert result.specialty == CAPABILITY


def test_p01_s04_missing_authority_fails_closed() -> None:
    with pytest.raises(SofiaBindingError, match="authority_reference_required"):
        SofiaP01Executor().execute(request(authority_ref=None))


def test_p01_s05_incompatible_capability_is_rejected() -> None:
    with pytest.raises(SofiaBindingError, match="capability_incompatible"):
        SofiaP01Executor().execute(request(capability="assurance"))


def test_p01_s06_handoff_does_not_transfer_authority() -> None:
    with pytest.raises(SofiaBindingError, match="authority_reference"):
        SofiaP01Executor().execute(request(authority_ref="handoff:p01"))


def test_p01_s07_receipt_is_causal_and_verifiable() -> None:
    result = SofiaP01Executor().execute(request())
    receipt = result.receipt
    assert receipt.mission_id == result.mission_id
    assert receipt.operation_id == result.operation_id
    assert receipt.authority_ref == AUTHORITY
    assert receipt.receipt_id
    assert receipt.canonical_payload()["ocs_id"] == "SOFIA"


def test_p01_s08_recovery_readback_does_not_execute_again() -> None:
    executor = SofiaP01Executor()
    first = executor.execute(request())
    recovered = SofiaP01Executor()
    recovered._readback[first.operation_id] = first
    replay = recovered.execute(request())
    assert replay.receipt.state is SofiaExecutionState.REPLAYED
    assert replay.receipt.receipt_id == first.receipt.receipt_id
    assert recovered.execution_count == 0
    assert recovered.readback(first.operation_id) == first
