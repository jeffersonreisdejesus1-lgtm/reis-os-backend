from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from .contracts import ExecutionInstance, ExecutionReceipt, InstanceRole, InstanceState


class ExecutionPlaneStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        c.row_factory = sqlite3.Row
        return c

    def _init_schema(self) -> None:
        with self._connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS execution_instances(
              instance_id TEXT PRIMARY KEY, mission_id TEXT NOT NULL, ocs_id TEXT NOT NULL,
              host TEXT NOT NULL, provider TEXT NOT NULL, role TEXT NOT NULL, generation INTEGER NOT NULL,
              authority_ref TEXT NOT NULL, state_namespace TEXT NOT NULL, memory_namespace TEXT NOT NULL,
              parent_instance_id TEXT, lease_id TEXT NOT NULL, state TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS execution_instance_lookup
              ON execution_instances(mission_id,ocs_id,host,role,state,generation);
            CREATE TABLE IF NOT EXISTS execution_receipts(
              mission_id TEXT NOT NULL, idempotency_key TEXT NOT NULL, request_hash TEXT NOT NULL,
              receipt_json TEXT NOT NULL, PRIMARY KEY(mission_id,idempotency_key));
            CREATE TABLE IF NOT EXISTS execution_events(
              sequence INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, payload_json TEXT NOT NULL);
            """)

    def save_instance(self, instance: ExecutionInstance) -> None:
        with self._connect() as c:
            c.execute(
                "INSERT INTO execution_instances VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (instance.instance_id, instance.mission_id, instance.ocs_id, instance.host,
                 instance.provider, instance.role.value, instance.generation, instance.authority_ref,
                 instance.state_namespace, instance.memory_namespace, instance.parent_instance_id,
                 instance.lease_id, instance.state.value),
            )
            self._event(c, "INSTANCE_MATERIALIZED", asdict(instance))

    def load_instance(self, instance_id: str) -> ExecutionInstance:
        with self._connect() as c:
            row = c.execute("SELECT * FROM execution_instances WHERE instance_id=?", (instance_id,)).fetchone()
        if row is None:
            raise KeyError(instance_id)
        return ExecutionInstance(
            row["instance_id"], row["mission_id"], row["ocs_id"], row["host"], row["provider"],
            InstanceRole(row["role"]), row["generation"], row["authority_ref"], row["state_namespace"],
            row["memory_namespace"], row["parent_instance_id"], row["lease_id"], InstanceState(row["state"])
        )

    def active(self, mission_id: str, ocs_id: str, host: str, role: InstanceRole) -> ExecutionInstance | None:
        with self._connect() as c:
            row = c.execute(
                "SELECT instance_id FROM execution_instances WHERE mission_id=? AND ocs_id=? AND host=? AND role=? AND state='ACTIVE' ORDER BY generation DESC,rowid DESC LIMIT 1",
                (mission_id, ocs_id, host, role.value),
            ).fetchone()
        return None if row is None else self.load_instance(str(row["instance_id"]))

    def fence(self, instance_id: str) -> None:
        with self._connect() as c:
            cur = c.execute("UPDATE execution_instances SET state='FENCED' WHERE instance_id=? AND state='ACTIVE'", (instance_id,))
            if cur.rowcount != 1:
                raise ValueError("instance_not_active")
            self._event(c, "INSTANCE_FENCED", {"instance_id": instance_id})

    def receipt(self, mission_id: str, key: str) -> tuple[str, ExecutionReceipt] | None:
        with self._connect() as c:
            row = c.execute("SELECT request_hash,receipt_json FROM execution_receipts WHERE mission_id=? AND idempotency_key=?", (mission_id, key)).fetchone()
        if row is None:
            return None
        data = json.loads(row["receipt_json"])
        return str(row["request_hash"]), ExecutionReceipt(**data)

    def save_receipt(self, request_hash: str, receipt: ExecutionReceipt) -> None:
        with self._connect() as c:
            c.execute("BEGIN IMMEDIATE")
            c.execute(
                "INSERT INTO execution_receipts VALUES(?,?,?,?)",
                (receipt.mission_id, receipt.idempotency_key, request_hash, json.dumps(asdict(receipt), sort_keys=True)),
            )
            self._event(c, "EXECUTION_RECEIPT", asdict(receipt))
            c.execute("COMMIT")

    @staticmethod
    def _event(c: sqlite3.Connection, event_type: str, payload: dict[str, object]) -> None:
        c.execute("INSERT INTO execution_events(event_type,payload_json) VALUES(?,?)", (event_type, json.dumps(payload, sort_keys=True)))
