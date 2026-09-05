from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.command.events import CommandEvent, Freshness


@dataclass(slots=True)
class ProjectionState:
    institution: dict[str, Any] = field(default_factory=dict)
    ocs: dict[str, dict[str, Any]] = field(default_factory=dict)
    operations: dict[str, dict[str, Any]] = field(default_factory=dict)
    gates: dict[str, dict[str, Any]] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    evidence: dict[str, dict[str, Any]] = field(default_factory=dict)
    system_health: dict[str, Any] = field(
        default_factory=lambda: {
            "status": "unknown",
            "freshness": Freshness.UNKNOWN.value,
            "evidence_refs": [],
        }
    )
    maps: dict[str, dict[str, Any]] = field(default_factory=dict)


class CommandProjector:
    def rebuild(self, events: list[CommandEvent]) -> ProjectionState:
        state = ProjectionState()
        for event in events:
            self.apply(state, event)
        return state

    def apply(self, state: ProjectionState, event: CommandEvent) -> None:
        common = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "source": event.source,
            "source_version": event.source_version,
            "freshness": event.freshness.value,
            "evidence_refs": list(event.evidence_refs),
            "occurred_at": event.occurred_at_utc(),
            "correlation_id": event.correlation_id,
            "causation_id": event.causation_id,
        }
        state.events.append({**common, "payload": event.payload})

        kind = event.payload.get("projection")
        data = event.payload.get("data")
        if not isinstance(data, dict):
            data = {}

        if kind == "institution":
            state.institution = {**common, **data}
        elif kind == "ocs":
            if event.ocs_id is None:
                return
            state.ocs[event.ocs_id] = {**common, **data}
        elif kind == "operation":
            key = event.run_id or event.project_id or event.event_id
            state.operations[key] = {**common, **data}
        elif kind == "gate":
            key = str(data.get("gate_id", event.event_id))
            state.gates[key] = {**common, **data}
        elif kind in {"evidence", "receipt"}:
            key = str(data.get("evidence_id", event.event_id))
            state.evidence[key] = {**common, **data}
        elif kind == "system_health":
            status = str(data.get("status", "unknown"))
            if not event.evidence_refs and status != "unknown":
                status = "unknown"
            state.system_health = {**common, **data, "status": status}
        elif kind == "map":
            key = str(data.get("map_id", event.event_id))
            state.maps[key] = {**common, **data}


def canonical_projection(state: ProjectionState) -> dict[str, Any]:
    return {
        "institution": state.institution,
        "ocs": state.ocs,
        "operations": state.operations,
        "gates": state.gates,
        "events": state.events,
        "evidence": state.evidence,
        "system_health": state.system_health,
        "maps": state.maps,
    }
