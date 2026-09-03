from __future__ import annotations

from pathlib import Path

import pytest

from app.universal_kernel.contracts import StateRecord
from app.universal_kernel.state_trace import (
    SQLiteStatePersistencePort,
    StateCore,
    state_record_hash,
)


def _record(
    state_id: str,
    *,
    version: int,
    predecessor: str | None,
    value: str,
) -> StateRecord:
    return StateRecord(
        state_id=state_id,
        ocs="SOFIA",
        version=version,
        predecessor=predecessor,
        payload={"value": value, "nested": {"count": version}},
        verified=True,
    )


def _write(core: StateCore, record: StateRecord) -> StateRecord:
    return core.write(
        record,
        lambda persisted: state_record_hash(persisted) == state_record_hash(record),
        actor_ocs_id="SOFIA",
        target_namespace="state://SOFIA/runtime",
        state_ref=record.state_id,
        authority_context="authority:g3-f01",
    )


def test_g3_f01_survives_statecore_destruction_and_fresh_reload(tmp_path: Path) -> None:
    db_path = tmp_path / "statecore.sqlite3"
    first_port = SQLiteStatePersistencePort(db_path)
    first_core = StateCore(first_port)
    genesis = _record("state:sofia:1", version=1, predecessor=None, value="alpha")
    persisted = _write(first_core, genesis)
    expected_hash = state_record_hash(persisted)

    del first_core
    del first_port

    second_port = SQLiteStatePersistencePort(db_path)
    second_core = StateCore(second_port)
    reloaded = second_core.current("SOFIA")

    assert reloaded is not None
    assert reloaded.state_id == genesis.state_id
    assert reloaded.version == genesis.version
    assert reloaded.predecessor == genesis.predecessor
    assert state_record_hash(reloaded) == expected_hash
    assert second_core.get(genesis.state_id) == reloaded


def test_g3_f01_preserves_version_and_predecessor_across_restart(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "statecore.sqlite3"
    first_core = StateCore(SQLiteStatePersistencePort(db_path))
    genesis = _record("state:sofia:1", version=1, predecessor=None, value="alpha")
    _write(first_core, genesis)

    del first_core

    second_core = StateCore(SQLiteStatePersistencePort(db_path))
    successor = _record(
        "state:sofia:2",
        version=2,
        predecessor=genesis.state_id,
        value="beta",
    )
    _write(second_core, successor)

    del second_core

    third_core = StateCore(SQLiteStatePersistencePort(db_path))
    reloaded = third_core.current("SOFIA")
    assert reloaded is not None
    assert reloaded.state_id == successor.state_id
    assert reloaded.version == 2
    assert reloaded.predecessor == genesis.state_id
    assert state_record_hash(third_core.get(genesis.state_id)) == state_record_hash(
        genesis
    )
    assert state_record_hash(reloaded) == state_record_hash(successor)


def test_g3_f01_write_requires_fresh_durable_readback_match(tmp_path: Path) -> None:
    db_path = tmp_path / "statecore.sqlite3"
    port = SQLiteStatePersistencePort(db_path)
    core = StateCore(port)
    record = _record("state:sofia:1", version=1, predecessor=None, value="alpha")
    _write(core, record)

    port.corrupt_payload_for_test(record.state_id, {"value": "tampered"})

    with pytest.raises(RuntimeError, match="state_durable_integrity_failed"):
        StateCore(SQLiteStatePersistencePort(db_path))
