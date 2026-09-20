"""Governed capability-to-skill resolution for CUPUWA."""

from .registry import SkillDescriptor, SkillRegistry
from .resolver import SkillResolution, resolve_skill

__all__ = ["SkillDescriptor", "SkillRegistry", "SkillResolution", "resolve_skill"]
