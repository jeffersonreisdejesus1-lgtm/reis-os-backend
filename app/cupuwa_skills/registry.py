from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SkillDescriptor:
    skill_id: str
    version: str
    capabilities: frozenset[str]
    compatible_ocs: frozenset[str]
    status: str = "VALIDATED"
    authority_granted: str = "NONE"

    def __post_init__(self) -> None:
        if not self.skill_id or not self.version:
            raise ValueError("skill_identity_required")
        if self.authority_granted != "NONE":
            raise ValueError("skill_cannot_grant_authority")
        if self.status not in {"CANDIDATE", "VALIDATED", "RETIRED"}:
            raise ValueError("invalid_skill_status")


class SkillRegistry:
    def __init__(self, skills: Iterable[SkillDescriptor] = ()) -> None:
        self._skills = {skill.skill_id: skill for skill in skills}

    def register(self, skill: SkillDescriptor) -> None:
        current = self._skills.get(skill.skill_id)
        if current is not None and current.version != skill.version:
            raise ValueError("skill_version_conflict")
        self._skills[skill.skill_id] = skill

    def find(self, capability: str, ocs_id: str) -> tuple[SkillDescriptor, ...]:
        return tuple(
            skill
            for skill in self._skills.values()
            if skill.status == "VALIDATED"
            and capability in skill.capabilities
            and ocs_id in skill.compatible_ocs
        )
