from __future__ import annotations

import pytest
from typing import TypedDict

from app.cupuwa_skills.acquisition import SkillCandidateRegistry
from app.cupuwa_skills.registry import SkillRegistry


class CandidateArgs(TypedDict):
    skill_id: str
    version: str
    capability: str
    procedure: str
    proposed_by: str
    evidence: tuple[str, ...]


def test_missing_skill_becomes_candidate_not_executable() -> None:
    candidates = SkillCandidateRegistry()
    candidate, receipt = candidates.propose(
        skill_id="missing-skill",
        version="1.0.0",
        capability="new_capability",
        procedure="bounded procedure",
        proposed_by="SOFIA",
        evidence=("test:evidence",),
    )
    assert candidate.status == "CANDIDATE"
    assert receipt.action == "PROPOSE"
    assert SkillRegistry().find("new_capability", "SOFIA") == ()


def test_candidate_requires_independent_validation() -> None:
    candidates = SkillCandidateRegistry()
    candidate, _ = candidates.propose(
        skill_id="candidate-skill",
        version="1.0.0",
        capability="new_capability",
        procedure="bounded procedure",
        proposed_by="SOFIA",
        evidence=("test:evidence",),
    )
    with pytest.raises(PermissionError, match="not_validated"):
        candidates.register(
            SkillRegistry(),
            candidate.candidate_id,
            compatible_ocs=frozenset({"SOFIA"}),
        )


def test_validated_candidate_becomes_discoverable() -> None:
    candidates = SkillCandidateRegistry()
    candidate, _ = candidates.propose(
        skill_id="candidate-skill",
        version="1.0.0",
        capability="new_capability",
        procedure="bounded procedure",
        proposed_by="SOFIA",
        evidence=("test:evidence",),
    )
    candidates.validate(candidate.candidate_id, validation_ref="AGORA:pass:1")
    registry = SkillRegistry()
    receipt = candidates.register(
        registry,
        candidate.candidate_id,
        compatible_ocs=frozenset({"SOFIA"}),
    )
    assert receipt.status == "AVAILABLE"
    assert len(registry.find("new_capability", "SOFIA")) == 1
    assert registry.find("new_capability", "SOFIA")[0].authority_granted == "NONE"


def test_identical_candidate_is_idempotent() -> None:
    candidates = SkillCandidateRegistry()
    kwargs: CandidateArgs = {
        "skill_id": "same",
        "version": "1.0.0",
        "capability": "cap",
        "procedure": "procedure",
        "proposed_by": "SOFIA",
        "evidence": ("evidence",),
    }
    first, _ = candidates.propose(**kwargs)
    second, _ = candidates.propose(**kwargs)
    assert first == second


def test_conflicting_candidate_payload_fails_closed() -> None:
    candidates = SkillCandidateRegistry()
    kwargs: CandidateArgs = {
        "skill_id": "same",
        "version": "1.0.0",
        "capability": "cap",
        "procedure": "procedure",
        "proposed_by": "SOFIA",
        "evidence": ("evidence",),
    }
    candidates.propose(**kwargs)
    with pytest.raises(ValueError, match="candidate_payload_conflict"):
        candidates.propose(**{**kwargs, "evidence": ("different",)})
