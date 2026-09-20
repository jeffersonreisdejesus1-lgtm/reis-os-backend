from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.ocs_instances.concurrency import (
    AuxiliaryConcurrencyError,
    AuxiliaryOperationCoordinator,
    CanonicalOperation,
)


def claim(path: Path, owner: str) -> CanonicalOperation:
    return AuxiliaryOperationCoordinator(path).claim(
        operation_id="operation:1",
        payload_fingerprint="payload:1",
        mission_id="mission:1",
        authority_reference="authority:1",
        capability="bounded-capability",
        owner_id=owner,
    )


def test_concurrent_same_operation_has_one_canonical_claim(tmp_path: Path) -> None:
    path = tmp_path / "coordination.sqlite3"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda owner: claim(path, owner), ("owner:1", "owner:2"))
        )
    assert len({result.owner_id for result in results}) == 1
    assert AuxiliaryOperationCoordinator(path).read("operation:1").state == "EXECUTING"


def test_replay_after_completion_returns_one_result_and_receipt(tmp_path: Path) -> None:
    path = tmp_path / "coordination.sqlite3"
    store = AuxiliaryOperationCoordinator(path)
    first = store.claim(
        operation_id="operation:1",
        payload_fingerprint="payload:1",
        mission_id="mission:1",
        authority_reference="authority:1",
        capability="capability:1",
        owner_id="owner:1",
    )
    completed = store.complete(
        operation_id="operation:1",
        owner_id=str(first.owner_id),
        receipt_id="receipt:1",
        result_reference="result:1",
    )
    replay = store.claim(
        operation_id="operation:1",
        payload_fingerprint="payload:1",
        mission_id="mission:1",
        authority_reference="authority:1",
        capability="capability:1",
        owner_id="owner:2",
    )
    assert replay == completed
    assert replay.receipt_id == "receipt:1"


def test_concurrent_completion_is_idempotent_and_keeps_one_receipt(
    tmp_path: Path,
) -> None:
    path = tmp_path / "coordination.sqlite3"
    store = AuxiliaryOperationCoordinator(path)
    store.claim(
        operation_id="operation:1",
        payload_fingerprint="payload:1",
        mission_id="mission:1",
        authority_reference="authority:1",
        capability="capability:1",
        owner_id="owner:1",
    )

    def finish() -> CanonicalOperation:
        return AuxiliaryOperationCoordinator(path).complete(
            operation_id="operation:1",
            owner_id="owner:1",
            receipt_id="receipt:1",
            result_reference="result:1",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: finish(), (1, 2)))
    assert all(result.receipt_id == "receipt:1" for result in results)
    assert AuxiliaryOperationCoordinator(path).read("operation:1").state == "SUCCEEDED"


def test_conflicting_payload_is_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "coordination.sqlite3"
    claim(path, "owner:1")
    with pytest.raises(AuxiliaryConcurrencyError, match="payload_conflict"):
        AuxiliaryOperationCoordinator(path).claim(
            operation_id="operation:1",
            payload_fingerprint="payload:2",
            mission_id="mission:1",
            authority_reference="authority:1",
            capability="bounded-capability",
            owner_id="owner:2",
        )


def test_stale_owner_cannot_complete(tmp_path: Path) -> None:
    path = tmp_path / "coordination.sqlite3"
    claim(path, "owner:1")
    with pytest.raises(AuxiliaryConcurrencyError, match="stale_owner"):
        AuxiliaryOperationCoordinator(path).complete(
            operation_id="operation:1",
            owner_id="owner:2",
            receipt_id="receipt:1",
            result_reference="result:1",
        )


def test_restart_readback_preserves_causal_binding(tmp_path: Path) -> None:
    path = tmp_path / "coordination.sqlite3"
    first = AuxiliaryOperationCoordinator(path)
    claimed = first.claim(
        operation_id="operation:1",
        payload_fingerprint="payload:1",
        mission_id="mission:1",
        authority_reference="authority:1",
        capability="capability:1",
        owner_id="owner:1",
    )
    restarted = AuxiliaryOperationCoordinator(path).read("operation:1")
    assert restarted == claimed
    assert restarted.mission_id == "mission:1"
    assert restarted.authority_reference == "authority:1"
    assert restarted.capability == "capability:1"


def test_authority_and_capability_are_bound_to_canonical_operation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "coordination.sqlite3"
    claim(path, "owner:1")
    with pytest.raises(AuxiliaryConcurrencyError, match="scope_conflict"):
        AuxiliaryOperationCoordinator(path).claim(
            operation_id="operation:1",
            payload_fingerprint="payload:1",
            mission_id="mission:1",
            authority_reference="authority:other",
            capability="bounded-capability",
            owner_id="owner:2",
        )

