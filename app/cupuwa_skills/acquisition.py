from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .registry import SkillDescriptor, SkillRegistry


@dataclass(frozen=True, slots=True)
class SkillCandidate:
    candidate_id: str
    skill_id: str
    version: str
    capability: str
    procedure: str
    proposed_by: str
    evidence: tuple[str, ...]
    fingerprint: str
    status: str = "CANDIDATE"


@dataclass(frozen=True, slots=True)
class SkillAcquisitionReceipt:
    action: str
    candidate_id: str
    status: str
    evidence: tuple[str, ...]


class SkillCandidateRegistry:
    def __init__(self) -> None:
        self._candidates: dict[str, SkillCandidate] = {}
        self._validated: set[str] = set()

    def propose(
        self,
        *,
        skill_id: str,
        version: str,
        capability: str,
        procedure: str,
        proposed_by: str,
        evidence: tuple[str, ...],
    ) -> tuple[SkillCandidate, SkillAcquisitionReceipt]:
        payload: dict[str, Any] = {
            "skill_id": skill_id,
            "version": version,
            "capability": capability,
            "procedure": procedure,
            "proposed_by": proposed_by,
            "evidence": evidence,
        }
        fingerprint = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        candidate_id = (
            f"candidate:{skill_id}:{version}:{capability}:{proposed_by}"
        )
        candidate = SkillCandidate(
            candidate_id=candidate_id,
            skill_id=skill_id,
            version=version,
            capability=capability,
            procedure=procedure,
            proposed_by=proposed_by,
            evidence=evidence,
            fingerprint=fingerprint,
        )
        existing = self._candidates.get(candidate_id)
        if existing is not None and existing != candidate:
            raise ValueError("candidate_payload_conflict")
        self._candidates[candidate_id] = candidate
        return candidate, SkillAcquisitionReceipt(
            action="PROPOSE",
            candidate_id=candidate_id,
            status="CANDIDATE",
            evidence=evidence,
        )

    def validate(
        self, candidate_id: str, *, validation_ref: str
    ) -> SkillAcquisitionReceipt:
        if not validation_ref:
            raise PermissionError("independent_validation_required")
        if candidate_id not in self._candidates:
            raise LookupError("candidate_not_found")
        self._validated.add(candidate_id)
        return SkillAcquisitionReceipt(
            action="VALIDATE",
            candidate_id=candidate_id,
            status="VALIDATED",
            evidence=(validation_ref,),
        )

    def register(
        self,
        registry: SkillRegistry,
        candidate_id: str,
        *,
        compatible_ocs: frozenset[str],
    ) -> SkillAcquisitionReceipt:
        candidate = self._candidates.get(candidate_id)
        if candidate is None:
            raise LookupError("candidate_not_found")
        if candidate_id not in self._validated:
            raise PermissionError("candidate_not_validated")
        registry.register(
            SkillDescriptor(
                skill_id=candidate.skill_id,
                version=candidate.version,
                capabilities=frozenset({candidate.capability}),
                compatible_ocs=compatible_ocs,
                authority_granted="NONE",
            )
        )
        return SkillAcquisitionReceipt(
            action="REGISTER",
            candidate_id=candidate_id,
            status="AVAILABLE",
            evidence=candidate.evidence,
        )
