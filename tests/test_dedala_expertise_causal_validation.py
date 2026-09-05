from __future__ import annotations

from dataclasses import replace

from app.expertise.causal_validation import (
    REPRESENTATIVE_ARCHITECTURE_CASES,
    evaluate_representative_case,
    evaluate_representative_suite,
)
from app.expertise.physiology import DedalaExpertisePhysiology
from app.universal_kernel.contracts import (
    ActionProposal,
    AuthorizationDecision,
    Evidence,
    ExecutionResult,
    RiskLevel,
)


class FakeKernel:
    def __init__(self) -> None:
        self.calls: list[ActionProposal] = []

    @property
    def institutional_run(self) -> bool:
        return True

    def execute(self, proposal: ActionProposal) -> ExecutionResult:
        self.calls.append(proposal)
        return ExecutionResult(
            authorized=True,
            effected=True,
            proven=True,
            reason="effect_proven",
            governance_decision=AuthorizationDecision.ALLOW,
            trace_id=proposal.trace_id,
        )


def _proposal(case_id: str) -> ActionProposal:
    return ActionProposal(
        action_id=f"ACT-{case_id}",
        actor="DÉDALA",
        ocs="DÉDALA",
        capability="architecture",
        operation="derive_and_execute",
        payload={"case_id": case_id},
        risk=RiskLevel.MEDIUM,
        evidence=(Evidence(ref="LOCAL-RUNTIME-BOUNDARY", passed=True),),
        authority_ref="AUTH-DEDALA-CAUSAL-001",
        trace_id=f"TRACE-{case_id}",
    )


def test_four_representative_families_have_bounded_causal_consumption() -> None:
    receipts = evaluate_representative_suite()

    assert len(receipts) == 4
    assert all(receipt.causal_consumption_proven for receipt in receipts)
    assert all(
        receipt.reason == "bounded_causal_expertise_consumption_proven"
        for receipt in receipts
    )
    assert all(receipt.identity_effect == "NONE" for receipt in receipts)
    assert all(receipt.authority_effect == "NONE" for receipt in receipts)
    assert all(receipt.canon_effect == "NONE" for receipt in receipts)

    families = {
        source_id.split("-", 1)[0]
        for receipt in receipts
        for source_id in receipt.source_ids
    }
    assert {"FOWLER", "KLEPPMANN", "NEWMAN", "HOHPE"}.issubset(families)


def test_each_case_selects_expected_lens_and_expected_source_family() -> None:
    for case in REPRESENTATIVE_ARCHITECTURE_CASES:
        receipt = evaluate_representative_case(case)
        assert case.expected_lens in receipt.selected_lenses
        assert any(
            source_id.startswith(f"{case.expected_source_family}-")
            for source_id in receipt.source_ids
        )
        assert receipt.evidence_refs


def test_wrong_expected_family_fails_closed_instead_of_claiming_causality() -> None:
    case = REPRESENTATIVE_ARCHITECTURE_CASES[0]
    mismatched = replace(case, expected_source_family="KLEPPMANN")

    receipt = evaluate_representative_case(mismatched)

    assert receipt.causal_consumption_proven is False
    assert receipt.reason == "expected_source_family_not_retrieved"


def test_representative_cases_reach_kernel_without_authority_or_evidence_mutation() -> None:
    kernel = FakeKernel()
    physiology = DedalaExpertisePhysiology(kernel=kernel)

    for case in REPRESENTATIVE_ARCHITECTURE_CASES:
        proposal = _proposal(case.case_id)
        original_evidence = proposal.evidence
        original_authority = proposal.authority_ref

        result = physiology.execute(
            proposal,
            problem=case.problem,
            proposition=case.proposition,
            falsifier=lambda candidate, evidence, case=case: (
                case.expected_lens in candidate.candidate_lenses
                and any(
                    item.source_id.startswith(f"{case.expected_source_family}-")
                    for item in evidence
                )
            ),
            verifier=lambda candidate, evidence: (
                bool(candidate.evidence_refs)
                and all(item.authority_effect == "NONE" for item in evidence)
                and all(item.canon_effect == "NONE" for item in evidence)
            ),
        )

        assert result.material_execution_attempted is True
        assert result.kernel_result is not None
        assert result.kernel_result.proven is True
        assert result.identity_effect == "NONE"
        assert result.authority_effect == "NONE"
        assert result.canon_effect == "NONE"
        assert proposal.evidence == original_evidence
        assert proposal.authority_ref == original_authority

    assert len(kernel.calls) == 4
