from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from app.noesis_r7 import (
    GovernorContract,
    GovernorFunction,
    GovernorLease,
    GovernanceCommand,
    GovernanceTask,
    R1R6IntegrationContract,
    R7ArchitecturalReadiness,
    R7DurableRuntime,
    R7InvariantError,
)
from app.noesis_r7.contracts import FailurePoint

MISSION = "mission:noesis:r7:durable"
AUTH = "authority:noesis:r7:durable"
SOURCE = "founder-handoff:NOESIS-TO-AGORA-R7-REFACTOR-IMPLEMENTATION-001"
TEST_DERIVATION = "synthetic-test-only:r7-governor-derivation"


def readiness():
    return R7ArchitecturalReadiness(
        r7_i_taxonomy_frozen=True,
        r7_o_taxonomy_frozen=True,
        cross_taxonomy_complete=True,
        normalized_requirements_available=True,
        governor_derivation_valid=True,
        derivation_ref=TEST_DERIVATION,
    )


def contract():
    return GovernorContract(
        "governor:durable-state",
        GovernorFunction.STATE,
        ("phase", "findings"),
        ("phase", "findings"),
        ("SET_STATE",),
        AUTH,
    )


def lease(*, generation=1, lease_id="lease:durable:1"):
    return GovernorLease(
        lease_id,
        "governor:durable-state",
        MISSION,
        AUTH,
        SOURCE,
        ("state:noesis:r7",),
        generation,
        100.0,
        100.0,
        500.0,
        20,
    )


def command(*, command_id="cmd:durable:1", idempotency_key="idem:durable:1",
            lease_id="lease:durable:1", generation=1, expected_state_version=0,
            write_set=None):
    return GovernanceCommand(
        command_id,
        MISSION,
        "governor:durable-state",
        generation,
        lease_id,
        AUTH,
        "SET_STATE",
        write_set or {"phase": "IMPLEMENTATION"},
        idempotency_key,
        expected_state_version,
        ("state:noesis:r7",),
    )


def open_runtime(path: Path, *, derived=True):
    return R7DurableRuntime(
        mission_id=MISSION,
        integration=R1R6IntegrationContract.canonical(),
        database_path=path,
        initial_state={"phase": "INTAKE"},
        architectural_readiness=readiness() if derived else None,
    )


def admit(rt, cmd, *, priority=1):
    rt.schedule(
        GovernanceTask(
            task_id=cmd.command_id,
            mission_id=MISSION,
            governor_id=cmd.governor_id,
            command_type=cmd.command_type,
            priority=priority,
            created_seq=rt._task_seq + 1,
            command_id=cmd.command_id,
        )
    )


def execute(rt, cmd, *, now=110.0):
    admit(rt, cmd)
    return rt.execute(cmd, now=now)


def bootstrap(path):
    rt = open_runtime(path)
    rt.register_governor(contract())
    rt.bind_lease(lease())
    return rt


def test_durable_restart_refuses_materialized_governors_without_derivation_gate(tmp_path):
    path = tmp_path / "r7-gated.sqlite3"
    first = bootstrap(path)
    execute(first, command())
    with pytest.raises(R7InvariantError, match="PENDING_DERIVATION"):
        open_runtime(path, derived=False)


def test_restart_restores_state_receipts_leases_idempotency_and_scheduler(tmp_path):
    path = tmp_path / "r7.sqlite3"
    first = bootstrap(path)
    cmd = command()
    assert execute(first, cmd).mutation_count == 1
    pending = command(
        command_id="cmd:pending",
        idempotency_key="idem:pending",
        expected_state_version=1,
        write_set={"findings": ["pending"]},
    )
    admit(first, pending)
    restarted = open_runtime(path)
    assert restarted.state_version == 1
    assert restarted.verify_receipt_chain() is True
    assert restarted.verify_snapshot_chain() is True
    assert restarted.next_task().command_id == "cmd:pending"
    assert restarted.execute(pending, now=111.0).mutation_count == 1
    replay = restarted.execute(pending, now=112.0)
    assert replay.status.value == "REPLAYED"
    assert replay.mutation_count == 0


def test_post_commit_crash_restart_replay_is_exactly_once(tmp_path):
    path = tmp_path / "r7-crash.sqlite3"
    first = bootstrap(path)
    cmd = command()
    admit(first, cmd)
    first.inject_failure(FailurePoint.AFTER_COMMIT)
    with pytest.raises(RuntimeError, match="after_commit"):
        first.execute(cmd, now=110.0)
    restarted = open_runtime(path)
    assert restarted.state_version == 1
    replay = restarted.execute(cmd, now=111.0)
    assert replay.status.value == "REPLAYED"
    assert replay.mutation_count == 0
    assert restarted.state_version == 1


def test_recovery_fencing_survives_restart_and_version_is_monotonic(tmp_path):
    path = tmp_path / "r7-recovery.sqlite3"
    first = bootstrap(path)
    execute(first, command())
    first.checkpoint("cp:1", now=111.0)
    execute(
        first,
        command(
            command_id="cmd:2",
            idempotency_key="idem:2",
            expected_state_version=1,
            write_set={"findings": ["f1"]},
        ),
        now=112.0,
    )
    before = first.state_version
    assert first.recover_governor("governor:durable-state", checkpoint_id="cp:1") == 2
    assert first.state_version == before + 1
    first.bind_lease(lease(generation=2, lease_id="lease:durable:2"))
    restarted = open_runtime(path)
    assert restarted.current_generation("governor:durable-state") == 2
    stale = command(
        command_id="cmd:stale",
        idempotency_key="idem:stale",
        expected_state_version=restarted.state_version,
    )
    assert execute(restarted, stale, now=113.0).reason == "STALE_GENERATION"


def test_snapshot_tamper_fails_closed_on_restart(tmp_path):
    path = tmp_path / "r7-tamper.sqlite3"
    bootstrap(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE r7_runtime_snapshot_journal SET snapshot_json=? "
            "WHERE seq=(SELECT MAX(seq) FROM r7_runtime_snapshot_journal WHERE mission_id=?)",
            ('{"mission_id":"forged"}', MISSION),
        )
    with pytest.raises(R7InvariantError, match="R7_DURABLE_SNAPSHOT_INTEGRITY_FAILURE"):
        open_runtime(path)


def test_stale_writer_is_fenced_and_reconciled(tmp_path):
    path = tmp_path / "r7-stale.sqlite3"
    first = bootstrap(path)
    second = open_runtime(path)
    cmd = command()
    execute(first, cmd)
    with pytest.raises(R7InvariantError, match="R7_DURABLE_STALE_WRITER"):
        second.schedule(
            GovernanceTask(
                "cmd:second",
                MISSION,
                "governor:durable-state",
                "SET_STATE",
                1,
                second._task_seq + 1,
                "cmd:second",
            )
        )
    assert second.state_version == first.state_version
    assert second.verify_snapshot_chain() is True
