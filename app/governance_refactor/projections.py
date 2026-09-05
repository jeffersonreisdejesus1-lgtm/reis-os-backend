from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from app.governance_refactor.contracts import SCHEMA_VERSION

ALLOWED_RECORD_TYPES = frozenset(
    {
        "MissionMetricsRecord",
        "GatePerformanceRecord",
        "QualityApplicabilityMatrix",
        "QualityDomainAssessment",
        "QualityEvidenceBundle",
        "PromotionReadinessState",
        "FounderApprovalDecision",
        "RefactorEvent",
        "IntegrationCapabilityRecord",
        "AgentAvailabilityContract",
        "ChatInstitutionalRoutingContract",
        "AuxiliaryAgentEvidenceContract",
    }
)
_REQUIRED_TABLES = frozenset(
    {
        "governance_candidate_records",
        "governance_candidate_events",
        "governance_candidate_scopes",
    }
)
_TYPE_SQL = ",".join("?" for _ in ALLOWED_RECORD_TYPES)
_TYPE_VALUES = tuple(sorted(ALLOWED_RECORD_TYPES))


class GovernanceProjectionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CandidateFilter:
    record_type: str | None = None
    mission_id: str | None = None
    ocs_id: str | None = None

    def validate(self) -> None:
        if (
            self.record_type is not None
            and self.record_type not in ALLOWED_RECORD_TYPES
        ):
            raise GovernanceProjectionError("candidate_record_type_not_allowed")
        if self.mission_id is not None and not self.mission_id.strip():
            raise GovernanceProjectionError("candidate_mission_id_invalid")
        if self.ocs_id is not None and not self.ocs_id.strip():
            raise GovernanceProjectionError("candidate_ocs_id_invalid")


