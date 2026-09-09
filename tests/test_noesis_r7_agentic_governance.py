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
AUTH_SOURCE = "founder-authorized:noesis-r7"


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
        authority_source_ref=AUTH_SOURCE,
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
    rt.bind_lease(lease())
    return rt


def test_exact_r1_r6_binding_and_l0_preservation() -> None:
    compatible = R1R6IntegrationContract.canonical()
    compatible.assert_compatible()
    assert compatible.scheduler_is_authority is False
    assert compatible.governance_may_mutate_l0 is False
    with pytest.raises(R7InvariantError, match="R7_L0_BINDING_DRIFT"):
        replace(compatible, l0_binding_hash="forged").assert_compatible()
    with pytest.raises(
        R7InvariantError,
        match="R7_REQUIRES_EXACT_CANONICAL_R1_R6",
    ):
        replace(
            compatible,
            active_layers=compatible.active_layers[:-1],
        ).assert_compatible()


def test_state_ownership_and_cross_owner_write_zero_mutation() -> None:
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
    rt.bind_lease(lease("governor:evidence", lease_id="lease:r7:evidence"))
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
    assert rt.state == before


def test_scheduler_priority_and_authority_boundary() -> None:
    rt = runtime()
    rt.schedule(
        GovernanceTask("task:1", MISSION, "governor:state", "SET_STATE", 1, 1)
    )
    rt.schedule(
        GovernanceTask("task:2", MISSION, "governor:state", "SET_STATE", 10, 2)
    )
    first = rt.next_task()
    second = rt.next_task()
    assert first is not None and first.task_id == "task:2"
    assert second is not None and second.task_id == "task:1"

    forbidden = replace(
        governor(),
        allowed_commands=governor().allowed_commands + ("MERGE",),
    )
    other = R7GovernanceRuntime(
        mission_id=MISSION,
        integration=R1R6IntegrationContract.canonical(),
    )
    other.register_governor(forbidden)
    with pytest.raises(R7InvariantError, match="SCHEDULER_CANNOT_GRANT_AUTHORITY"):
        other.schedule(
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
            "msg:1",
            MISSION,
            "governor:state",
            "governor:communication",
            "HANDOFF_FOR_REVIEW",
            "evidence:r7:1",
        )
    )
    assert rt.communications[0].authority_transferred is False
    with pytest.raises(
        R7InvariantError,
        match="GOVERNOR_COMMUNICATION_MUST_NOT_TRANSFER_AUTHORITY",
    ):
        CommunicationEnvelope(
            "msg:forged",
            MISSION,
            "governor:state",
            "governor:communication",
            "FORGED_TRANSFER",
            "none",
            authority_transferred=True,
        )


def test_lease_expiry_fencing_and_material_effect_fail_closed() -> None:
    rt = runtime()
    expired = rt.execute(command(command_id="cmd:expired"), now=250.0)
    assert expired.reason == "LEASE_EXPIRED_OR_NOT_YET_VALID"
    assert expired.mutation_count == 0

    rt2 = runtime()
    assert rt2.fence_generation("governor:state") == 2
    stale = rt2.execute(command(command_id="cmd:stale"), now=110.0)
    assert stale.reason == "STALE_GENERATION"
    assert stale.mutation_count == 0
    rt2.bind_lease(lease(lease_id="lease:r7:gen2", generation=2))
    effect = rt2.execute(
        command(
            command_id="cmd:effect",
            lease_id="lease:r7:gen2",
            generation=2,
            idempotency_key="idem:effect",
            material_effect_requested=True,
        ),
        now=110.0,
    )
    assert effect.reason == "R7_INTERNAL_GOVERNANCE_CANNOT_EXECUTE_MATERIAL_EFFECT"
    assert effect.mutation_count == 0
    assert effect.material_effect_performed is False


def test_replay_divergence_and_receipt_integrity() -> None:
    rt = runtime()
    first_command = command()
    first = rt.execute(first_command, now=110.0)
    replay = rt.execute(first_command, now=111.0)
    assert first.state_version_after == 1
    assert replay.status.value == "REPLAYED"
    assert replay.mutation_count == 0
    assert rt.state_version == 1
    assert rt.verify_receipt_chain() is True
    with pytest.raises(R7InvariantError, match="IDEMPOTENCY_KEY_DIVERGENT_COMMAND"):
        rt.execute(
            replace(first_command, write_set={"current_phase": "DIVERGENT"}),
            now=112.0,
        )


def test_failure_injection_pre_and_post_commit_converges() -> None:
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
    replay = rt.execute(command(), now=112.0)
    assert replay.status.value == "REPLAYED"
    assert replay.mutation_count == 0
    assert rt.state_version == 1
    assert rt.verify_receipt_chain() is True


def test_owner_scoped_recovery_preserves_other_governor_state() -> None:
    rt = runtime()
    rt.register_governor(
        governor(
            "governor:evidence",
            owned=("evidence_refs",),
            function=GovernorFunction.EVIDENCE,
        )
    )
    rt.bind_lease(lease("governor:evidence", lease_id="lease:r7:evidence"))
    rt.execute(command(), now=110.0)
    rt.checkpoint("checkpoint:r7:1", now=111.0)
    rt.execute(
        command(
            command_id="cmd:state-later",
            write_set={"blockers": ["finding:1"]},
            idempotency_key="idem:state-later",
            expected_state_version=1,
        ),
        now=112.0,
    )
    rt.execute(
        command(
            command_id="cmd:evidence-later",
            governor_id="governor:evidence",
            lease_id="lease:r7:evidence",
            write_set={"evidence_refs": ["e1"]},
            idempotency_key="idem:evidence-later",
            expected_state_version=2,
        ),
        now=113.0,
    )
    assert rt.state_version == 3
    assert rt.recover_governor(
        "governor:state",
        checkpoint_id="checkpoint:r7:1",
    ) == 2
    assert rt.state_version == 4
    assert "blockers" not in rt.state
    assert rt.state["evidence_refs"] == ["e1"]
    stale = rt.execute(
        command(
            command_id="cmd:old",
            idempotency_key="idem:old",
            expected_state_version=4,
        ),
        now=114.0,
    )
    assert stale.reason == "STALE_GENERATION"


def test_rollback_is_monotonic_and_invalidates_post_checkpoint_key() -> None:
    rt = runtime()
    rt.execute(command(), now=110.0)
    rt.checkpoint("checkpoint:r7:rollback", now=111.0)
    later = command(
        command_id="cmd:later",
        write_set={"blockers": ["b1"]},
        idempotency_key="idem:later",
        expected_state_version=1,
    )
    rt.execute(later, now=112.0)
    rt.rollback_to_checkpoint("checkpoint:r7:rollback")
    assert rt.state_version == 3
    assert "blockers" not in rt.state
    assert rt.verify_receipt_chain() is True
    with pytest.raises(
        R7InvariantError,
        match="IDEMPOTENCY_KEY_INVALIDATED_BY_ROLLBACK",
    ):
        rt.execute(later, now=113.0)
