from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from hashlib import sha256
from typing import Iterable


class LearningStatus(str, Enum):
    CANDIDATE = "candidate"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class EvidenceRef:
    ref: str
    verdict: str


@dataclass(frozen=True)
class Experience:
    experience_id: str
    ocs: str
    category: str
    problem: str
    solution: str
    outcome: str
    evidence: tuple[EvidenceRef, ...]
    seq: int
    status: LearningStatus = LearningStatus.CANDIDATE
    predecessor: str | None = None
    supersedes: str | None = None
    rollback_of: str | None = None

    @property
    def content_hash(self) -> str:
        material = "|".join((self.experience_id, self.ocs, self.category, self.problem, self.solution, self.outcome, self.status.value))
        return sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RetrievalPolicy:
    verified_evidence_weight: float = 2.0
    category_match_weight: float = 2.0
    lexical_overlap_weight: float = 1.0
    recency_weight: float = 0.1


@dataclass(frozen=True)
class LPEProfile:
    ocs: str
    specialty: str
    allowed_categories: tuple[str, ...]
    policy: RetrievalPolicy = RetrievalPolicy()


@dataclass
class LearningState:
    profile: LPEProfile
    records: list[Experience] = field(default_factory=list)
    epoch: int = 0

    @property
    def policy(self) -> RetrievalPolicy:
        return self.profile.policy

    def _head(self) -> str | None:
        return self.records[-1].experience_id if self.records else None

    def append_candidate(self, *, experience_id: str, category: str, problem: str, solution: str, outcome: str, evidence: Iterable[EvidenceRef]) -> Experience:
        if category not in self.profile.allowed_categories:
            raise ValueError("category outside OCS LPE profile")
        if any(r.experience_id == experience_id for r in self.records):
            raise ValueError("duplicate experience_id")
        exp = Experience(
            experience_id=experience_id,
            ocs=self.profile.ocs,
            category=category,
            problem=problem,
            solution=solution,
            outcome=outcome,
            evidence=tuple(evidence),
            seq=len(self.records) + 1,
            predecessor=self._head(),
        )
        self.records.append(exp)
        self.epoch += 1
        return exp

    def verify(self, experience_id: str) -> Experience:
        idx, exp = self._find(experience_id)
        if exp.status is not LearningStatus.CANDIDATE:
            raise ValueError("only candidate learning may be verified")
        if not exp.evidence or not all(e.verdict.lower().startswith("pass") for e in exp.evidence):
            raise ValueError("verification requires passing bound evidence")
        verified = replace(exp, status=LearningStatus.VERIFIED)
        self.records[idx] = verified
        self.epoch += 1
        return verified

    def reject(self, experience_id: str) -> Experience:
        idx, exp = self._find(experience_id)
        if exp.status not in {LearningStatus.CANDIDATE, LearningStatus.VERIFIED}:
            raise ValueError("record cannot be rejected from current state")
        rejected = replace(exp, status=LearningStatus.REJECTED)
        self.records[idx] = rejected
        self.epoch += 1
        return rejected

    def supersede(self, old_id: str, replacement_id: str, *, category: str, problem: str, solution: str, outcome: str, evidence: Iterable[EvidenceRef]) -> Experience:
        idx, old = self._find(old_id)
        if old.status is not LearningStatus.VERIFIED:
            raise ValueError("only verified learning may be superseded")
        replacement = self.append_candidate(
            experience_id=replacement_id,
            category=category,
            problem=problem,
            solution=solution,
            outcome=outcome,
            evidence=evidence,
        )
        verified = self.verify(replacement.experience_id)
        self.records[idx] = replace(old, status=LearningStatus.SUPERSEDED, supersedes=replacement_id)
        self.epoch += 1
        return verified

    def rollback(self, experience_id: str, rollback_id: str, evidence: Iterable[EvidenceRef]) -> Experience:
        idx, exp = self._find(experience_id)
        if exp.status is not LearningStatus.VERIFIED:
            raise ValueError("rollback target must be verified")

        restored_predecessor_id: str | None = None
        if exp.predecessor is not None:
            try:
                predecessor_idx, predecessor = self._find(exp.predecessor)
            except KeyError:
                predecessor = None
            if (
                predecessor is not None
                and predecessor.status is LearningStatus.SUPERSEDED
                and predecessor.supersedes == experience_id
            ):
                self.records[predecessor_idx] = replace(predecessor, status=LearningStatus.VERIFIED)
                restored_predecessor_id = predecessor.experience_id

        self.records[idx] = replace(exp, status=LearningStatus.ROLLED_BACK)
        marker = self.append_candidate(
            experience_id=rollback_id,
            category=exp.category,
            problem=f"rollback:{exp.problem}",
            solution=(
                f"restore predecessor behavior:{restored_predecessor_id}"
                if restored_predecessor_id is not None
                else "restore baseline behavior"
            ),
            outcome="rollback_applied",
            evidence=evidence,
        )
        marker_idx, _ = self._find(marker.experience_id)
        persisted_marker = replace(marker, rollback_of=experience_id)
        self.records[marker_idx] = persisted_marker
        self.epoch += 1
        return persisted_marker

    def retrieve(self, query: str, category: str, k: int = 3) -> list[Experience]:
        if category not in self.profile.allowed_categories:
            raise ValueError("category outside OCS LPE profile")
        if k <= 0:
            return []
        q = _tokens(query)
        verified = [r for r in self.records if r.status is LearningStatus.VERIFIED]
        scored: list[tuple[float, Experience]] = []
        max_seq = max((r.seq for r in verified), default=1)
        for record in verified:
            rt = _tokens(record.problem + " " + record.solution)
            overlap = len(q & rt) / max(1, len(q | rt))
            score = self.policy.verified_evidence_weight
            score += self.policy.category_match_weight if record.category == category else 0.0
            score += self.policy.lexical_overlap_weight * overlap
            score += self.policy.recency_weight * (record.seq / max_seq)
            scored.append((score, record))
        scored.sort(key=lambda x: (x[0], x[1].seq), reverse=True)
        return [r for _, r in scored[:k]]

    def update_external_policy(self, policy: RetrievalPolicy) -> None:
        if min(policy.verified_evidence_weight, policy.category_match_weight, policy.lexical_overlap_weight, policy.recency_weight) < 0:
            raise ValueError("policy weights must be non-negative")
        self.profile = replace(self.profile, policy=policy)
        self.epoch += 1

    def _find(self, experience_id: str) -> tuple[int, Experience]:
        for idx, record in enumerate(self.records):
            if record.experience_id == experience_id:
                return idx, record
        raise KeyError(experience_id)


def _tokens(text: str) -> set[str]:
    return {token.casefold() for token in text.replace("_", " ").replace("-", " ").split() if token}


# LPE invariants inherited from Sofia:
# LEARNING != AUTHORITY
# MEMORY_UPDATE != PARAMETER_UPDATE
# PARAMETRIC_CHANGE != CONSTITUTION_CHANGE
# UNVERIFIED_LEARNING != ACTIVE_LEARNED_POLICY
# FAILED_EVOLUTION -> ROLLBACK
# Rollback semantics: deactivate bad learning, reactivate its superseded predecessor when present,
# otherwise return to baseline behavior; always preserve rollback provenance in EXPERIENCE_STORE.
# OCS_LOCAL_EXPERIENCE_ONLY = TRUE
