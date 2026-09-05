from __future__ import annotations

import pytest

from app.expertise.physiology import DedalaExpertisePhysiology
from app.expertise.sources import (
    ExpertEvidenceFragment,
    ExpertSourceRecord,
    sha256_text,
)
from app.universal_kernel.contracts import (
    ActionProposal,
    AuthorizationDecision,
    Evidence,
    ExecutionResult,
    RiskLevel,
)


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


def _source_material() -> tuple[
    tuple[ExpertSourceRecord, ...], tuple[ExpertEvidenceFragment, ...]
]:
    content = "Incremental refactoring preserves architecture boundaries."
    source = ExpertSourceRecord(
        source_id="SRC-FOWLER-001",
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
    return DedalaExpertisePhysiology(
        kernel=kernel,
        sources=sources,
        fragments=fragments,
    )


def test_verified_derivation_reaches_kernel_without_authority_expansion() -> None:
    kernel = FakeKernel()
    proposal = _proposal()
    original_evidence = proposal.evidence
    original_authority = proposal.authority_ref

    result = _physiology(kernel).execute(
        proposal,
        problem="architecture refactoring boundary",
        proposition="Use an incremental refactoring boundary.",
        falsifier=lambda candidate, evidence: True,
        verifier=lambda candidate, evidence: True,
    )

    assert result.material_execution_attempted is True
    assert result.kernel_result is not None
    assert result.kernel_result.proven is True
    assert result.authority_effect == "NONE"
    assert result.canon_effect == "NONE"
    assert result.identity_effect == "NONE"
    assert result.candidate is not None
    assert result.candidate.persistence_status == "PERSISTENCE_ELIGIBLE"
    assert proposal.evidence == original_evidence
    assert proposal.authority_ref == original_authority
    assert kernel.calls == [proposal]
    assert result.phases[-1] == "KERNEL_GOVERNANCE_AND_EXECUTION"


def test_default_seeded_corpus_is_used_when_no_fixture_is_supplied() -> None:
    kernel = FakeKernel()
    result = DedalaExpertisePhysiology(kernel=kernel).execute(
        _proposal(),
        problem="distributed consistency failure state",
        proposition="Require stale-writer rejection at the protected state boundary.",
        falsifier=lambda candidate, evidence: True,
        verifier=lambda candidate, evidence: True,
    )

    assert result.material_execution_attempted is True
    assert any(item.source_id.startswith("KLEPPMANN-") for item in result.evidence)
    assert kernel.calls == [_proposal()]


def test_partial_corpus_override_fails_closed() -> None:
    sources, _ = _source_material()
    with pytest.raises(
        ValueError,
        match="complete_expertise_corpus_configuration_required",
    ):
        DedalaExpertisePhysiology(kernel=FakeKernel(), sources=sources)


def test_failed_falsification_blocks_kernel_execution() -> None:
    kernel = FakeKernel()
    result = _physiology(kernel).execute(
        _proposal(),
        problem="architecture refactoring boundary",
        proposition="Candidate proposition.",
        falsifier=lambda candidate, evidence: False,
        verifier=lambda candidate, evidence: True,
    )

    assert result.reason == "expertise_falsification_failed"
    assert result.material_execution_attempted is False
    assert result.kernel_result is None
    assert kernel.calls == []
    assert "VERIFY" not in result.phases


def test_failed_verification_blocks_kernel_execution() -> None:
    kernel = FakeKernel()
    result = _physiology(kernel).execute(
        _proposal(),
        problem="architecture refactoring boundary",
        proposition="Candidate proposition.",
        falsifier=lambda candidate, evidence: True,
        verifier=lambda candidate, evidence: False,
    )

    assert result.reason == "expertise_verification_failed"
    assert result.material_execution_attempted is False
    assert result.kernel_result is None
    assert kernel.calls == []


def test_no_applicable_lens_or_evidence_fails_closed_before_kernel() -> None:
    kernel = FakeKernel()
    result = _physiology(kernel).execute(
        _proposal(),
        problem="unrelated cooking problem",
        proposition="Candidate proposition.",
        falsifier=lambda candidate, evidence: True,
        verifier=lambda candidate, evidence: True,
    )

    assert result.reason == "no_applicable_expert_lens"
    assert result.material_execution_attempted is False
    assert kernel.calls == []


def test_non_dedala_and_non_institutional_runs_are_rejected() -> None:
    with pytest.raises(
        ValueError, match="dedala_expertise_path_requires_dedala_proposal"
    ):
        _physiology(FakeKernel()).execute(
            _proposal(ocs="NÓESIS"),
            problem="architecture refactoring",
            proposition="Candidate proposition.",
            falsifier=lambda candidate, evidence: True,
            verifier=lambda candidate, evidence: True,
        )

    with pytest.raises(
        ValueError, match="institutional_identity_binding_required_for_expertise"
    ):
        _physiology(FakeKernel(institutional_run=False)).execute(
            _proposal(),
            problem="architecture refactoring",
            proposition="Candidate proposition.",
            falsifier=lambda candidate, evidence: True,
            verifier=lambda candidate, evidence: True,
        )


def test_phase_order_places_identity_before_expertise_and_kernel_last() -> None:
    kernel = FakeKernel()
    result = _physiology(kernel).execute(
        _proposal(),
        problem="architecture refactoring boundary",
        proposition="Candidate proposition.",
        falsifier=lambda candidate, evidence: True,
        verifier=lambda candidate, evidence: True,
    )

    assert result.phases.index("BIND_ACTIVE_IDENTITY") < result.phases.index(
        "LOAD_EXPERTISE_MANIFEST"
    )
    assert result.phases.index("RETRIEVE_EXPERT_EVIDENCE") < result.phases.index(
        "FALSIFY"
    )
    assert result.phases.index("FALSIFY") < result.phases.index("VERIFY")
    assert result.phases[-1] == "KERNEL_GOVERNANCE_AND_EXECUTION"
