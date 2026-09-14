from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MissionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CHECKPOINTED = "CHECKPOINTED"
    REPLACEMENT_PENDING = "REPLACEMENT_PENDING"
    RECOVERED = "RECOVERED"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class MissionSnapshot:
    mission_id: str
    organization_id: str
    ocs_id: str
    authority_ref: str
    state_namespace: str
    memory_namespace: str
    generation: int
    instance_id: str
    status: MissionStatus
    checkpoint_version: int
    checkpoint_hash: str | None
    transcript_ref: str | None


@dataclass(frozen=True)
class RepositoryEffectReceipt:
    mission_id: str
    idempotency_key: str
    generation: int
    path: str
    before_hash: str
    after_hash: str
    duplicate_effect: bool
    readback_hash: str