class GovernanceCommandViews:
    """Tenant-scoped, read-only Command projection over governance candidates.

    The scope table is an additive boundary. Legacy records without an explicit
    organization binding are deliberately invisible; tenant ownership is never
    inferred from the Command request.
    """

    def __init__(self, database_path: str | Path) -> None:
        self._path = Path(database_path)

    def list_candidates(
        self,
        *,
        organization_id: str,
        filters: CandidateFilter,
        cursor: int,
        limit: int,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        self._validate_request(organization_id, filters, cursor, limit)
        health = self._health()
        if health != "available":
            return self._empty(health, cursor)
        clauses = [
            "s.organization_id=?",
            "r.position>?",
            f"r.record_type IN ({_TYPE_SQL})",
        ]
        values: list[object] = [organization_id, cursor, *_TYPE_VALUES]
        if filters.record_type is not None:
            clauses.append("r.record_type=?")
            values.append(filters.record_type)
        if filters.mission_id is not None:
            clauses.append("json_extract(r.payload_json, '$.mission_id')=?")
            values.append(filters.mission_id)
        if filters.ocs_id is not None:
            clauses.append("json_extract(r.payload_json, '$.ocs_id')=?")
            values.append(filters.ocs_id)
        values.append(limit + 1)
        rows = self._query(
            f"""
            SELECT r.* FROM governance_candidate_records r
            JOIN governance_candidate_scopes s
              ON s.record_type=r.record_type
             AND s.record_id=r.record_id
             AND s.schema_version=r.schema_version
            WHERE """ + " AND ".join(clauses) + " ORDER BY r.position ASC LIMIT ?",
            tuple(values),
        )
        items = [self._record(row, now=now) for row in rows]
        selected = items[:limit]
        next_cursor = int(selected[-1]["position"]) if len(items) > limit else None
        return {
            "items": selected,
            "count": len(selected),
            "next_cursor": next_cursor,
            "source": self._source(health),
            "epistemic_boundary": self._boundary(),
        }

    def get_candidate(
        self,
        *,
        organization_id: str,
        record_type: str,
        record_id: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        filters = CandidateFilter(record_type=record_type)
        self._validate_request(organization_id, filters, 0, 1)
        if not record_id.strip():
            raise GovernanceProjectionError("candidate_record_id_invalid")
        if self._health() != "available":
            raise GovernanceProjectionError("candidate_projection_unavailable")
        rows = self._query(
            """
            SELECT r.* FROM governance_candidate_records r
            JOIN governance_candidate_scopes s
              ON s.record_type=r.record_type
             AND s.record_id=r.record_id
             AND s.schema_version=r.schema_version
            WHERE s.organization_id=? AND r.record_type=? AND r.record_id=?
              AND r.schema_version=?
            """,
            (organization_id, record_type, record_id, SCHEMA_VERSION),
        )
        if not rows:
            raise GovernanceProjectionError("candidate_record_not_found")
        return self._record(rows[0], now=now)

    def events(
        self,
        *,
        organization_id: str,
        cursor: int,
        limit: int,
    ) -> dict[str, Any]:
        self._validate_request(organization_id, CandidateFilter(), cursor, limit)
        health = self._health()
        if health != "available":
            return self._empty(health, cursor)
        event_sql = f"""
            SELECT e.* FROM governance_candidate_events e
            JOIN governance_candidate_scopes s
              ON s.record_type=e.record_type
             AND s.record_id=e.record_id
             AND s.schema_version=e.schema_version
            WHERE s.organization_id=? AND e.position>?
              AND e.record_type IN ({_TYPE_SQL})
            ORDER BY e.position ASC LIMIT ?
            """
        rows = self._query(
            event_sql,
            (organization_id, cursor, *_TYPE_VALUES, limit + 1),
        )
        items = [self._event(row) for row in rows[:limit]]
        return {
            "items": items,
            "count": len(items),
            "next_cursor": int(items[-1]["position"]) if len(rows) > limit else None,
            "source": self._source(health),
            "epistemic_boundary": self._boundary(),
        }

    def summary(self, *, organization_id: str) -> dict[str, Any]:
        self._validate_request(organization_id, CandidateFilter(), 0, 100)
        health = self._health()
        if health != "available":
            return {
                "counts_by_type": {},
                "total": None,
                "source": self._source(health),
                "epistemic_boundary": self._boundary(),
            }
        rows = self._query(
            f"""
            SELECT r.record_type, COUNT(*) AS count
            FROM governance_candidate_records r
            JOIN governance_candidate_scopes s
              ON s.record_type=r.record_type
             AND s.record_id=r.record_id
             AND s.schema_version=r.schema_version
            WHERE s.organization_id=?
              AND r.record_type IN ({_TYPE_SQL})
            GROUP BY r.record_type
            ORDER BY r.record_type ASC
            """,
            (organization_id, *_TYPE_VALUES),
        )
        counts = {str(row["record_type"]): int(row["count"]) for row in rows}
        return {
            "counts_by_type": counts,
            "total": sum(counts.values()),
            "source": self._source(health),
            "epistemic_boundary": self._boundary(),
        }

    def _record(self, row: sqlite3.Row, *, now: datetime | None) -> dict[str, Any]:
        payload_json = str(row["payload_json"])
        self._verify_hash(payload_json, str(row["payload_hash"]))
        payload = json.loads(payload_json)
        self._verify_evidence_envelope(row, payload)
        observed = self._observed_at(payload, str(row["written_at"]))
        return {
            "position": int(row["position"]),
            "record_type": str(row["record_type"]),
            "record_id": str(row["record_id"]),
            "schema_version": str(row["schema_version"]),
            "payload_hash": str(row["payload_hash"]),
            "payload": payload,
            "source_refs": json.loads(str(row["source_refs_json"])),
            "provenance_refs": json.loads(str(row["provenance_refs_json"])),
            "written_at": str(row["written_at"]),
            "freshness": self._freshness(observed, now),
            "claim_state": "candidate",
        }

    def _event(self, row: sqlite3.Row) -> dict[str, Any]:
        payload_json = str(row["payload_json"])
        self._verify_hash(payload_json, str(row["payload_hash"]))
        self._verify_evidence_envelope(row, json.loads(payload_json))
        return {
            "position": int(row["position"]),
            "event_id": str(row["event_id"]),
            "record_type": str(row["record_type"]),
            "record_id": str(row["record_id"]),
            "event_type": str(row["event_type"]),
            "payload_hash": str(row["payload_hash"]),
            "occurred_at": str(row["occurred_at"]),
        }

    def _health(self) -> str:
        if not self._path.is_file():
            return "unavailable"
        try:
            rows = self._query("SELECT name FROM sqlite_master WHERE type='table'", ())
        except sqlite3.Error:
            return "error"
        names = {str(row["name"]) for row in rows}
        return "available" if _REQUIRED_TABLES.issubset(names) else "incompatible"

    def _query(self, sql: str, values: tuple[object, ...]) -> list[sqlite3.Row]:
        try:
            with sqlite3.connect(self._path) as connection:
                connection.row_factory = sqlite3.Row
                return list(connection.execute(sql, values).fetchall())
        except sqlite3.Error as exc:
            raise GovernanceProjectionError("candidate_projection_read_failed") from exc

    @staticmethod
    def _validate_request(
        organization_id: str, filters: CandidateFilter, cursor: int, limit: int
    ) -> None:
        if not organization_id.strip():
            raise GovernanceProjectionError("candidate_organization_id_invalid")
        if cursor < 0:
            raise GovernanceProjectionError("candidate_cursor_invalid")
        if not 1 <= limit <= 100:
            raise GovernanceProjectionError("candidate_limit_invalid")
        filters.validate()

    @staticmethod
    def _verify_hash(payload_json: str, expected: str) -> None:
        if sha256(payload_json.encode()).hexdigest() != expected:
            raise GovernanceProjectionError("candidate_projection_hash_mismatch")

    @staticmethod
    def _verify_evidence_envelope(
        row: sqlite3.Row, payload: dict[str, Any]
    ) -> None:
        for key, column in (
            ("source_refs", "source_refs_json"),
            ("provenance_refs", "provenance_refs_json"),
        ):
            stored = json.loads(str(row[column]))
            embedded = payload.get(key, [])
            if stored != embedded:
                raise GovernanceProjectionError(
                    "candidate_evidence_envelope_mismatch"
                )

    @staticmethod
    def _observed_at(payload: dict[str, Any], fallback: str) -> datetime | None:
        value = payload.get("observed_at", fallback)
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else None

    @staticmethod
    def _freshness(observed: datetime | None, now: datetime | None) -> str:
        if observed is None:
            return "unknown"
        clock = datetime.now(UTC) if now is None else now
        if clock.tzinfo is None:
            raise GovernanceProjectionError("timezone_aware_timestamp_required")
        age = (clock - observed).total_seconds()
        if age < 0:
            return "unknown"
        return "current" if age <= 300 else "stale"

    @staticmethod
    def _source(health: str) -> dict[str, Any]:
        return {
            "health": health,
            "schema_version": SCHEMA_VERSION if health == "available" else None,
            "truth_role": "governance_candidate_store",
            "duplicates_command_event_truth": False,
        }

    @staticmethod
    def _boundary() -> dict[str, bool]:
        return {
            "candidate_is_authority": False,
            "requested_is_executed": False,
            "executed_is_verified": False,
            "verified_is_assured": False,
            "unknown_is_zero": False,
            "no_data_is_healthy": False,
        }

    def _empty(self, health: str, cursor: int) -> dict[str, Any]:
        return {
            "items": [],
            "count": 0,
            "next_cursor": None,
            "cursor": cursor,
            "source": self._source(health),
            "epistemic_boundary": self._boundary(),
        }
