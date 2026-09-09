from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.noesis_r7 import (
    GovernorContract,
    GovernorFunction,
    GovernorLease,
    GovernanceCommand,
    R1R6IntegrationContract,
    R7DurableRuntime,
    R7InvariantError,
)
from app.noesis_r7.contracts import FailurePoint

MISSION = "mission:noesis:r7:durable"
AUTH = "authority:noesis:r7:durable"
AUTH_SOURCE = "founder-authorized:noesis-r7"


def contract() -> GovernorContract:
    return GovernorContract(
        governor_id="governor:durable-state",
        function=GovernorFunction.STATE,
        owned_state_keys=("phase", "findings"),
        readable_state_keys=("phase", "findings"),
        allowed_commands=("SET_STATE",),
        authority_ceiling_ref=AUTH,
    )


def lease(
    *,
    generation: int = 1,
    lease_id: str = "lease:durable:1",
) -> GovernorLease:
    return GovernorLease(
        lease_id=lease_id,
        governor_id="governor:durable-state",
        mission_id=MISSION,
        authority_ref=AUTH,
        authority_source_ref=AUTH_SOURCE,
        scope=("state:noesis:r7",),
        generation=generation,
        issued_at=100.0,
        not_before=100.0,
        expires_at=500.0,
        max_uses=20,
    )


def command(
    *,
    command_id: str = "cmd:durable:1",
    idempotency_key: str = "idem:durable:1",
    lease_id: str = "lease:durable:1",
    generation: int = 1,
    expected_state_version: int = 0,
    write_set: dict[str, object] | None = None,
) -> GovernanceCommand:
    return GovernanceCommand(
        command_id=command_id,
        mission_id=MISSION,
        governor_id="governor:durable-state",
        generation=generation,
        lease_id=lease_id,
        authority_ref=AUTH,
        command_type="SET_STATE",
        write_set=write_set or {"phase": "IMPLEMENTATION"},
        idempotency_key=idempotency_key,
        expected_state_version=expected_state_version,
        scope=("state:noesis:r7",),
    )


def open_runtime(path: Path) -> R7DurableRuntime:
    return R7DurableRuntime(
        mission_id=MISSION,
        integration=R1R6IntegrationContract.canonical(),
        database_path=path,
        initial_state={"phase": "INTAKE"},
    )


def bootstrap(path: Path) -> R7DurableRuntime:
    runtime = open_runtime(path)
    runtime.register_governor(contract())
    runtime.bind_lease(lease())
    return runtime


def test_restart_restores_state_receipts_lease_and_idempotency(tmp_path: Path) -> None:
    path = tmp_path / "r7.sqlite3"
    first = bootstrap(path)
    receipt = first.execute(command(), now=110.0)
    assert receipt.mutation_count == 1
    assert first.state_version == 1
    assert first.verify_snapshot_chain() is True

    restarted = open_runtime(path)
    assert restarted.state == {"phase": "IMPLEMENTATION"}
    assert restarted.state_version == 1
    assert restarted.verify_receipt_chain() is True
    assert restarted.verify_snapshot_chain() is True
    replay = restarted.execute(command(), now=111.0)
    assert replay.status.value == "REPLAYED"
    assert replay.mutation_count == 0
    assert restarted.state_version == 1


def test_post_commit_crash_restart_replays_without_duplicate(tmp_path: Path) -> None:
    path = tmp_path / "r7-crash.sqlite3"
    first = bootstrap(path)
    first.inject_failure(FailurePoint.AFTER_COMMIT)
    with pytest.raises(RuntimeError, match="injected_failure_after_commit"):
        first.execute(command(), now=110.0)

    restarted = open_runtime(path)
    assert restarted.state_version == 1
    assert restarted.state["phase"] == "IMPLEMENTATION"
    replay = restarted.execute(command(), now=111.0)
    assert replay.status.value == "REPLAYED"
    assert replay.mutation_count == 0
    assert restarted.state_version == 1


def test_recovery_fencing_is_monotonic_and_survives_restart(tmp_path: Path) -> None:
    path = tmp_path / "r7-recovery.sqlite3"
    first = bootstrap(path)
    first.execute(command(), now=110.0)
    first.checkpoint("checkpoint:durable:1", now=111.0)
    first.execute(
        command(
            command_id="cmd:durable:2",
            idempotency_key="idem:durable:2",
            expected_state_version=1,
            write_set={"findings": ["f1"]},
        ),
        now=112.0,
    )
    assert first.state_version == 2
    assert first.recover_governor(
        "governor:durable-state",
        checkpoint_id="checkpoint:durable:1",
    ) == 2
    assert first.state_version == 3
    first.bind_lease(lease(generation=2, lease_id="lease:durable:2"))

    restarted = open_runtime(path)
    assert restarted.current_generation("governor:durable-state") == 2
    assert restarted.state_version == 3
    assert "findings" not in restarted.state
    stale = restarted.execute(
        command(
            command_id="cmd:stale",
            idempotency_key="idem:stale",
            expected_state_version=3,
        ),
        now=113.0,
    )
    assert stale.reason == "STALE_GENERATION"
    assert stale.mutation_count == 0
    current = restarted.execute(
        command(
            command_id="cmd:current",
            idempotency_key="idem:current",
            lease_id="lease:durable:2",
            generation=2,
            expected_state_version=3,
            write_set={"findings": ["recovered"]},
        ),
        now=114.0,
    )
    assert current.mutation_count == 1
    assert restarted.state_version == 4


def test_stale_writer_is_fenced_and_reconciles_to_durable_head(tmp_path: Path) -> None:
    path = tmp_path / "r7-cas.sqlite3"
    first = bootstrap(path)
    second = open_runtime(path)

    accepted = first.execute(command(), now=110.0)
    assert accepted.mutation_count == 1
    competing = command(
        command_id="cmd:competing",
        idempotency_key="idem:competing",
        write_set={"phase": "COMPETING"},
    )
    with pytest.raises(R7InvariantError, match="R7_DURABLE_STALE_WRITER"):
        second.execute(competing, now=111.0)
    assert second.state == {"phase": "IMPLEMENTATION"}
    assert second.state_version == 1
    assert open_runtime(path).state == {"phase": "IMPLEMENTATION"}


def test_snapshot_tamper_fails_closed_on_restart(tmp_path: Path) -> None:
    path = tmp_path / "r7-tamper.sqlite3"
    first = open_runtime(path)
    first.register_governor(contract())
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            UPDATE r7_runtime_snapshot_journal
            SET snapshot_json = ?
            WHERE seq = (
                SELECT MAX(seq) FROM r7_runtime_snapshot_journal
                WHERE mission_id = ?
            )
            """,
            ('{"mission_id":"forged"}', MISSION),
        )
    with pytest.raises(
        R7InvariantError,
        match="R7_DURABLE_SNAPSHOT_INTEGRITY_FAILURE",
    ):
        open_runtime(path)
