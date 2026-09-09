from __future__ import annotations

from dataclasses import replace

import pytest

from app.noesis_r7 import (
    CommunicationEnvelope,
    GovernorContract,
    GovernorFunction,
    GovernorLease,
    GovernanceCommand,
    GovernanceTask,
    R1R6IntegrationContract,
    R7GovernanceRuntime,
    R7InvariantError,
)
from app.noesis_r7.contracts import FailurePoint


MISSION = "mission:noesis:r7"
AUTH = "authority:noesis:r7:internal-governance"


def governor(
    governor_id: str = "governor:state",
    *,
    owned: tuple[str, ...] = ("current_phase", "blockers"),
    function: GovernorFunction = GovernorFunction.STATE,
) -> GovernorContract:
    return GovernorContract(
        governor_id=governor_id,
        function=function,
        owned_state_keys=owned,
        readable_state_keys=owned + ("mission_id",),
        allowed_commands=("SET_STATE", "RECONCILE"),
        authority_ceiling_ref=AUTH,
    )


def lease(
    governor_id: str = "governor:state",
    *,
    lease_id: str = "lease:r7:1",
    generation: int = 1,
    now: float = 100.0,
) -> GovernorLease:
    return GovernorLease(
        lease_id=lease_id,
        governor_id=governor_id,
        mission_id=MISSION,
        authority_ref=AUTH,
        scope=("state:noesis:r7",),
        generation=generation,
        issued_at=now,
        not_before=now,
        expires_at=now + 100.0,
        max_uses=10,
    )


def command(
    *,
    command_id: str = "cmd:1",
    governor_id: str = "governor:state",
    lease_id: str = "lease:r7:1",
    generation: int = 1,
    write_set: dict[str, object] | None = None,
    idempotency_key: str = "idem:1",
    expected_state_version: int = 0,
    command_type: str = "SET_STATE",
    material_effect_requested: bool = False,
) -> GovernanceCommand:
    return GovernanceCommand(
        command_id=command_id,
        mission_id=MISSION,
        governor_id=governor_id,
        generation=generation,
        lease_id=lease_id,
        authority_ref=AUTH,
        command_type=command_type,
        write_set=write_set or {"current_phase": "IMPLEMENTATION"},
        idempotency_key=idempotency_key,
        expected_state_version=expected_state_version,
        scope=("state:noesis:r7",),
        material_effect_requested=material_effect_requested,
    )


def runtime() -> R7GovernanceRuntime:
    rt = R7GovernanceRuntime(
        mission_id=MISSION,
        integration=R1R6IntegrationContract.canonical(),
        initial_state={"mission_id": MISSION, "current_phase": "INTAKE"},
    )
    rt.register_governor(governor())
    rt.issue_lease(lease())
    return rt


def test_r7_requires_exact_canonical_r1_r6_and_preserves_l0() -> None:
    compatible = R1R6IntegrationContract.canonical()
    compatible.assert_compatible()
    assert compatible.scheduler_is_authority is False
    assert compatible.governance_may_mutate_l0 is False

    with pytest.raises(R7InvariantError, match="R7_L0_BINDING_DRIFT"):
        replace(compatible, l0_binding_hash="forged").assert_compatible()

    with pytest.raises(R7InvariantError, match="R7_REQUIRES_EXACT_CANONICAL_R1_R6"):
        replace(compatible, active_layers=compatible.active_layers[:-1]).assert_compatible()


def test_state_ownership_is_unique_and_cross_governor_write_denies_without_mutation() -> None:
    rt = runtime()
    with pytest.raises(R7InvariantError, match="STATE_OWNERSHIP_CONFLICT"):
        rt.register_governor(governor("governor:other", owned=("blockers",)))

    rt.register_governor(
        governor(
            "governor:evidence",
            owned=("evidence_refs",),
            function=GovernorFunction.EVIDENCE,
        )
    )
    rt.issue_lease(lease("governor:evidence", lease_id="lease:r7:evidence"))
    before = rt.state
    receipt = rt.execute(
        command(
            command_id="cmd:cross-owner",
            governor_id="governor:evidence",
            lease_id="lease:r7:evidence",
            write_set={"current_phase": "FORGED"},
            idempotency_key="idem:cross-owner",
        ),
        now=110.0,
    )
    assert receipt.reason == "STATE_OWNERSHIP_VIOLATION"
    assert receipt.mutation_count == 0
    assert receipt.state_version_after == receipt.state_version_before
    assert rt.state == before


def test_scheduler_orders_deterministically_and_cannot_grant_forbidden_authority() -> None:
    rt = runtime()
    rt.schedule(
        GovernanceTask("task:1", MISSION, "governor:state", "SET_STATE", 1, 1)
    )
    rt.schedule(
        GovernanceTask("task:2", MISSION, "governor:state", "SET_STATE", 10, 2)
    )
    assert rt.next_task() is not None
    next_task = rt.next_task()
    assert next_task is not None
    assert next_task.task_id == "task:1"

    forbidden = replace(
        governor(),
        allowed_commands=governor().allowed_commands + ("MERGE",),
    )
    second = R7GovernanceRuntime(
        mission_id=MISSION,
        integration=R1R6IntegrationContract.canonical(),
    )
    second.register_governor(forbidden)
    with pytest.raises(R7InvariantError, match="SCHEDULER_CANNOT_GRANT_AUTHORITY"):
        second.schedule(
            GovernanceTask("task:merge", MISSION, "governor:state", "MERGE", 1, 1)
        )


