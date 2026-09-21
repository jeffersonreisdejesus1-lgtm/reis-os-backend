"""Governed capability-to-skill resolution for CUPUWA."""

from .acquisition import (
    SkillAcquisitionReceipt,
    SkillCandidate,
    SkillCandidateRegistry,
)
from .coi_bridge import COISkillExecution, execute_coi_skill
from .enforcement import SkillEnforcementReceipt, enforce_required_skills
from .executor import SkillReceipt, execute_skill
from .integration import SkillMissionResult, execute_mission_skill
from .loader import LoadedSkill, SkillLoader
from .registry import SkillDescriptor, SkillRegistry
from .resolver import SkillResolution, resolve_skill

__all__ = [
    "COISkillExecution",
    "LoadedSkill",
    "SkillAcquisitionReceipt",
    "SkillCandidate",
    "SkillCandidateRegistry",
    "SkillDescriptor",
    "SkillEnforcementReceipt",
    "SkillLoader",
    "SkillMissionResult",
    "SkillReceipt",
    "SkillRegistry",
    "SkillResolution",
    "enforce_required_skills",
    "execute_coi_skill",
    "execute_mission_skill",
    "execute_skill",
    "resolve_skill",
]
