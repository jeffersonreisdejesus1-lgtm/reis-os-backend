from __future__ import annotations

import pytest
from app.gica.increment_decision import (
    DecisionRequirements,
    can_promote,
    decide,
)
from app.gica.increment_evidence import (
    ActorReference,
    ActorType,
    EvidenceReference,
    EvidenceStatus,
    EvidenceType,
    EvidenceValue,
    ExecutionEvidence,
    ExecutionStatus,
)
from app.gica.increment_ledger import IncrementReceiptConflict, InMemoryIncrementLedger
from app.gica.increment_receipt import (
    SCHEMA_VERSION,
    Decision,
    FileChange,
    FileChangeType,
    IncrementReceipt,
)


def receipt(
    *,
    head_after_status: EvidenceStatus = EvidenceStatus.OBSERVED,
    test_status: ExecutionStatus = ExecutionStatus.PASS,
    reviewer: ActorReference | None = ActorReference("iris", ActorType.OCS),
    build_status: ExecutionStatus = ExecutionStatus.NOT_EXECUTED,
) -> IncrementReceipt:
    before = EvidenceValue(EvidenceStatus.OBSERVED, "a" * 40, "git-before")
    after = EvidenceValue(
        head_after_status,
        "b" * 40 if head_after_status is EvidenceStatus.OBSERVED else None,
        "git-after" if head_after_status is EvidenceStatus.OBSERVED else None,
    )
    files = EvidenceValue(
        EvidenceStatus.OBSERVED,
        (
            FileChange(
                "app/gica/example.py",
                FileChangeType.ADDED,
                after_blob_sha="c" * 40,
            ),
        ),
        "git-diff",
    )
    test = ExecutionEvidence(
        test_status,
        "pytest tests/test_gica_increment_receipt.py",
        0 if test_status is ExecutionStatus.PASS else None,
        evidence_refs=("test-log",),
    )
    build = ExecutionEvidence(
        build_status,
        "build",
        0 if build_status is ExecutionStatus.PASS else None,
        evidence_refs=("build-log",) if build_status is ExecutionStatus.PASS else (),
    )
    runtime = ExecutionEvidence(ExecutionStatus.NOT_EXECUTED)
    return IncrementReceipt(
        SCHEMA_VERSION,
        IncrementReceipt.expected_receipt_id(
            schema_version=SCHEMA_VERSION,
            intention_id="i-1",
            program="GICA",
            repository="repo",
            branch="branch",
            head_before=before,
            head_after=after,
        ),
        "i-1",
        "GICA",
        "repo",
        "branch",
        before,
        after,
        files,
        ("pytest tests/test_gica_increment_receipt.py",),
        test,
        build,
        runtime,
        (
            EvidenceReference("git-diff", EvidenceType.GITHUB, "commit/b"),
            EvidenceReference("test-log", EvidenceType.TEST, "run/1"),
        ),
        Decision(Decision.HOLD, "draft"),
        "2026-09-16T00:00:00Z",
        ActorReference("sofia", ActorType.OCS),
        reviewer,
    )


def test_valid_pass_receipt_and_deterministic_id() -> None:
    item = receipt()
    assert item.receipt_id == receipt().receipt_id
    assert decide(item) == Decision(Decision.PASS, "all_applicable_requirements_satisfied")


def test_test_failure_requires_repair() -> None:
    assert decide(receipt(test_status=ExecutionStatus.FAIL)) == Decision(
        Decision.REPAIR,
        "tests_failed",
    )


def test_missing_head_or_reviewer_holds() -> None:
    assert decide(receipt(head_after_status=EvidenceStatus.UNKNOWN)) == Decision(
        Decision.HOLD,
        "head_after_not_observed",
    )
    assert decide(receipt(reviewer=None)) == Decision(
        Decision.HOLD,
        "reviewer_missing",
    )


def test_required_test_and_build_rules() -> None:
    item = receipt(build_status=ExecutionStatus.NOT_EXECUTED)
    requirements = DecisionRequirements(
        required_test_commands=("pytest tests/test_gica_increment_receipt.py",),
        build_required=True,
    )
    assert decide(item, requirements).value == Decision.HOLD
    passed = receipt(build_status=ExecutionStatus.PASS)
    assert decide(passed, DecisionRequirements(build_required=True)).value == Decision.PASS


def test_ledger_replay_and_conflict() -> None:
    ledger = InMemoryIncrementLedger()
    item = receipt()
    assert ledger.put(item) == item.receipt_id
    assert ledger.put(item) == item.receipt_id
    conflict = receipt()
    object.__setattr__(conflict, "created_at", "different")
    with pytest.raises(IncrementReceiptConflict):
        ledger.put(conflict)


def test_immutable_decided_receipt() -> None:
    item = receipt()
    with pytest.raises(AttributeError):
        item.decision = Decision(Decision.PASS, "late")  # type: ignore[misc]


def test_no_promotion() -> None:
    assert can_promote(receipt()) is False