def test_communication_never_transfers_authority() -> None:
    rt = runtime()
    rt.register_governor(
        governor(
            "governor:communication",
            owned=("last_message_ref",),
            function=GovernorFunction.COMMUNICATION,
        )
    )
    rt.communicate(
        CommunicationEnvelope(
            message_id="msg:1",
            mission_id=MISSION,
            source_governor_id="governor:state",
            target_governor_id="governor:communication",
            relation="HANDOFF_FOR_REVIEW",
            payload_ref="evidence:r7:1",
        )
    )
    assert len(rt.communications) == 1
    assert rt.communications[0].authority_transferred is False

    with pytest.raises(
        R7InvariantError,
        match="GOVERNOR_COMMUNICATION_MUST_NOT_TRANSFER_AUTHORITY",
    ):
        CommunicationEnvelope(
            message_id="msg:forged",
            mission_id=MISSION,
            source_governor_id="governor:state",
            target_governor_id="governor:communication",
            relation="FORGED_TRANSFER",
            payload_ref="none",
            authority_transferred=True,
        )


def test_lease_expiry_stale_generation_and_fencing_fail_closed() -> None:
    rt = runtime()
    expired = rt.execute(command(command_id="cmd:expired"), now=250.0)
    assert expired.reason == "LEASE_EXPIRED_OR_NOT_YET_VALID"
    assert expired.mutation_count == 0

    rt2 = runtime()
    assert rt2.fence_generation("governor:state") == 2
    stale = rt2.execute(command(command_id="cmd:stale"), now=110.0)
    assert stale.reason == "STALE_GENERATION"
    assert stale.mutation_count == 0

    rt2.issue_lease(lease(lease_id="lease:r7:gen2", generation=2))
    accepted = rt2.execute(
        command(
            command_id="cmd:gen2",
            lease_id="lease:r7:gen2",
            generation=2,
            idempotency_key="idem:gen2",
        ),
        now=110.0,
    )
    assert accepted.mutation_count == 1


def test_idempotent_replay_does_not_duplicate_and_divergent_payload_conflicts() -> None:
    rt = runtime()
    first_command = command()
    first = rt.execute(first_command, now=110.0)
    replay = rt.execute(first_command, now=111.0)
    assert first.state_version_after == 1
    assert replay.status.value == "REPLAYED"
    assert rt.state_version == 1
    assert len(rt.receipts) == 1

    with pytest.raises(R7InvariantError, match="IDEMPOTENCY_KEY_DIVERGENT_COMMAND"):
        rt.execute(
            replace(first_command, write_set={"current_phase": "DIVERGENT"}),
            now=112.0,
        )


def test_r7_refuses_material_effect_even_with_valid_internal_lease() -> None:
    rt = runtime()
    receipt = rt.execute(
        command(command_id="cmd:effect", material_effect_requested=True),
        now=110.0,
    )
    assert receipt.reason == "R7_INTERNAL_GOVERNANCE_CANNOT_EXECUTE_MATERIAL_EFFECT"
    assert receipt.material_effect_performed is False
    assert receipt.mutation_count == 0


def test_failure_injection_pre_commit_is_zero_mutation_after_commit_is_recoverable() -> None:
    rt = runtime()
    before = rt.state
    rt.inject_failure(FailurePoint.BEFORE_COMMIT)
    with pytest.raises(RuntimeError, match="injected_failure_before_commit"):
        rt.execute(command(), now=110.0)
    assert rt.state == before
    assert rt.state_version == 0
    assert len(rt.receipts) == 0

    rt.inject_failure(FailurePoint.AFTER_COMMIT)
    with pytest.raises(RuntimeError, match="injected_failure_after_commit"):
        rt.execute(command(), now=111.0)
    assert rt.state_version == 1
    assert len(rt.receipts) == 1
    replay = rt.execute(command(), now=112.0)
    assert replay.status.value == "REPLAYED"
    assert rt.state_version == 1
    assert len(rt.receipts) == 1


def test_checkpoint_recovery_fences_predecessor_and_restores_allowed_state() -> None:
    rt = runtime()
    rt.execute(command(), now=110.0)
    checkpoint = rt.checkpoint("checkpoint:r7:1", now=111.0)
    assert checkpoint.state_version == 1

    rt.execute(
        command(
            command_id="cmd:2",
            write_set={"blockers": ["finding:1"]},
            idempotency_key="idem:2",
            expected_state_version=1,
        ),
        now=112.0,
    )
    assert rt.state_version == 2
    next_generation = rt.recover_governor(
        "governor:state",
        checkpoint_id="checkpoint:r7:1",
    )
    assert next_generation == 2
    assert rt.state_version == 1
    assert "blockers" not in rt.state

    stale = rt.execute(
        command(
            command_id="cmd:old-after-recovery",
            idempotency_key="idem:old-after-recovery",
            expected_state_version=1,
        ),
        now=113.0,
    )
    assert stale.reason == "STALE_GENERATION"
    assert stale.mutation_count == 0


def test_receipt_chain_and_internal_rollback_are_deterministic() -> None:
    rt = runtime()
    rt.execute(command(), now=110.0)
    rt.checkpoint("checkpoint:r7:rollback", now=111.0)
    rt.execute(
        command(
            command_id="cmd:later",
            write_set={"blockers": ["b1"]},
            idempotency_key="idem:later",
            expected_state_version=1,
        ),
        now=112.0,
    )
    assert rt.verify_receipt_chain() is True
    rt.rollback_to_checkpoint("checkpoint:r7:rollback")
    assert rt.state_version == 1
    assert "blockers" not in rt.state
    assert rt.verify_receipt_chain() is True
