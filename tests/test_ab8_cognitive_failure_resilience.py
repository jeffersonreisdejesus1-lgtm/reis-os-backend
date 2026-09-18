from app.cognitive_validation.failure_resilience import (
    CognitiveFailureResilienceGate,
    FaultKind,
    FaultProbe,
    ProtectiveAction,
    run_ab8_fault_matrix,
)


def test_stale_memory_is_denied() -> None:
    result = CognitiveFailureResilienceGate().evaluate(
        FaultProbe(kind=FaultKind.STALE_MEMORY, presented_memory_version=6, current_memory_version=7)
    )
    assert result.action is ProtectiveAction.DENY
    assert result.mutation_allowed is False
    assert result.learning_allowed is False
    assert result.advance_allowed is False


def test_corrupt_memory_is_quarantined() -> None:
    result = CognitiveFailureResilienceGate().evaluate(
        FaultProbe(kind=FaultKind.CORRUPT_MEMORY, memory_checksum_valid=False)
    )
    assert result.action is ProtectiveAction.QUARANTINE
    assert result.reason == "memory_checksum_invalid"


def test_stale_generation_is_fenced() -> None:
    result = CognitiveFailureResilienceGate().evaluate(
        FaultProbe(kind=FaultKind.STALE_GENERATION, presented_generation=2, current_generation=3)
    )
    assert result.action is ProtectiveAction.DENY
    assert result.reason == "stale_generation_fenced"
    assert result.mutation_allowed is False


def test_duplicate_experience_is_idempotently_suppressed() -> None:
    result = CognitiveFailureResilienceGate().evaluate(
        FaultProbe(kind=FaultKind.DUPLICATE_EXPERIENCE, experience_seen=True)
    )
    assert result.action is ProtectiveAction.DEDUPLICATE
    assert result.mutation_allowed is False
    assert result.learning_allowed is False
    assert result.advance_allowed is True


def test_false_feedback_cannot_modify_learning() -> None:
    result = CognitiveFailureResilienceGate().evaluate(
        FaultProbe(kind=FaultKind.FALSE_FEEDBACK, feedback_verified=False)
    )
    assert result.action is ProtectiveAction.QUARANTINE
    assert result.learning_allowed is False
    assert result.advance_allowed is False


def test_partial_commit_enters_reconciliation() -> None:
    result = CognitiveFailureResilienceGate().evaluate(
        FaultProbe(kind=FaultKind.PARTIAL_COMMIT, commit_complete=False)
    )
    assert result.action is ProtectiveAction.RECONCILE
    assert result.mutation_allowed is False
    assert result.advance_allowed is False


def test_corrupt_checkpoint_rolls_back() -> None:
    result = CognitiveFailureResilienceGate().evaluate(
        FaultProbe(kind=FaultKind.CORRUPT_CHECKPOINT, checkpoint_checksum_valid=False)
    )
    assert result.action is ProtectiveAction.ROLLBACK
    assert result.advance_allowed is False


def test_fault_matrix_covers_all_required_ab8_faults() -> None:
    matrix = run_ab8_fault_matrix()
    assert {item.kind for item in matrix} == set(FaultKind)
    assert all(item.learning_allowed is False for item in matrix)
    assert all(item.mutation_allowed is False for item in matrix)


def test_clean_controls_remain_operational() -> None:
    gate = CognitiveFailureResilienceGate()
    controls = (
        FaultProbe(kind=FaultKind.STALE_MEMORY),
        FaultProbe(kind=FaultKind.CORRUPT_MEMORY),
        FaultProbe(kind=FaultKind.STALE_GENERATION),
        FaultProbe(kind=FaultKind.FALSE_FEEDBACK),
        FaultProbe(kind=FaultKind.PARTIAL_COMMIT),
        FaultProbe(kind=FaultKind.CORRUPT_CHECKPOINT),
    )
    for probe in controls:
        result = gate.evaluate(probe)
        assert result.mutation_allowed is True
        assert result.learning_allowed is True
        assert result.advance_allowed is True
