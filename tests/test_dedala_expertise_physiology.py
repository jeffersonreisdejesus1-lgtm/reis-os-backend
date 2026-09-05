from __future__ import annotations

import pytest

from app.expertise.assurance import (
    FalsificationReceipt,
    VerificationReceipt,
    candidate_binding,
    evidence_binding,
)
from app.expertise.physiology import DedalaExpertisePhysiology
from app.expertise.sources import ExpertEvidenceFragment, ExpertSourceRecord, sha256_text
from app.universal_kernel.contracts import (
    ActionProposal,
    AuthorizationDecision,
    Evidence,
    ExecutionResult,
    RiskLevel,
)

REVISION = "test-revision-001"


class FakeKernel:
    def __init__(self, *, institutional_run: bool = True) -> None:
        self._institutional_run = institutional_run
        self.calls: list[ActionProposal] = []

    @property
    def institutional_run(self) -> bool:
        return self._institutional_run

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


class BoundFalsifier:
    def __init__(self, survived: bool = True, revision: str = REVISION) -> None:
        self.survived = survived
        self.revision = revision

    def evaluate(self, candidate, evidence, assessed_revision):
        return FalsificationReceipt(
            receipt_id="FALSIFY-001",
            candidate_binding=candidate_binding(candidate),
            evidence_binding=evidence_binding(evidence),
            assessed_revision=self.revision,
            procedure_id="bounded-adversarial-procedure-v1",
            survived=self.survived,
            evidence_refs=candidate.evidence_refs,
        )


class BoundVerifier:
    def __init__(self, verified: bool = True, revision: str = REVISION) -> None:
        self.verified = verified
        self.revision = revision

    def evaluate(self, candidate, evidence, assessed_revision):
        return VerificationReceipt(
            receipt_id="VERIFY-001",
            candidate_binding=candidate_binding(candidate),
            evidence_binding=evidence_binding(evidence),
            assessed_revision=self.revision,
            procedure_id="bounded-verification-procedure-v1",
            verified=self.verified,
            evidence_refs=candidate.evidence_refs,
        )


def _proposal(*, ocs: str = "DÉDALA") -> ActionProposal:
    return ActionProposal(
        action_id="ACT-DEDALA-001",
        actor="DÉDALA",
        ocs=ocs,
        capability="architecture",
        operation="derive_and_execute",
        payload={"target": "runtime-boundary"},
        risk=RiskLevel.MEDIUM,
        evidence=(Evidence(ref="LOCAL-RUNTIME-001", passed=True),),
        authority_ref="AUTH-001",
        trace_id="TRACE-001",
    )


def _source_material() -> tuple[tuple[ExpertSourceRecord, ...], tuple[ExpertEvidenceFragment, ...]]:
    content = "Incremental refactoring preserves architecture boundaries."
    source = ExpertSourceRecord(
        source_id="FOWLER-FIXTURE-001",
        source_family="FOWLER",
        author="external-author",
        work="external-work",
        edition_or_date="bounded-fixture",
        source_type="technical_source",
        locator="fixture:source",
        content_hash=sha256_text("source-provenance"),
        ingestion_version="fixture-v1",
        licensing_access_class="TEST_FIXTURE",
        retrieval_tags=("architecture", "refactoring", "boundary"),
    )
    fragment = ExpertEvidenceFragment(
        source_id=source.source_id,
        fragment_id="FRAG-001",
        content=content,
        locator="fixture:fragment:1",
        content_hash=sha256_text(content),
        retrieval_tags=("architecture", "refactoring"),
    )
    return (source,), (fragment,)


def _physiology(kernel: FakeKernel) -> DedalaExpertisePhysiology:
    sources, fragments = _source_material()
    return DedalaExpertisePhysiology(kernel=kernel, sources=sources, fragments=fragments)


def _execute(physiology, proposal, *, falsifier=None, verifier=None, revision=REVISION):
    return physiology.execute(
        proposal,
        problem="architecture refactoring boundary",
        proposition="Use an incremental refactoring boundary.",
        assessed_revision=revision,
        falsifier=falsifier or BoundFalsifier(),
        verifier=verifier or BoundVerifier(),
    )


def test_verified_derivation_reaches_kernel_without_authority_expansion() -> None:
    kernel = FakeKernel()
    proposal = _proposal()
    original_evidence = proposal.evidence
    original_authority = proposal.authority_ref
    result = _execute(_physiology(kernel), proposal)

    assert result.material_execution_attempted is True
    assert result.kernel_result is not None and result.kernel_result.proven is True
    assert result.candidate is not None
    assert result.candidate.persistence_status == "PERSISTENCE_ELIGIBLE"
    assert result.falsification_receipt is not None
    assert result.verification_receipt is not None
    assert proposal.evidence == original_evidence
    assert proposal.authority_ref == original_authority
    assert kernel.calls == [proposal]


def test_boolean_callbacks_are_not_accepted_as_assurance() -> None:
    with pytest.raises(ValueError, match="typed_falsification_evaluator_required"):
        _physiology(FakeKernel()).execute(
            _proposal(),
            problem="architecture refactoring boundary",
            proposition="candidate",
            assessed_revision=REVISION,
            falsifier=lambda candidate, evidence: True,
            verifier=BoundVerifier(),
        )


def test_wrong_revision_receipts_fail_closed() -> None:
    with pytest.raises(ValueError, match="falsification_receipt_revision_mismatch"):
        _execute(
            _physiology(FakeKernel()),
            _proposal(),
            falsifier=BoundFalsifier(revision="other-revision"),
        )


def test_failed_falsification_and_verification_block_kernel() -> None:
    kernel = FakeKernel()
    result = _execute(_physiology(kernel), _proposal(), falsifier=BoundFalsifier(False))
    assert result.reason == "expertise_falsification_failed"
    assert result.material_execution_attempted is False
    assert kernel.calls == []

    kernel = FakeKernel()
    result = _execute(_physiology(kernel), _proposal(), verifier=BoundVerifier(False))
    assert result.reason == "expertise_verification_failed"
    assert result.material_execution_attempted is False
    assert kernel.calls == []


def test_non_dedala_and_non_institutional_runs_are_rejected() -> None:
    with pytest.raises(ValueError, match="dedala_expertise_path_requires_dedala_proposal"):
        _execute(_physiology(FakeKernel()), _proposal(ocs="NÓESIS"))
    with pytest.raises(ValueError, match="institutional_identity_binding_required_for_expertise"):
        _execute(_physiology(FakeKernel(institutional_run=False)), _proposal())


def test_default_seeded_corpus_uses_typed_receipts() -> None:
    kernel = FakeKernel()
    result = DedalaExpertisePhysiology(kernel=kernel).execute(
        _proposal(),
        problem="distributed consistency failure state",
        proposition="Require stale-writer rejection at the protected state boundary.",
        assessed_revision=REVISION,
        falsifier=BoundFalsifier(),
        verifier=BoundVerifier(),
    )
    assert result.material_execution_attempted is True
    assert any(item.source_family == "KLEPPMANN" for item in result.evidence)


def test_no_applicable_lens_fails_closed_before_assurance_or_kernel() -> None:
    kernel = FakeKernel()
    result = DedalaExpertisePhysiology(kernel=kernel).execute(
        _proposal(),
        problem="unrelated cooking problem",
        proposition="Candidate proposition.",
        assessed_revision=REVISION,
        falsifier=BoundFalsifier(),
        verifier=BoundVerifier(),
    )
    assert result.reason == "no_applicable_expert_lens"
    assert result.material_execution_attempted is False
    assert kernel.calls == []
