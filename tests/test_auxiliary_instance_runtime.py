from pathlib import Path

import pytest

from app.ocs_instances.auxiliary_runtime import (
    AuxiliaryAuthority,
    AuxiliaryInstanceRuntime,
)
from app.ocs_instances.contracts import InstanceBindingError


def authority() -> AuxiliaryAuthority:
    return AuxiliaryAuthority("auth:1", ("bounded-capability",), "SOFIA")


def test_spawn_replay_and_restart_are_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "aux.sqlite3"
    calls = []

    def execute(parent: str, capability: str, task: str) -> tuple[str, str, str]:
        calls.append(task)
        return ("instance:1", "SUCCEEDED", "result:1")

    first = AuxiliaryInstanceRuntime(path).spawn_instance(
        parent_mission_id="mission:1", requesting_ocs="SOFIA",
        target_capability="bounded-capability", bounded_task="task",
        authority=authority(), operation_id="op:1", executor=execute,
    )
    second = AuxiliaryInstanceRuntime(path).spawn_instance(
        parent_mission_id="mission:1", requesting_ocs="SOFIA",
        target_capability="bounded-capability", bounded_task="task",
        authority=authority(), operation_id="op:1", executor=execute,
    )
    assert first == second
    assert calls == ["task"]
    assert AuxiliaryInstanceRuntime(path).reconcile("op:1") == first


def test_invalid_authority_and_conflict_fail_closed(tmp_path: Path) -> None:
    runtime = AuxiliaryInstanceRuntime(tmp_path / "aux.sqlite3")
    with pytest.raises(PermissionError):
        runtime.spawn_instance(
            parent_mission_id="m", requesting_ocs="SOFIA",
            target_capability="bounded-capability", bounded_task="t",
            authority=None, operation_id="o", executor=lambda *_: ("i", "S", "r"),
        )
    runtime.spawn_instance(
        parent_mission_id="m", requesting_ocs="SOFIA",
        target_capability="bounded-capability", bounded_task="t",
        authority=authority(), operation_id="o", executor=lambda *_: ("i", "S", "r"),
    )
    with pytest.raises(InstanceBindingError, match="IDEMPOTENCY_CONFLICT"):
        runtime.spawn_instance(
            parent_mission_id="m", requesting_ocs="SOFIA",
            target_capability="bounded-capability", bounded_task="different",
            authority=authority(), operation_id="o",
            executor=lambda *_: ("i2", "S", "r2"),
        )


def test_missing_executor_never_simulates_spawn(tmp_path: Path) -> None:
    with pytest.raises(
        InstanceBindingError, match="material_instance_executor_required"
    ):
        AuxiliaryInstanceRuntime(tmp_path / "aux.sqlite3").spawn_instance(
            parent_mission_id="m", requesting_ocs="SOFIA",
            target_capability="bounded-capability", bounded_task="t",
            authority=authority(), operation_id="o", executor=None,
        )
