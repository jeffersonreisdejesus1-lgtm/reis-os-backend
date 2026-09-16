from __future__ import annotations

from dataclasses import dataclass

from .increment_evidence import EvidenceStatus, ExecutionStatus
from .increment_receipt import Decision, IncrementReceipt


@dataclass(frozen=True)
class DecisionRequirements:
    required_test_commands: tuple[str, ...] = ()
    build_required: bool = False
    runtime_required: bool = False


def decide(
    receipt: IncrementReceipt,
    requirements: DecisionRequirements = DecisionRequirements(),
) -> Decision:
    receipt.validate()
    if receipt.head_after.status is not EvidenceStatus.OBSERVED:
        return Decision(Decision.HOLD, "head_after_not_observed")
    if receipt.reviewer is None:
        return Decision(Decision.HOLD, "reviewer_missing")
    if receipt.files_changed.status is not EvidenceStatus.OBSERVED:
        return Decision(Decision.HOLD, "files_changed_not_observed")
    if receipt.test_result.status is ExecutionStatus.FAIL:
        return Decision(Decision.REPAIR, "tests_failed")
    if receipt.test_result.status is not ExecutionStatus.PASS:
        return Decision(Decision.HOLD, "tests_not_passed")
    missing_tests = set(requirements.required_test_commands) - set(
        receipt.test_commands
    )
    if missing_tests:
        return Decision(Decision.HOLD, "required_test_command_missing")
    if requirements.build_required and receipt.build_result.status is not ExecutionStatus.PASS:
        return Decision(Decision.REPAIR if receipt.build_result.status is ExecutionStatus.FAIL else Decision.HOLD, "build_requirement_unmet")
    if requirements.runtime_required and receipt.runtime_result.status is not ExecutionStatus.PASS:
        return Decision(
            Decision.REPAIR
            if receipt.runtime_result.status is ExecutionStatus.FAIL
            else Decision.HOLD,
            "runtime_requirement_unmet",
        )
    if not receipt.evidence_references:
        return Decision(Decision.HOLD, "evidence_missing")
    return Decision(Decision.PASS, "all_applicable_requirements_satisfied")


def can_promote(_: IncrementReceipt) -> bool:
    return False
