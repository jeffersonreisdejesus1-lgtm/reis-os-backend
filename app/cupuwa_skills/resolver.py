from __future__ import annotations

from dataclasses import dataclass

from .registry import SkillDescriptor, SkillRegistry


@dataclass(frozen=True, slots=True)
class SkillResolution:
    capability: str
    ocs_id: str
    skill: SkillDescriptor


def resolve_skill(
    registry: SkillRegistry,
    *,
    capability: str,
    ocs_id: str,
    authority_ref: str | None,
) -> SkillResolution:
    if not authority_ref:
        raise PermissionError("skill_resolution_requires_authority_reference")
    matches = registry.find(capability, ocs_id)
    if len(matches) != 1:
        raise LookupError("skill_resolution_not_unique")
    return SkillResolution(capability=capability, ocs_id=ocs_id, skill=matches[0])
