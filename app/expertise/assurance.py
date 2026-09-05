from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol

from .derivation import ArchitecturalDerivationCandidate
from .retriever import RetrievedExpertEvidence


def _sha256_json(payload: object) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def candidate_binding(candidate: ArchitecturalDerivationCandidate) -> str:
    return _sha256_json(
        {
            "ocs_id": candidate.ocs_id,
            "problem": candidate.problem,
            "proposition": candidate.proposition,
            "candidate_lenses": list(candidate.candidate_lenses),
            "evidence_refs": list(candidate.evidence_refs),
            "identity_effect": candidate.identity_effect,
            "authority_effect": candidate.authority_effect,
            "canon_effect": candidate.canon_effect,
        }
    )


def evidence_binding(evidence: tuple[RetrievedExpertEvidence, ...]) -> str:
    return _sha256_json(
        [
            {
                "source_id": item.source_id,
                "source_family": item.source_family,
                "fragment_id": item.fragment_id,
                "locator": item.locator,
                "content": item.content,
                "source_class": item.source_class,
                "applicability_score": item.applicability_score,
                "authority_effect": item.authority_effect,
                "canon_effect": item.canon_effect,
            }
            for item in evidence
        ]
    )


@dataclass(frozen=True)
class FalsificationReceipt:
    receipt_id: str
    candidate_binding: str
    evidence_binding: str
    assessed_revision: str
    procedure_id: str
    survived: bool
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class VerificationReceipt:
    receipt_id: str
    candidate_binding: str
    evidence_binding: str
    assessed_revision: str
    procedure_id: str
    verified: bool
    evidence_refs: tuple[str, ...]


class FalsificationEvaluator(Protocol):
    def evaluate(
        self,
        candidate: ArchitecturalDerivationCandidate,
        evidence: tuple[RetrievedExpertEvidence, ...],
        assessed_revision: str,
    ) -> FalsificationReceipt: ...


class VerificationEvaluator(Protocol):
    def evaluate(
        self,
        candidate: ArchitecturalDerivationCandidate,
        evidence: tuple[RetrievedExpertEvidence, ...],
        assessed_revision: str,
    ) -> VerificationReceipt: ...


def validate_falsification_receipt(
    receipt: FalsificationReceipt,
    candidate: ArchitecturalDerivationCandidate,
    evidence: tuple[RetrievedExpertEvidence, ...],
    assessed_revision: str,
) -> None:
    if not isinstance(receipt, FalsificationReceipt):
        raise ValueError("typed_falsification_receipt_required")
    if not receipt.receipt_id.strip() or not receipt.procedure_id.strip():
        raise ValueError("falsification_receipt_incomplete")
    if receipt.assessed_revision != assessed_revision or not assessed_revision.strip():
        raise ValueError("falsification_receipt_revision_mismatch")
    if receipt.candidate_binding != candidate_binding(candidate):
        raise ValueError("falsification_receipt_candidate_mismatch")
    if receipt.evidence_binding != evidence_binding(evidence):
        raise ValueError("falsification_receipt_evidence_mismatch")
    if receipt.evidence_refs != candidate.evidence_refs:
        raise ValueError("falsification_receipt_refs_mismatch")


def validate_verification_receipt(
    receipt: VerificationReceipt,
    candidate: ArchitecturalDerivationCandidate,
    evidence: tuple[RetrievedExpertEvidence, ...],
    assessed_revision: str,
) -> None:
    if not isinstance(receipt, VerificationReceipt):
        raise ValueError("typed_verification_receipt_required")
    if not receipt.receipt_id.strip() or not receipt.procedure_id.strip():
        raise ValueError("verification_receipt_incomplete")
    if receipt.assessed_revision != assessed_revision or not assessed_revision.strip():
        raise ValueError("verification_receipt_revision_mismatch")
    if receipt.candidate_binding != candidate_binding(candidate):
        raise ValueError("verification_receipt_candidate_mismatch")
    if receipt.evidence_binding != evidence_binding(evidence):
        raise ValueError("verification_receipt_evidence_mismatch")
    if receipt.evidence_refs != candidate.evidence_refs:
        raise ValueError("verification_receipt_refs_mismatch")
