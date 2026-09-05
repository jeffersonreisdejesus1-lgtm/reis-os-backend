from __future__ import annotations

from dataclasses import replace

from app.expertise.assurance import (
    FalsificationReceipt,
    VerificationReceipt,
    candidate_binding,
    evidence_binding,
)
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

REVISION = "causal-suite-revision-001"


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


class CaseFalsifier:
    def __init__(self, case) -> None:
        self.case = case

    def evaluate(self, candidate, evidence, assessed_revision):
        survived = (
            self.case.expected_lens in candidate.candidate_lenses
            and any(item.source_family == self.case.expected_source_family for item in evidence)
        )
        return FalsificationReceipt(
            receipt_id=f"FALSIFY-{self.case.case_id}",
            candidate_binding=candidate_binding(candidate),
            evidence_binding=evidence_binding(evidence),
            assessed_revision=assessed_revision,
            procedure_id="representative-family-counterexample-check-v1",
            survived=survived,
            evidence_refs=candidate.evidence_refs,
        )


class CaseVerifier:
    def evaluate(self, candidate, evidence, assessed_revision):
        verified = bool(candidate.evidence_refs) and all(
            item.authority_effect == "NONE" and item.canon_effect == "NONE"
            for item in evidence
        )
        return VerificationReceipt(
            receipt_id="VERIFY-REPRESENTATIVE-CASE",
            candidate_binding=candidate_binding(candidate),
            evidence_binding=evidence_binding(evidence),
            assessed_revision=assessed_revision,
            procedure_id="bounded-evidence-integrity-check-v1",
            verified=verified,
            evidence_refs=candidate.evidence_refs,
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


def test_four_representative_families_have_bounded_routing_consumption() -> None:
    receipts = evaluate_representative_suite()
    assert len(receipts) == 4
    assert all(receipt.causal_consumption_proven for receipt in receipts)
    assert all(
        receipt.reason == "bounded_routing_and_evidence_attachment_causality_proven"
        for receipt in receipts
    )
    assert all(
        receipt.semantic_derivation_causality_proven is False for receipt in receipts
    )
    families = {
        source_id.split("-", 1)[0]
        for receipt in receipts
        for source_id in receipt.source_ids
    }
    assert {"FOWLER", "KLEPPMANN", "NEWMAN", "HOHPE"}.issubset(families)


def test_wrong_expected_family_fails_closed_instead_of_claiming_causality() -> None:
    case = REPRESENTATIVE_ARCHITECTURE_CASES[0]
    mismatched = replace(case, expected_source_family="KLEPPMANN")
    receipt = evaluate_representative_case(mismatched)
    assert receipt.causal_consumption_proven is False
    assert receipt.reason == "expected_source_family_not_authorized_by_lens"
    assert receipt.semantic_derivation_causality_proven is False


def test_representative_cases_reach_kernel_with_bound_receipts() -> None:
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
            assessed_revision=REVISION,
            falsifier=CaseFalsifier(case),
            verifier=CaseVerifier(),
        )
        assert result.material_execution_attempted is True
        assert result.kernel_result is not None and result.kernel_result.proven is True
        assert result.falsification_receipt is not None
        assert result.verification_receipt is not None
        assert proposal.evidence == original_evidence
        assert proposal.authority_ref == original_authority

    assert len(kernel.calls) == 4
