"""Governed capability-to-skill resolution for CUPUWA."""

from .coi_bridge import COISkillExecution, execute_coi_skill
from .executor import SkillReceipt, execute_skill
from .integration import SkillMissionResult, execute_mission_skill
from .loader import LoadedSkill, SkillLoader
from .registry import SkillDescriptor, SkillRegistry
from .resolver import SkillResolution, resolve_skill

__all__ = [
    "COISkillExecution",
    "LoadedSkill",
    "SkillDescriptor",
    "SkillLoader",
    "SkillMissionResult",
    "SkillReceipt",
    "SkillRegistry",
    "SkillResolution",
    "execute_coi_skill",
    "execute_mission_skill",
    "execute_skill",
    "resolve_skill",
]
