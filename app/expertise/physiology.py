from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.universal_kernel.contracts import ActionProposal, ExecutionResult

from .assurance import (
    FalsificationEvaluator,
    FalsificationReceipt,
    VerificationEvaluator,
    VerificationReceipt,
    validate_falsification_receipt,
    validate_verification_receipt,
)
from .corpus import (
    DEDALA_EXPERT_FRAGMENTS,
    DEDALA_EXPERT_SOURCES,
    validate_seed_corpus,
)
from .derivation import (
    ArchitecturalDerivationCandidate,
    assert_persistence_eligible,
    draft_architectural_derivation,
    record_falsification,
    record_verification,
)
from .registry import RetrievalPlan, build_retrieval_plan
from .retriever import RetrievedExpertEvidence, retrieve_expert_evidence
from .sources import ExpertEvidenceFragment, ExpertSourceRecord

DEDALA_OCS_ID = "DÉDALA"


class KernelExecutionPort(Protocol):
    @property
    def institutional_run(self) -> bool: ...

    def execute(self, proposal: ActionProposal) -> ExecutionResult: ...


@dataclass(frozen=True)
class DedalaPhysiologyOutcome:
    action_id: str
    problem: str
    phases: tuple[str, ...]
    retrieval_plan: RetrievalPlan | None
    evidence: tuple[RetrievedExpertEvidence, ...]
    candidate: ArchitecturalDerivationCandidate | None
    kernel_result: ExecutionResult | None
    material_execution_attempted: bool
    reason: str
    falsification_receipt: FalsificationReceipt | None = None
    verification_receipt: VerificationReceipt | None = None
    identity_effect: str = "NONE"
    authority_effect: str = "NONE"
    canon_effect: str = "NONE"


