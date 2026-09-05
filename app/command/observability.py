from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.command.event_store import CommandEventStore
from app.command.events import CommandEvent, Freshness


@dataclass(frozen=True)
class ObservabilitySnapshot:
    status: str
    event_count: int | None
    run_ids: tuple[str, ...]
    project_ids: tuple[str, ...]
    ocs_ids: tuple[str, ...]
    requests: tuple[dict[str, Any], ...]
    decisions: tuple[dict[str, Any], ...]
    events: tuple[dict[str, Any], ...]
    receipts: tuple[dict[str, Any], ...]
    errors: tuple[dict[str, Any], ...]
    latency_ms: dict[str, float | None]
    health: str
    freshness: Freshness
    correlation_ids: tuple[str, ...]
    causation_ids: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "event_count": self.event_count,
            "run_ids": list(self.run_ids),
            "project_ids": list(self.project_ids),
            "ocs_ids": list(self.ocs_ids),
            "requests": list(self.requests),
            "decisions": list(self.decisions),
            "events": list(self.events),
            "receipts": list(self.receipts),
            "errors": list(self.errors),
            "latency_ms": self.latency_ms,
            "health": self.health,
            "freshness": self.freshness.value,
            "correlation_ids": list(self.correlation_ids),
            "causation_ids": list(self.causation_ids),
        }


class CommandObservability:
    def __init__(self, database_path: str | Path) -> None:
        self._database_path = database_path

    def snapshot(self) -> dict[str, Any]:
        events = CommandEventStore(self._database_path).read_all()
        if not events:
            return ObservabilitySnapshot(
                status="no_data",
                event_count=None,
                run_ids=(),
                project_ids=(),
                ocs_ids=(),
                requests=(),
                decisions=(),
                events=(),
                receipts=(),
                errors=(),
                latency_ms={"min": None, "max": None, "avg": None},
                health="unknown",
                freshness=Freshness.UNKNOWN,
                correlation_ids=(),
                causation_ids=(),
            ).as_dict()

        event_views = tuple(self._view(event) for event in events)
        requests = tuple(view for view in event_views if self._kind(view) == "request")
        decisions = tuple(view for view in event_views if self._kind(view) == "decision")
        receipts = tuple(view for view in event_views if self._kind(view) == "receipt")
        errors = tuple(view for view in event_views if self._kind(view) == "error")
        latencies = [
            float(event.payload["latency_ms"])
            for event in events
            if isinstance(event.payload.get("latency_ms"), (int, float))
        ]
        health = "degraded" if errors else "observed_no_error_event"
        return ObservabilitySnapshot(
            status="observed",
            event_count=len(events),
            run_ids=self._unique(event.run_id for event in events),
            project_ids=self._unique(event.project_id for event in events),
            ocs_ids=self._unique(event.ocs_id for event in events),
            requests=requests,
            decisions=decisions,
            events=event_views,
            receipts=receipts,
            errors=errors,
            latency_ms=self._latency(latencies),
            health=health,
            freshness=self._freshness(events),
            correlation_ids=self._unique(event.correlation_id for event in events),
            causation_ids=self._unique(event.causation_id for event in events),
        ).as_dict()

    @staticmethod
    def _view(event: CommandEvent) -> dict[str, Any]:
        return {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "occurred_at": event.occurred_at_utc(),
            "run_id": event.run_id,
            "project_id": event.project_id,
            "ocs_id": event.ocs_id,
            "correlation_id": event.correlation_id,
            "causation_id": event.causation_id,
            "freshness": event.freshness.value,
            "source": event.source,
            "source_version": event.source_version,
            "evidence_refs": list(event.evidence_refs),
            "payload": event.payload,
        }

    @staticmethod
    def _kind(view: dict[str, Any]) -> str:
        event_type = str(view["event_type"]).casefold()
        payload = view["payload"]
        if isinstance(payload, dict):
            explicit = payload.get("observability_kind")
            if explicit in {"request", "decision", "receipt", "error"}:
                return str(explicit)
        for kind in ("request", "decision", "receipt", "error"):
            if kind in event_type:
                return kind
        return "event"

    @staticmethod
    def _unique(values: Any) -> tuple[str, ...]:
        return tuple(dict.fromkeys(value for value in values if isinstance(value, str) and value))

    @staticmethod
    def _latency(values: list[float]) -> dict[str, float | None]:
        if not values:
            return {"min": None, "max": None, "avg": None}
        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
        }

    @staticmethod
    def _freshness(events: list[CommandEvent]) -> Freshness:
        values = {event.freshness for event in events}
        if Freshness.STALE in values:
            return Freshness.STALE
        if Freshness.UNKNOWN in values:
            return Freshness.UNKNOWN
        if values == {Freshness.LIVE}:
            return Freshness.LIVE
        return Freshness.RECENT
