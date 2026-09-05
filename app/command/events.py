from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class Freshness(StrEnum):
    LIVE = "live"
    RECENT = "recent"
    STALE = "stale"
    UNKNOWN = "unknown"


class EventValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CommandEvent:
    event_id: str
    event_type: str
    schema_version: str
    occurred_at: datetime
    source: str
    source_version: str
    institution_id: str
    ocs_id: str | None
    project_id: str | None
    run_id: str | None
    causation_id: str | None
    correlation_id: str | None
    sequence: int
    idempotency_key: str
    freshness: Freshness
    evidence_refs: tuple[str, ...]
    payload: dict[str, Any]

    def validate(self) -> None:
        required = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "schema_version": self.schema_version,
            "source": self.source,
            "source_version": self.source_version,
            "institution_id": self.institution_id,
            "idempotency_key": self.idempotency_key,
        }
        if any(not value.strip() for value in required.values()):
            raise EventValidationError("command_event_required_field_missing")
        if self.sequence < 1:
            raise EventValidationError("command_event_sequence_invalid")
        if self.occurred_at.tzinfo is None:
            raise EventValidationError(
                "command_event_occurred_at_must_be_timezone_aware"
            )
        if self.source.casefold() in {"unknown", "", "unspecified"}:
            raise EventValidationError("command_event_source_unknown")
        target_ocs = self.payload.get("target_ocs_id")
        if target_ocs is not None and target_ocs != self.ocs_id:
            raise EventValidationError("command_event_cross_ocs_contamination")
        claim_state = self.payload.get("claim_state")
        if claim_state in {"verified", "assured"} and not self.evidence_refs:
            raise EventValidationError("command_event_claim_requires_evidence")

    def occurred_at_utc(self) -> str:
        return self.occurred_at.astimezone(UTC).isoformat()