class DedalaExpertisePhysiology:
    """Identity-bound Dédala path from expert retrieval to kernel execution.

    Expert material can shape a local derivation candidate, but never mutates the
    action proposal's authority or governance evidence. Falsification and verification
    are accepted only as typed, revision/evidence/candidate-bound receipts produced by
    evaluator objects. Boolean callbacks are not an admissible institutional proof.
    """

    def __init__(
        self,
        *,
        kernel: KernelExecutionPort,
        sources: tuple[ExpertSourceRecord, ...] | None = None,
        fragments: tuple[ExpertEvidenceFragment, ...] | None = None,
    ) -> None:
        if (sources is None) != (fragments is None):
            raise ValueError("complete_expertise_corpus_configuration_required")
        if sources is None and fragments is None:
            validate_seed_corpus()
            sources = DEDALA_EXPERT_SOURCES
            fragments = DEDALA_EXPERT_FRAGMENTS

        assert sources is not None
        assert fragments is not None
        self._kernel = kernel
        self._sources = sources
        self._fragments = fragments

    def execute(
        self,
        proposal: ActionProposal,
        *,
        problem: str,
        proposition: str,
        assessed_revision: str,
        falsifier: FalsificationEvaluator,
        verifier: VerificationEvaluator,
    ) -> DedalaPhysiologyOutcome:
        if proposal.ocs != DEDALA_OCS_ID:
            raise ValueError("dedala_expertise_path_requires_dedala_proposal")
        if not self._kernel.institutional_run:
            raise ValueError("institutional_identity_binding_required_for_expertise")
        if not problem.strip():
            raise ValueError("expertise_problem_required")
        if not assessed_revision.strip():
            raise ValueError("assessed_revision_required")
        if not hasattr(falsifier, "evaluate"):
            raise ValueError("typed_falsification_evaluator_required")
        if not hasattr(verifier, "evaluate"):
            raise ValueError("typed_verification_evaluator_required")

        phases: list[str] = [
            "BOOT",
            "LOAD_CONSTITUTION",
            "RECOVER_STATE",
            "BIND_ACTIVE_IDENTITY",
            "LOAD_EXPERTISE_MANIFEST",
            "UNDERSTAND",
            "FORMULATE",
        ]

        plan = build_retrieval_plan(problem)
        phases.extend(("PROBLEM_CLASSIFICATION", "SELECT_EXPERT_LENSES"))
        if not plan.candidate_lenses:
            return self._blocked(
                proposal,
                problem,
                phases,
                plan=plan,
                reason="no_applicable_expert_lens",
            )

        evidence = retrieve_expert_evidence(plan, self._sources, self._fragments)
        phases.append("RETRIEVE_EXPERT_EVIDENCE")
        if not evidence:
            return self._blocked(
                proposal,
                problem,
                phases,
                plan=plan,
                reason="no_applicable_expert_evidence",
            )

        candidate = draft_architectural_derivation(plan, evidence, proposition)
        phases.append("PLAN")

        falsification_receipt = falsifier.evaluate(
            candidate,
            evidence,
            assessed_revision,
        )
        validate_falsification_receipt(
            falsification_receipt,
            candidate,
            evidence,
            assessed_revision,
        )
        candidate = record_falsification(
            candidate,
            survived=falsification_receipt.survived,
        )
        phases.append("FALSIFY")
        if candidate.falsification_status != "FALSIFICATION_SURVIVED":
            return self._blocked(
                proposal,
                problem,
                phases,
                plan=plan,
                evidence=evidence,
                candidate=candidate,
                reason="expertise_falsification_failed",
                falsification_receipt=falsification_receipt,
            )

        verification_receipt = verifier.evaluate(
            candidate,
            evidence,
            assessed_revision,
        )
        validate_verification_receipt(
            verification_receipt,
            candidate,
            evidence,
            assessed_revision,
        )
        candidate = record_verification(
            candidate,
            verified=verification_receipt.verified,
        )
        phases.append("VERIFY")
        if candidate.verification_status != "VERIFIED":
            return self._blocked(
                proposal,
                problem,
                phases,
                plan=plan,
                evidence=evidence,
                candidate=candidate,
                reason="expertise_verification_failed",
                falsification_receipt=falsification_receipt,
                verification_receipt=verification_receipt,
            )

        assert_persistence_eligible(candidate)
        phases.append("DERIVATION_PERSISTENCE_ELIGIBLE")

        original_evidence = proposal.evidence
        original_authority_ref = proposal.authority_ref
        kernel_result = self._kernel.execute(proposal)
        phases.append("KERNEL_GOVERNANCE_AND_EXECUTION")

        if proposal.evidence != original_evidence:
            raise RuntimeError("expertise_must_not_mutate_governance_evidence")
        if proposal.authority_ref != original_authority_ref:
            raise RuntimeError("expertise_must_not_mutate_authority")

        return DedalaPhysiologyOutcome(
            action_id=proposal.action_id,
            problem=problem,
            phases=tuple(phases),
            retrieval_plan=plan,
            evidence=evidence,
            candidate=candidate,
            kernel_result=kernel_result,
            material_execution_attempted=True,
            reason=kernel_result.reason,
            falsification_receipt=falsification_receipt,
            verification_receipt=verification_receipt,
        )

    @staticmethod
    def _blocked(
        proposal: ActionProposal,
        problem: str,
        phases: list[str],
        *,
        plan: RetrievalPlan | None,
        reason: str,
        evidence: tuple[RetrievedExpertEvidence, ...] = (),
        candidate: ArchitecturalDerivationCandidate | None = None,
        falsification_receipt: FalsificationReceipt | None = None,
        verification_receipt: VerificationReceipt | None = None,
    ) -> DedalaPhysiologyOutcome:
        return DedalaPhysiologyOutcome(
            action_id=proposal.action_id,
            problem=problem,
            phases=tuple(phases),
            retrieval_plan=plan,
            evidence=evidence,
            candidate=candidate,
            kernel_result=None,
            material_execution_attempted=False,
            reason=reason,
            falsification_receipt=falsification_receipt,
            verification_receipt=verification_receipt,
        )
