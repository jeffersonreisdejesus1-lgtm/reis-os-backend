from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .executor import SkillReceipt, execute_skill
from .loader import SkillLoader
from .registry import SkillRegistry
from .resolver import resolve_skill


@dataclass(frozen=True, slots=True)
class SkillMissionResult:
    receipt: SkillReceipt


def execute_mission_skill(
    registry: SkillRegistry,
    loader: SkillLoader,
    *,
    capability: str,
    ocs_id: str,
    authority_ref: str | None,
    payload: dict[str, Any],
) -> SkillMissionResult:
    resolution = resolve_skill(
        registry,
        capability=capability,
        ocs_id=ocs_id,
        authority_ref=authority_ref,
    )
    loaded = loader.load(resolution.skill)
    return SkillMissionResult(
        receipt=execute_skill(
            loaded,
            authority_ref=authority_ref,
            payload=payload,
        )
    )
