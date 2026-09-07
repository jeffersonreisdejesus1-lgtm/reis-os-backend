from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


class GovernanceLedger:
    """Append-only governance ledger.

    Bounded SoR for governance records only. It is not a mission, identity or authority SoR.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        c.row_factory = sqlite3.Row
        return c

    def _init_schema(self) -> None:
        with self._connect() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS governance_records(
                    record_type TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    object_ref TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    PRIMARY KEY(record_type, record_id)
                );
                CREATE INDEX IF NOT EXISTS governance_object_idx
                    ON governance_records(object_ref, record_type);
                CREATE TABLE IF NOT EXISTS capability_records(
                    capability_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _payload(record: Any) -> dict[str, Any]:
        if not is_dataclass(record):
            raise TypeError("governance_record_must_be_dataclass")
        return asdict(record)

    @staticmethod
    def _encoded(payload: dict[str, Any]) -> tuple[str, str]:
        import hashlib

        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return encoded, hashlib.sha256(encoded.encode()).hexdigest()

    def append(self, *, record_type: str, record_id: str, object_ref: str, record: Any) -> None:
        payload = self._payload(record)
        encoded, digest = self._encoded(payload)
        with self._connect() as c:
            c.execute("BEGIN IMMEDIATE")
            prior = c.execute(
                "SELECT payload_hash FROM governance_records WHERE record_type=? AND record_id=?",
                (record_type, record_id),
            ).fetchone()
            if prior is not None:
                c.execute("COMMIT")
                if str(prior["payload_hash"]) != digest:
                    raise ValueError("governance_idempotency_conflict")
                return
            c.execute(
                "INSERT INTO governance_records VALUES(?,?,?,?,?)",
                (record_type, record_id, object_ref, encoded, digest),
            )
            c.execute("COMMIT")

    def records(self, *, object_ref: str, record_type: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as c:
            if record_type is None:
                rows = c.execute(
                    "SELECT record_type,record_id,payload_json FROM governance_records WHERE object_ref=? ORDER BY record_type,record_id",
                    (object_ref,),
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT record_type,record_id,payload_json FROM governance_records WHERE object_ref=? AND record_type=? ORDER BY record_id",
                    (object_ref, record_type),
                ).fetchall()
        return [
            {
                "record_type": str(row["record_type"]),
                "record_id": str(row["record_id"]),
                "payload": json.loads(row["payload_json"]),
            }
            for row in rows
        ]

    def upsert_capability(self, capability: Any) -> None:
        payload = self._payload(capability)
        encoded, digest = self._encoded(payload)
        capability_id = str(payload["capability_id"])
        with self._connect() as c:
            c.execute("BEGIN IMMEDIATE")
            prior = c.execute(
                "SELECT payload_hash FROM capability_records WHERE capability_id=?",
                (capability_id,),
            ).fetchone()
            if prior is not None and str(prior["payload_hash"]) == digest:
                c.execute("COMMIT")
                return
            c.execute(
                "INSERT INTO capability_records(capability_id,payload_json,payload_hash) VALUES(?,?,?) "
                "ON CONFLICT(capability_id) DO UPDATE SET payload_json=excluded.payload_json,payload_hash=excluded.payload_hash",
                (capability_id, encoded, digest),
            )
            c.execute("COMMIT")

    def capabilities(self) -> list[dict[str, Any]]:
        with self._connect() as c:
            rows = c.execute("SELECT payload_json FROM capability_records ORDER BY capability_id").fetchall()
        return [json.loads(row["payload_json"]) for row in rows]
