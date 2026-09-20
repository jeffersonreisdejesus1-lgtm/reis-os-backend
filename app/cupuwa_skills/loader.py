from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .registry import SkillDescriptor


SkillProcedure = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class LoadedSkill:
    descriptor: SkillDescriptor
    procedure: SkillProcedure


class SkillLoader:
    def __init__(self, procedures: dict[str, SkillProcedure]) -> None:
        self._procedures = dict(procedures)

    def load(self, descriptor: SkillDescriptor) -> LoadedSkill:
        if descriptor.authority_granted != "NONE":
            raise PermissionError("skill_loader_authority_violation")
        procedure = self._procedures.get(descriptor.skill_id)
        if procedure is None:
            raise LookupError("skill_procedure_not_available")
        return LoadedSkill(descriptor=descriptor, procedure=procedure)
