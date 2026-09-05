from __future__ import annotations

import base64
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from app.ocs_instances.contracts import InstanceBinding, InstanceStatus
from app.ocs_instances.store import InstanceBindingStore

DERIVATION_VERSION = "ib6-v1"
CANONICAL_STATUSES = frozenset(item.value for item in InstanceStatus)


class OperationalPhase(StrEnum):
    AWAITING_PLATFORM_INSTANCE = "awaiting_platform_instance"
    BOOTSTRAP_ACKNOWLEDGED = "bootstrap_acknowledged"
    REPLACEMENT_PENDING = "replacement_pending"
    RECOVERED = "recovered"


class ViewFreshness(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class InstanceFilter:
    mission_id: str | None = None
    ocs_id: str | None = None
    canonical_status: str | None = None
    operational_phase: str | None = None


class CommandInstanceViews:
    """Read-only Command projections over the durable instance registry."""

    def __init__(self, database_path: str | Path) -> None:
        self._path = str(database_path)
        self._store = InstanceBindingStore(database_path)

    def list_instances(
        self,
        *,
        filters: InstanceFilter,
        cursor: str | None,
        limit: int,
        now: float | None = None,
    ) -> dict[str, Any]:
        offset = self._decode_cursor(cursor)
        bindings = self._bindings(filters)
        projected = [self._project(item, now=now) for item in bindings]
        if filters.operational_phase is not None:
            projected = [
                item
                for item in projected
                if filters.operational_phase in item["operational_phases"]
            ]
        selected = projected[offset : offset + limit]
        next_offset = offset + len(selected)
        next_cursor = (
            self._encode_cursor(next_offset) if next_offset < len(projected) else None
        )
        return {
            "items": selected,
            "count": len(selected),
            "next_cursor": next_cursor,
            "snapshot": self._snapshot(projected),
            "source": self._source(),
        }

    def get(self, binding_id: str, *, now: float | None = None) -> dict[str, Any]:
        binding = self._store.get(binding_id)
        result = self._project(binding, now=now)
        result["journal"] = self._journal(binding_id)
        result["lineage"] = self.lineage(binding_id, now=now)
        return result

    def lineage(self, binding_id: str, *, now: float | None = None) -> dict[str, Any]:
        target = self._store.get(binding_id)
        with self._store._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM ocs_instance_bindings
                WHERE organization_id = ? AND mission_id = ? AND ocs_id = ?
                ORDER BY generation ASC
                """,
                (target.organization_id, target.mission_id, target.ocs_id),
            ).fetchall()
        generations = [self._project(self._store._row(row), now=now) for row in rows]
        return {
            "run_id": target.run_id,
            "ocs_id": target.ocs_id,
            "current_generation": max(item["generation"] for item in generations),
            "generations": generations,
            "source": self._source(),
        }

    def comparison(self, binding_id: str) -> dict[str, Any]:
        current = self._store.get(binding_id)
        predecessor = (
            None
            if current.predecessor_binding_id is None
            else self._store.get(current.predecessor_binding_id)
        )
        fields = (
            "profile_hash",
            "identity_binding_hash",
            "authority_ref",
            "state_namespace",
            "memory_namespace",
            "checkpoint_version",
            "checkpoint_hash",
            "hazel_event_hash",
        )
        comparisons = [
            {
                "field": field,
                "predecessor": None
                if predecessor is None
                else getattr(predecessor, field),
                "current": getattr(current, field),
                "equal": None
                if predecessor is None
                else getattr(predecessor, field) == getattr(current, field),
            }
            for field in fields
        ]
        verified = predecessor is not None and all(
            item["equal"]
            for item in comparisons
            if item["field"]
            in {
                "profile_hash",
                "identity_binding_hash",
                "authority_ref",
                "state_namespace",
                "memory_namespace",
            }
        )
        return {
            "binding_id": binding_id,
            "predecessor_binding_id": current.predecessor_binding_id,
            "comparisons": comparisons,
            "claim_state": "verified" if verified else "observed",
            "verified": verified,
            "evidence_refs": self._evidence_refs(current),
            "boundary": "verified_is_not_assured",
            "source": self._source(),
        }

    def recovery_center(
        self,
        *,
        filters: InstanceFilter,
        cursor: str | None,
        limit: int,
        now: float | None = None,
    ) -> dict[str, Any]:
        result = self.list_instances(
            filters=filters, cursor=cursor, limit=limit, now=now
        )
        attention = {
            InstanceStatus.HOLD.value,
            InstanceStatus.REVOKED.value,
            InstanceStatus.REPLACED.value,
        }
        result["items"] = [
            item
            for item in result["items"]
            if item["canonical_status"] in attention
            or OperationalPhase.REPLACEMENT_PENDING.value in item["operational_phases"]
            or item["freshness"] != ViewFreshness.CURRENT.value
        ]
        result["count"] = len(result["items"])
        result["epistemic_boundary"] = {
            "requested_is_executed": False,
            "executed_is_verified": False,
            "verified_is_assured": False,
            "unknown_is_zero": False,
            "no_data_is_healthy": False,
        }
        return result

    def journal_feed(self, *, cursor: int, limit: int) -> dict[str, Any]:
        if cursor < 0:
            raise ValueError("command_instance_cursor_invalid")
        with self._store._connect() as connection:
            total_row = connection.execute(
                "SELECT COUNT(*) AS count FROM ocs_instance_journal"
            ).fetchone()
            total = 0 if total_row is None else int(total_row["count"])
            if cursor > total:
                raise ValueError("command_instance_cursor_ahead")
            rows = connection.execute(
                """
                SELECT * FROM ocs_instance_journal
                ORDER BY position ASC LIMIT ? OFFSET ?
                """,
                (limit, cursor),
            ).fetchall()
        events = [self._journal_row(row) for row in rows]
        return {
            "events": events,
            "next_cursor": cursor + len(events),
            "freshness": self._event_freshness(events),
            "source": self._source(),
        }

    def _bindings(self, filters: InstanceFilter) -> list[InstanceBinding]:
        if (
            filters.canonical_status is not None
            and filters.canonical_status not in CANONICAL_STATUSES
        ):
            raise ValueError("command_instance_status_invalid")
        if filters.operational_phase is not None and filters.operational_phase not in {
            item.value for item in OperationalPhase
        }:
            raise ValueError("command_instance_phase_invalid")
        clauses: list[str] = []
        values: list[str] = []
        for column, value in (
            ("mission_id", filters.mission_id),
            ("ocs_id", filters.ocs_id),
            ("status", filters.canonical_status),
        ):
            if value is not None:
                clauses.append(f"{column} = ?")
                values.append(value)
        where = "" if not clauses else "WHERE " + " AND ".join(clauses)
        with self._store._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM ocs_instance_bindings {where} "
                "ORDER BY updated_at DESC, binding_id ASC",
                tuple(values),
            ).fetchall()
        return [self._store._row(row) for row in rows]

    def _project(
        self, binding: InstanceBinding, *, now: float | None
    ) -> dict[str, Any]:
        phases = self._phases(binding)
        evidence_refs = self._evidence_refs(binding)
        freshness = self._freshness(binding.updated_at, now=now)
        return {
            **asdict(binding),
            "maturity": binding.maturity.value,
            "canonical_status": binding.status.value,
            "status": binding.status.value,
            "operational_phases": [item.value for item in phases],
            "phase_derivations": [
                {
                    "phase": item.value,
                    "basis": self._phase_basis(item),
                    "source_refs": evidence_refs,
                    "derived_at": datetime.now(UTC).isoformat(),
                    "derivation_version": DERIVATION_VERSION,
                }
                for item in phases
            ],
            "freshness": freshness.value,
            "source_version": str(binding.version),
            "evidence_refs": evidence_refs,
            "fencing": {
                "generation": binding.generation,
                "platform_instance_id": binding.platform_instance_id,
                "current": binding.status
                not in {InstanceStatus.REPLACED, InstanceStatus.REVOKED},
                "basis": "canonical_status_and_generation",
            },
            "epistemic_state": self._epistemic_state(binding),
        }

    def _phases(self, binding: InstanceBinding) -> tuple[OperationalPhase, ...]:
        phases: list[OperationalPhase] = []
        if (
            binding.status is InstanceStatus.PERSISTED
            and binding.platform_instance_id is None
        ):
            phases.append(OperationalPhase.AWAITING_PLATFORM_INSTANCE)
        if (
            binding.status
            in {
                InstanceStatus.ACTIVE,
                InstanceStatus.CHECKPOINTED,
                InstanceStatus.CLOSED,
            }
            and binding.platform_instance_id is not None
        ):
            phases.append(OperationalPhase.BOOTSTRAP_ACKNOWLEDGED)
        if self._replacement_is_pending(binding.binding_id):
            phases.append(OperationalPhase.REPLACEMENT_PENDING)
        if (
            binding.predecessor_binding_id is not None
            and binding.checkpoint_version > 0
        ):
            phases.append(OperationalPhase.RECOVERED)
        return tuple(phases)

    def _replacement_is_pending(self, binding_id: str) -> bool:
        with self._store._connect() as connection:
            row = connection.execute(
                """
                SELECT state FROM ocs_action_sagas
                WHERE binding_id = ? AND operation = 'ocs_instance_replacement'
                ORDER BY updated_at DESC LIMIT 1
                """,
                (binding_id,),
            ).fetchone()
        return row is not None and str(row["state"]) != "LEASE_FINALIZED"

    @staticmethod
    def _phase_basis(phase: OperationalPhase) -> str:
        return {
            OperationalPhase.AWAITING_PLATFORM_INSTANCE: (
                "status=persisted AND platform_instance_id IS NULL"
            ),
            OperationalPhase.BOOTSTRAP_ACKNOWLEDGED: (
                "status IN active,checkpointed,closed AND "
                "platform_instance_id IS NOT NULL"
            ),
            OperationalPhase.REPLACEMENT_PENDING: (
                "replacement saga exists AND state!=LEASE_FINALIZED"
            ),
            OperationalPhase.RECOVERED: (
                "predecessor_binding_id IS NOT NULL AND checkpoint_version>0"
            ),
        }[phase]

    @staticmethod
    def _freshness(updated_at: float, *, now: float | None) -> ViewFreshness:
        current = datetime.now(UTC).timestamp() if now is None else now
        age = current - updated_at
        if age < 0:
            return ViewFreshness.UNKNOWN
        return ViewFreshness.CURRENT if age <= 300 else ViewFreshness.STALE

    @staticmethod
    def _epistemic_state(binding: InstanceBinding) -> str:
        if binding.status in {InstanceStatus.PREPARED, InstanceStatus.PERSISTED}:
            return "requested"
        if binding.status in {InstanceStatus.BOUND, InstanceStatus.ACTIVE}:
            return "executed"
        if binding.status is InstanceStatus.CHECKPOINTED:
            return "verified"
        return "observed"

    @staticmethod
    def _evidence_refs(binding: InstanceBinding) -> list[str]:
        refs = [f"binding:{binding.binding_id}", f"journal:{binding.binding_id}"]
        if binding.hazel_event_hash is not None:
            refs.append(f"hazel:event:{binding.hazel_event_hash}")
        return refs

    def _journal(self, binding_id: str) -> list[dict[str, Any]]:
        return [self._journal_row(row) for row in self._store.journal(binding_id)]

    @staticmethod
    def _journal_row(row: Any) -> dict[str, Any]:
        item = dict(row)
        item["payload"] = json.loads(str(item.pop("payload_json")))
        item["source_version"] = str(item["binding_version"])
        item["evidence_refs"] = [f"journal-event:{item['event_id']}"]
        return item

    @staticmethod
    def _event_freshness(events: list[dict[str, Any]]) -> str:
        if not events:
            return ViewFreshness.UNKNOWN.value
        return ViewFreshness.CURRENT.value

    @staticmethod
    def _snapshot(items: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "total": len(items),
            "source_version": max(
                (int(item["source_version"]) for item in items), default=0
            ),
            "freshness": (
                ViewFreshness.UNKNOWN.value
                if not items
                else ViewFreshness.STALE.value
                if any(item["freshness"] == ViewFreshness.STALE.value for item in items)
                else ViewFreshness.CURRENT.value
            ),
        }

    @staticmethod
    def _source() -> dict[str, str]:
        return {
            "name": "ocs_instance_registry",
            "projection_version": "ib6-v1",
            "claim_boundary": "verified_is_not_assured",
        }

    @staticmethod
    def _encode_cursor(offset: int) -> str:
        return base64.urlsafe_b64encode(f"ib6:{offset}".encode()).decode()

    @staticmethod
    def _decode_cursor(cursor: str | None) -> int:
        if cursor is None:
            return 0
        try:
            decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
            prefix, raw = decoded.split(":", maxsplit=1)
            offset = int(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("command_instance_cursor_invalid") from exc
        if prefix != "ib6" or offset < 0:
            raise ValueError("command_instance_cursor_invalid")
        return offset


def encode_instance_sse(batch: dict[str, Any]) -> list[str]:
    messages = []
    for event in batch["events"]:
        payload = json.dumps(event, sort_keys=True, separators=(",", ":"))
        message = (
            f"id: {event['position']}\n"
            f"event: {event['event_type']}\n"
            f"data: {payload}\n\n"
        )
        messages.append(message)
    control = json.dumps(
        {
            "next_cursor": batch["next_cursor"],
            "freshness": batch["freshness"],
            "fallback": "/v1/command/instances",
        },
        sort_keys=True,
    )
    messages.append(f"event: command.instance.cursor\ndata: {control}\n\n")
    return messages
