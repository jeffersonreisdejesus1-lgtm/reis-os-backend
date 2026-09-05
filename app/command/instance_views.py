from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from app.ocs_instances.contracts import (
    BindingMaturity,
    InstanceBinding,
    InstanceBindingError,
    InstanceStatus,
)

DERIVATION_VERSION = "ib6-v2"
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
    recovery_only: bool = False

    def digest(self) -> str:
        value = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class PageCursor:
    organization_id: str
    filter_hash: str
    snapshot_at: float
    last_created_at: float | None = None
    last_binding_id: str | None = None


class CommandInstanceViews:
    """Organization-scoped, non-mutating projection over the instance registry."""

    def __init__(self, database_path: str | Path) -> None:
        self._path = Path(database_path)

    def list_instances(
        self,
        *,
        organization_id: str,
        filters: InstanceFilter,
        cursor: str | None,
        limit: int,
        now: float | None = None,
    ) -> dict[str, Any]:
        self._validate_scope(organization_id, filters)
        clock = datetime.now(UTC).timestamp() if now is None else now
        page = self._decode_cursor(
            cursor,
            organization_id=organization_id,
            filter_hash=filters.digest(),
            clock=clock,
        )
        health = self._source_health()
        if health != "available":
            return self._empty_page(health)
        all_items = self._filtered_items(
            organization_id=organization_id,
            filters=filters,
            snapshot_at=page.snapshot_at,
            clock=clock,
            health=health,
        )
        candidates = [
            item
            for item in all_items
            if page.last_created_at is None
            or float(item["created_at"]) < page.last_created_at
            or (
                float(item["created_at"]) == page.last_created_at
                and str(item["binding_id"]) > str(page.last_binding_id)
            )
        ]
        selected = candidates[:limit]
        next_cursor = None
        if len(candidates) > limit and selected:
            last = selected[-1]
            next_cursor = self._encode_cursor(
                PageCursor(
                    organization_id=organization_id,
                    filter_hash=filters.digest(),
                    snapshot_at=page.snapshot_at,
                    last_created_at=float(last["created_at"]),
                    last_binding_id=str(last["binding_id"]),
                )
            )
        return {
            "items": selected,
            "count": len(selected),
            "total": len(all_items),
            "next_cursor": next_cursor,
            "snapshot": self._snapshot(
                selected,
                total=len(all_items),
                snapshot_at=page.snapshot_at,
                health=health,
            ),
            "source": self._source(health),
        }

    def get(
        self,
        binding_id: str,
        *,
        organization_id: str,
        now: float | None = None,
    ) -> dict[str, Any]:
        binding = self._get_scoped(binding_id, organization_id)
        result = self._project(binding, clock=now, health=self._source_health())
        result["journal"] = self._journal(binding_id, organization_id)
        result["lineage"] = self.lineage(
            binding_id, organization_id=organization_id, now=now
        )
        return result

    def lineage(
        self,
        binding_id: str,
        *,
        organization_id: str,
        now: float | None = None,
    ) -> dict[str, Any]:
        target = self._get_scoped(binding_id, organization_id)
        rows = self._read(
            """
            SELECT * FROM ocs_instance_bindings
            WHERE organization_id=? AND mission_id=? AND ocs_id=?
            ORDER BY generation ASC
            """,
            (organization_id, target.mission_id, target.ocs_id),
        )
        health = self._source_health()
        items = [
            self._project(self._row(row), clock=now, health=health) for row in rows
        ]
        return {
            "run_id": target.run_id,
            "ocs_id": target.ocs_id,
            "current_generation": max(
                (item["generation"] for item in items), default=None
            ),
            "generations": items,
            "source": self._source(health),
        }

    def comparison(self, binding_id: str, *, organization_id: str) -> dict[str, Any]:
        current = self._get_scoped(binding_id, organization_id)
        predecessor = self._predecessor(current)
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
        proof = self._recovery_proof(current, predecessor)
        return {
            "binding_id": binding_id,
            "predecessor_binding_id": current.predecessor_binding_id,
            "comparisons": comparisons,
            "recovery_proof": proof,
            "claim_state": "verified" if proof["complete"] else "observed",
            "verified": proof["complete"],
            "evidence_refs": self._evidence_refs(current),
            "boundary": "verified_is_not_assured",
            "source": self._source(self._source_health()),
        }

    def recovery_center(
        self,
        *,
        organization_id: str,
        filters: InstanceFilter,
        cursor: str | None,
        limit: int,
        now: float | None = None,
    ) -> dict[str, Any]:
        result = self.list_instances(
            organization_id=organization_id,
            filters=replace(filters, recovery_only=True),
            cursor=cursor,
            limit=limit,
            now=now,
        )
        result["epistemic_boundary"] = {
            "requested_is_executed": False,
            "executed_is_verified": False,
            "verified_is_assured": False,
            "unknown_is_zero": False,
            "no_data_is_healthy": False,
        }
        return result

    def journal_feed(
        self,
        *,
        organization_id: str,
        cursor: int,
        limit: int,
        now: float | None = None,
    ) -> dict[str, Any]:
        if cursor < 0:
            raise ValueError("command_instance_cursor_invalid")
        health = self._source_health()
        if health != "available":
            return {
                "events": [],
                "next_cursor": cursor,
                "freshness": ViewFreshness.UNKNOWN.value,
                "source": self._source(health),
            }
        count = self._read(
            """
            SELECT COUNT(*) AS count FROM ocs_instance_journal j
            JOIN ocs_instance_bindings b ON b.binding_id=j.binding_id
            WHERE b.organization_id=?
            """,
            (organization_id,),
        )
        total = int(count[0]["count"])
        if cursor > total:
            raise ValueError("command_instance_cursor_ahead")
        rows = self._read(
            """
            SELECT j.* FROM ocs_instance_journal j
            JOIN ocs_instance_bindings b ON b.binding_id=j.binding_id
            WHERE b.organization_id=?
            ORDER BY j.position ASC LIMIT ? OFFSET ?
            """,
            (organization_id, limit, cursor),
        )
        events = [self._journal_row(row) for row in rows]
        clock = datetime.now(UTC).timestamp() if now is None else now
        freshness_values = {
            self._freshness(float(event["occurred_at"]), clock=clock, health=health)
            for event in events
        }
        freshness = ViewFreshness.UNKNOWN
        if ViewFreshness.STALE in freshness_values:
            freshness = ViewFreshness.STALE
        elif freshness_values == {ViewFreshness.CURRENT}:
            freshness = ViewFreshness.CURRENT
        return {
            "events": events,
            "next_cursor": cursor + len(events),
            "freshness": freshness.value,
            "batch_availability": "available",
            "source": self._source(health),
        }

    def _filtered_items(
        self,
        *,
        organization_id: str,
        filters: InstanceFilter,
        snapshot_at: float,
        clock: float,
        health: str,
    ) -> list[dict[str, Any]]:
        clauses = ["organization_id=?", "created_at<=?"]
        values: list[Any] = [organization_id, snapshot_at]
        for column, value in (
            ("mission_id", filters.mission_id),
            ("ocs_id", filters.ocs_id),
            ("status", filters.canonical_status),
        ):
            if value is not None:
                clauses.append(f"{column}=?")
                values.append(value)
        rows = self._read(
            "SELECT * FROM ocs_instance_bindings WHERE "
            + " AND ".join(clauses)
            + " ORDER BY created_at DESC, binding_id ASC",
            tuple(values),
        )
        items = [
            self._project(self._row(row), clock=clock, health=health) for row in rows
        ]
        if filters.operational_phase is not None:
            items = [
                item
                for item in items
                if filters.operational_phase in item["operational_phases"]
            ]
        if filters.recovery_only:
            attention = {
                InstanceStatus.HOLD.value,
                InstanceStatus.REVOKED.value,
                InstanceStatus.REPLACED.value,
            }
            items = [
                item
                for item in items
                if item["canonical_status"] in attention
                or OperationalPhase.REPLACEMENT_PENDING.value
                in item["operational_phases"]
                or OperationalPhase.RECOVERED.value in item["operational_phases"]
                or item["freshness"] != ViewFreshness.CURRENT.value
            ]
        return items

    def _project(
        self, binding: InstanceBinding, *, clock: float | None, health: str
    ) -> dict[str, Any]:
        effective_clock = datetime.now(UTC).timestamp() if clock is None else clock
        phases = self._phases(binding)
        refs = self._evidence_refs(binding)
        return {
            **asdict(binding),
            "maturity": binding.maturity.value,
            "canonical_status": binding.status.value,
            "status": binding.status.value,
            "operational_phases": [phase.value for phase in phases],
            "phase_derivations": [
                {
                    "phase": phase.value,
                    "basis": self._phase_basis(phase),
                    "source_refs": refs,
                    "derived_at": datetime.now(UTC).isoformat(),
                    "derivation_version": DERIVATION_VERSION,
                }
                for phase in phases
            ],
            "freshness": self._freshness(
                binding.updated_at, clock=effective_clock, health=health
            ).value,
            "source_version": str(binding.version),
            "evidence_refs": refs,
            "fencing": self._fencing(binding),
            "epistemic_state": (
                "verified"
                if OperationalPhase.RECOVERED in phases
                else "requested"
                if binding.status in {InstanceStatus.PREPARED, InstanceStatus.PERSISTED}
                else "executed"
                if binding.status in {InstanceStatus.BOUND, InstanceStatus.ACTIVE}
                else "observed"
            ),
        }

    def _phases(self, binding: InstanceBinding) -> tuple[OperationalPhase, ...]:
        phases: list[OperationalPhase] = []
        events = {row["event_type"] for row in self._journal_rows(binding.binding_id)}
        if (
            binding.status is InstanceStatus.PERSISTED
            and binding.platform_instance_id is None
        ):
            phases.append(OperationalPhase.AWAITING_PLATFORM_INSTANCE)
        if "OCS_BOOTSTRAP_ACKNOWLEDGED" in events:
            phases.append(OperationalPhase.BOOTSTRAP_ACKNOWLEDGED)
        saga = self._replacement_saga(binding.binding_id)
        if saga is not None and saga["state"] != "LEASE_FINALIZED":
            phases.append(OperationalPhase.REPLACEMENT_PENDING)
        if self._recovery_proof(binding, self._predecessor(binding))["complete"]:
            phases.append(OperationalPhase.RECOVERED)
        return tuple(phases)

    def _fencing(self, binding: InstanceBinding) -> dict[str, Any]:
        rows = self._read(
            """
            SELECT generation,status FROM ocs_instance_bindings
            WHERE organization_id=? AND mission_id=? AND ocs_id=?
            """,
            (binding.organization_id, binding.mission_id, binding.ocs_id),
        )
        maximum = max((int(row["generation"]) for row in rows), default=None)
        active = sum(row["status"] == InstanceStatus.ACTIVE.value for row in rows)
        nonterminal = {
            InstanceStatus.PREPARED.value,
            InstanceStatus.PERSISTED.value,
            InstanceStatus.BOUND.value,
            InstanceStatus.ACTIVE.value,
            InstanceStatus.CHECKPOINTED.value,
        }
        nonterminal_count = sum(row["status"] in nonterminal for row in rows)
        worker_states = {
            InstanceStatus.BOUND.value,
            InstanceStatus.ACTIVE.value,
            InstanceStatus.CHECKPOINTED.value,
        }
        worker_rows = [
            row
            for row in rows
            if row["status"] in worker_states
            and self._generation_has_platform(binding, int(row["generation"]))
        ]
        pending = self._lineage_has_pending_replacement(binding)
        ambiguous = (
            maximum is None
            or active > 1
            or nonterminal_count > 1
            or len(worker_rows) != 1
            or pending
        )
        worker_generation = None if ambiguous else int(worker_rows[0]["generation"])
        is_current_worker: bool | None = None
        if worker_generation is not None:
            is_current_worker = binding.generation == worker_generation
        return {
            "generation": binding.generation,
            "latest_registry_generation": maximum,
            "current_worker_generation": worker_generation,
            "active_generation_count": active,
            "nonterminal_generation_count": nonterminal_count,
            "platform_instance_id": binding.platform_instance_id,
            "is_current_worker": is_current_worker,
            "ambiguous": ambiguous,
            "basis": (
                "worker requires one nonterminal bound generation, platform receipt, "
                "and no pending replacement"
            ),
            "evidence_refs": [
                f"lineage:{binding.run_id}",
                f"binding:{binding.binding_id}",
            ],
        }

    def _generation_has_platform(
        self, binding: InstanceBinding, generation: int
    ) -> bool:
        rows = self._read(
            """
            SELECT platform_instance_id FROM ocs_instance_bindings
            WHERE organization_id=? AND mission_id=? AND ocs_id=?
              AND generation=?
            """,
            (
                binding.organization_id,
                binding.mission_id,
                binding.ocs_id,
                generation,
            ),
        )
        return bool(rows and rows[0]["platform_instance_id"])

    def _lineage_has_pending_replacement(self, binding: InstanceBinding) -> bool:
        rows = self._read(
            """
            SELECT s.state FROM ocs_action_sagas s
            JOIN ocs_instance_bindings b ON b.binding_id=s.binding_id
            WHERE b.organization_id=? AND b.mission_id=? AND b.ocs_id=?
              AND s.operation='ocs_instance_replacement'
              AND s.state!='LEASE_FINALIZED'
            LIMIT 1
            """,
            (binding.organization_id, binding.mission_id, binding.ocs_id),
        )
        return bool(rows)

    def _recovery_proof(
        self,
        current: InstanceBinding,
        predecessor: InstanceBinding | None,
    ) -> dict[str, Any]:
        saga = (
            None
            if predecessor is None
            else self._replacement_saga(predecessor.binding_id)
        )
        events = {row["event_type"] for row in self._journal_rows(current.binding_id)}
        checks = {
            "predecessor_present": predecessor is not None,
            "generation_contiguous": predecessor is not None
            and current.generation == predecessor.generation + 1,
            "checkpoint_version_contiguous": predecessor is not None
            and current.checkpoint_version == predecessor.checkpoint_version + 1,
            "checkpoint_hash_present": bool(current.checkpoint_hash),
            "hazel_event_hash_present": bool(current.hazel_event_hash),
            "identity_preserved": predecessor is not None
            and all(
                getattr(current, field) == getattr(predecessor, field)
                for field in (
                    "profile_hash",
                    "identity_binding_hash",
                    "authority_ref",
                    "state_namespace",
                    "memory_namespace",
                )
            ),
            "readback_verified_event": "OCS_REPLACEMENT_PERSISTED" in events,
            "replacement_saga_finalized": saga is not None
            and saga["state"] == "LEASE_FINALIZED",
        }
        return {
            "complete": all(checks.values()),
            "checks": checks,
            "basis": "IB5 durable replacement saga plus registry readback commit",
        }

    def _predecessor(self, binding: InstanceBinding) -> InstanceBinding | None:
        if binding.predecessor_binding_id is None:
            return None
        try:
            return self._get_scoped(
                binding.predecessor_binding_id, binding.organization_id
            )
        except InstanceBindingError:
            return None

    def _replacement_saga(self, binding_id: str) -> dict[str, Any] | None:
        rows = self._read(
            """
            SELECT * FROM ocs_action_sagas
            WHERE binding_id=? AND operation='ocs_instance_replacement'
            ORDER BY updated_at DESC LIMIT 1
            """,
            (binding_id,),
        )
        return None if not rows else dict(rows[0])

    def _get_scoped(self, binding_id: str, organization_id: str) -> InstanceBinding:
        rows = self._read(
            """
            SELECT * FROM ocs_instance_bindings
            WHERE binding_id=? AND organization_id=?
            """,
            (binding_id, organization_id),
        )
        if not rows:
            raise InstanceBindingError("instance_binding_not_found")
        return self._row(rows[0])

    def _journal(self, binding_id: str, organization_id: str) -> list[dict[str, Any]]:
        self._get_scoped(binding_id, organization_id)
        return [self._journal_row(row) for row in self._journal_rows(binding_id)]

    def _journal_rows(self, binding_id: str) -> list[sqlite3.Row]:
        return self._read(
            """
            SELECT * FROM ocs_instance_journal
            WHERE binding_id=? ORDER BY position
            """,
            (binding_id,),
        )

    def _source_health(self) -> str:
        if not self._path.exists():
            return "unavailable"
        required = {
            "ocs_instance_bindings": {
                "binding_id",
                "organization_id",
                "mission_id",
                "ocs_id",
                "generation",
                "platform_instance_id",
                "status",
                "created_at",
                "updated_at",
            },
            "ocs_instance_journal": {
                "position",
                "event_id",
                "binding_id",
                "event_type",
                "occurred_at",
            },
            "ocs_action_sagas": {
                "binding_id",
                "operation",
                "state",
                "updated_at",
            },
        }
        try:
            for table, expected_columns in required.items():
                columns = {
                    str(row["name"])
                    for row in self._read(f"PRAGMA table_info({table})", ())
                }
                if not expected_columns.issubset(columns):
                    return "degraded"
        except sqlite3.Error:
            return "degraded"
        return "available"

    def _read(self, query: str, values: tuple[Any, ...]) -> list[sqlite3.Row]:
        if not self._path.exists():
            return []
        uri = f"file:{self._path.resolve()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row
            return list(connection.execute(query, values).fetchall())

    @staticmethod
    def _row(row: sqlite3.Row) -> InstanceBinding:
        return InstanceBinding(
            binding_id=str(row["binding_id"]),
            mission_id=str(row["mission_id"]),
            run_id=str(row["run_id"]),
            organization_id=str(row["organization_id"]),
            ocs_id=str(row["ocs_id"]),
            profile_version=str(row["profile_version"]),
            profile_hash=str(row["profile_hash"]),
            identity_binding_hash=str(row["identity_binding_hash"]),
            request_hash=str(row["request_hash"]),
            maturity=BindingMaturity(str(row["maturity"])),
            host=str(row["host"]),
            capability=str(row["capability"]),
            lease_id=str(row["lease_id"]),
            authority_ref=str(row["authority_ref"]),
            scope=tuple(str(item) for item in json.loads(row["scope_json"])),
            state_namespace=str(row["state_namespace"]),
            memory_namespace=str(row["memory_namespace"]),
            generation=int(row["generation"]),
            platform_instance_id=row["platform_instance_id"],
            challenge_hash=str(row["challenge_hash"]),
            bootstrap_hash=str(row["bootstrap_hash"]),
            status=InstanceStatus(str(row["status"])),
            version=int(row["version"]),
            predecessor_binding_id=row["predecessor_binding_id"],
            checkpoint_version=int(row["checkpoint_version"]),
            checkpoint_hash=row["checkpoint_hash"],
            hazel_event_hash=row["hazel_event_hash"],
            idempotency_key=str(row["idempotency_key"]),
            correlation_id=str(row["correlation_id"]),
            causation_id=row["causation_id"],
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
        )

    @staticmethod
    def _journal_row(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["payload"] = json.loads(str(item.pop("payload_json")))
        item["source_version"] = str(item["binding_version"])
        item["evidence_refs"] = [f"journal-event:{item['event_id']}"]
        return item

    @staticmethod
    def _validate_scope(organization_id: str, filters: InstanceFilter) -> None:
        if not organization_id:
            raise ValueError("command_instance_organization_required")
        if (
            filters.canonical_status is not None
            and filters.canonical_status not in CANONICAL_STATUSES
        ):
            raise ValueError("command_instance_status_invalid")
        valid_phases = {item.value for item in OperationalPhase}
        if (
            filters.operational_phase is not None
            and filters.operational_phase not in valid_phases
        ):
            raise ValueError("command_instance_phase_invalid")

    @staticmethod
    def _phase_basis(phase: OperationalPhase) -> str:
        return {
            OperationalPhase.AWAITING_PLATFORM_INSTANCE: (
                "status=persisted AND platform_instance_id IS NULL"
            ),
            OperationalPhase.BOOTSTRAP_ACKNOWLEDGED: (
                "journal contains OCS_BOOTSTRAP_ACKNOWLEDGED"
            ),
            OperationalPhase.REPLACEMENT_PENDING: (
                "replacement saga exists AND state!=LEASE_FINALIZED"
            ),
            OperationalPhase.RECOVERED: "complete IB5 replacement/readback proof",
        }[phase]

    @staticmethod
    def _freshness(
        updated_at: float, *, clock: float | None, health: str
    ) -> ViewFreshness:
        if health != "available" or clock is None:
            return ViewFreshness.UNKNOWN
        age = clock - updated_at
        if age < 0:
            return ViewFreshness.UNKNOWN
        return ViewFreshness.CURRENT if age <= 300 else ViewFreshness.STALE

    @staticmethod
    def _evidence_refs(binding: InstanceBinding) -> list[str]:
        refs = [f"binding:{binding.binding_id}", f"journal:{binding.binding_id}"]
        if binding.hazel_event_hash is not None:
            refs.append(f"hazel:event:{binding.hazel_event_hash}")
        return refs

    @staticmethod
    def _source(health: str) -> dict[str, str]:
        return {
            "name": "ocs_instance_registry",
            "projection_version": DERIVATION_VERSION,
            "health": health,
            "claim_boundary": "verified_is_not_assured",
        }

    def _empty_page(self, health: str) -> dict[str, Any]:
        return {
            "items": [],
            "count": 0,
            "total": None,
            "next_cursor": None,
            "snapshot": {
                "generated_at": datetime.now(UTC).isoformat(),
                "snapshot_at": None,
                "boundary_kind": "unavailable",
                "content_immutable": False,
                "total": None,
                "freshness": ViewFreshness.UNKNOWN.value,
                "source_health": health,
            },
            "source": self._source(health),
        }

    @staticmethod
    def _snapshot(
        items: list[dict[str, Any]], *, total: int, snapshot_at: float, health: str
    ) -> dict[str, Any]:
        freshness = ViewFreshness.UNKNOWN.value
        values = {item["freshness"] for item in items}
        if ViewFreshness.STALE.value in values:
            freshness = ViewFreshness.STALE.value
        elif values == {ViewFreshness.CURRENT.value}:
            freshness = ViewFreshness.CURRENT.value
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "snapshot_at": snapshot_at,
            "boundary_kind": "membership_created_at",
            "content_immutable": False,
            "total": total,
            "freshness": freshness,
            "source_health": health,
        }

    @staticmethod
    def _encode_cursor(cursor: PageCursor) -> str:
        payload = json.dumps(asdict(cursor), sort_keys=True, separators=(",", ":"))
        return base64.urlsafe_b64encode(payload.encode()).decode()

    @staticmethod
    def _decode_cursor(
        cursor: str | None,
        *,
        organization_id: str,
        filter_hash: str,
        clock: float,
    ) -> PageCursor:
        if cursor is None:
            return PageCursor(organization_id, filter_hash, clock)
        try:
            payload = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
            result = PageCursor(**payload)
        except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("command_instance_cursor_invalid") from exc
        if (
            result.organization_id != organization_id
            or result.filter_hash != filter_hash
            or result.snapshot_at > clock
            or result.last_created_at is None
            or result.last_binding_id is None
        ):
            raise ValueError("command_instance_cursor_scope_mismatch")
        return result


def encode_instance_sse(batch: dict[str, Any]) -> list[str]:
    messages = []
    for event in batch["events"]:
        payload = json.dumps(event, sort_keys=True, separators=(",", ":"))
        messages.append(
            f"id: {event['position']}\n"
            f"event: {event['event_type']}\n"
            f"data: {payload}\n\n"
        )
    control = json.dumps(
        {
            "next_cursor": batch["next_cursor"],
            "freshness": batch["freshness"],
            "fallback": "/v1/command/instances",
            "source": batch["source"],
        },
        sort_keys=True,
    )
    messages.append(f"event: command.instance.cursor\ndata: {control}\n\n")
    return messages
