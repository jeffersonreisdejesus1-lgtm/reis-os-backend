from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

from .loader import LoadedSkill


@dataclass(frozen=True, slots=True)
class SkillReceipt:
    skill_id: str
    skill_version: str
    authority_ref: str
    status: str
    result_digest: str


def execute_skill(
    loaded: LoadedSkill,
    *,
    authority_ref: str | None,
    payload: dict[str, Any],
) -> SkillReceipt:
    if not authority_ref:
        raise PermissionError("skill_execution_requires_authority_reference")
    result = loaded.procedure(dict(payload))
    digest = sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return SkillReceipt(
        skill_id=loaded.descriptor.skill_id,
        skill_version=loaded.descriptor.version,
        authority_ref=authority_ref,
        status="SUCCESS",
        result_digest=digest,
    )
