from __future__ import annotations

from pathlib import Path
from typing import Any

from app.command.event_store import CommandEventStore
from app.command.projections import CommandProjector, ProjectionState


class CommandReadModels:
    def __init__(self, database_path: str | Path) -> None:
        self._database_path = database_path

    def snapshot(self) -> ProjectionState:
        events = CommandEventStore(self._database_path).read_all()
        return CommandProjector().rebuild(events)

    def institution(self) -> dict[str, Any]:
        return self.snapshot().institution

    def operations(self) -> list[dict[str, Any]]:
        return list(self.snapshot().operations.values())

    def gates(self) -> list[dict[str, Any]]:
        return list(self.snapshot().gates.values())

    def events(self) -> list[dict[str, Any]]:
        return self.snapshot().events

    def evidence(self) -> list[dict[str, Any]]:
        return list(self.snapshot().evidence.values())

    def system_health(self) -> dict[str, Any]:
        return self.snapshot().system_health

    def maps(self) -> list[dict[str, Any]]:
        return list(self.snapshot().maps.values())
