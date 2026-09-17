from __future__ import annotations

import json
import sqlite3
from hashlib import sha256
from pathlib import Path
from typing import Any

from app.gica.ga7_types import (
    Ga7CaseState,
    Ga7DiscoveryCaseInput,
    Ga7DiscoveryCaseResult,
    Ga7EpistemicClass,
    Ga7ReceiptType,
)


class Ga7LedgerError(RuntimeError):
    pass


class Ga7Ledger:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS ga7_cases (
                    case_key TEXT PRIMARY KEY,
                    identity_hash TEXT NOT NULL,
                    input_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    result_json TEXT
                );
                CREATE TABLE IF NOT EXISTS ga7_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    case_key TEXT NOT NULL,
                    receipt_type TEXT NOT NULL,
                    sequence_no INTEGER NOT NULL,
                    epistemic_class TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ga7_budget (
                    case_key TEXT PRIMARY KEY,
                    counters_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ga7_learning (
                    candidate_id TEXT PRIMARY KEY,
                    case_key TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    authority_impact TEXT NOT NULL
                );
                """
            )

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def bind_case(self, case: Ga7DiscoveryCaseInput) -> None:
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT identity_hash FROM ga7_cases WHERE case_key=?",
                (case.case_key(),),
            ).fetchone()
            if existing:
                if existing["identity_hash"] != case.identity_hash():
                    raise Ga7LedgerError("conflicting_case_identity")
                return
            conn.execute(
                "INSERT INTO ga7_cases(case_key, identity_hash, input_json, "
                "state) VALUES (?,?,?,?)",
                (
                    case.case_key(),
                    case.identity_hash(),
                    case.to_json(),
                    Ga7CaseState.CREATED.value,
                ),
            )

    def load_case(self, case_key: str) -> Ga7DiscoveryCaseInput:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT input_json FROM ga7_cases WHERE case_key=?", (case_key,)
            ).fetchone()
        if row is None:
            raise Ga7LedgerError("case_not_found")
        return Ga7DiscoveryCaseInput.from_json(row["input_json"])

    def set_state(self, case_key: str, state: Ga7CaseState) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE ga7_cases SET state=? WHERE case_key=?", (state.value, case_key)
            )

    def get_state(self, case_key: str) -> Ga7CaseState:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT state FROM ga7_cases WHERE case_key=?", (case_key,)
            ).fetchone()
        if row is None:
            raise Ga7LedgerError("case_not_found")
        return Ga7CaseState(row["state"])

    def next_sequence(self, case_key: str) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(sequence_no), 0) AS seq "
                "FROM ga7_receipts WHERE case_key=?",
                (case_key,),
            ).fetchone()
        return int(row["seq"]) + 1

    def append_receipt(
        self,
        *,
        receipt_id: str,
        case_key: str,
        receipt_type: Ga7ReceiptType,
        epistemic: Ga7EpistemicClass,
        payload: dict[str, Any],
    ) -> str:
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        digest = sha256(blob.encode()).hexdigest()
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT payload_hash FROM ga7_receipts WHERE receipt_id=?",
                (receipt_id,),
            ).fetchone()
            if existing:
                if existing["payload_hash"] != digest:
                    raise Ga7LedgerError("conflicting_receipt")
                return digest
            seq = self.next_sequence(case_key)
            conn.execute(
                "INSERT INTO ga7_receipts(receipt_id, case_key, receipt_type, "  # noqa: E501
                "sequence_no, epistemic_class, payload_hash, payload_json) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    receipt_id,
                    case_key,
                    receipt_type.value,
                    seq,
                    epistemic.value,
                    digest,
                    blob,
                ),
            )
        return digest

    def receipts(self, case_key: str) -> list[sqlite3.Row]:
        with self._conn() as conn:
            return list(
                conn.execute(
                    "SELECT * FROM ga7_receipts WHERE case_key=? ORDER BY sequence_no",
                    (case_key,),
                )
            )

    def finalize(self, result: Ga7DiscoveryCaseResult) -> None:
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT result_json FROM ga7_cases WHERE case_key=?", (result.case_key,)
            ).fetchone()
            if existing and existing["result_json"]:
                if existing["result_json"] != result.to_json():
                    raise Ga7LedgerError("conflicting_result")
                return
            conn.execute(
                "UPDATE ga7_cases SET state=?, result_json=? WHERE case_key=?",
                (result.state.value, result.to_json(), result.case_key),
            )

    def load_result(self, case_key: str) -> Ga7DiscoveryCaseResult | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT result_json FROM ga7_cases WHERE case_key=?", (case_key,)
            ).fetchone()
        if row is None or not row["result_json"]:
            return None
        try:
            return Ga7DiscoveryCaseResult.from_json(row["result_json"])
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            raise Ga7LedgerError("corrupt_ledger_record") from exc

    def put_budget(self, case_key: str, counters: dict[str, int]) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO ga7_budget(case_key, counters_json) "
                "VALUES (?,?)",
                (case_key, json.dumps(counters, sort_keys=True)),
            )

    def get_budget(self, case_key: str) -> dict[str, int]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT counters_json FROM ga7_budget WHERE case_key=?", (case_key,)
            ).fetchone()
        return json.loads(row["counters_json"]) if row else {}

    def put_learning(
        self, candidate_id: str, case_key: str, payload: dict[str, Any]
    ) -> None:
        if not payload.get("evidence_refs"):
            raise Ga7LedgerError("learning_missing_provenance")
        if payload.get("authority_impact", "NONE") != "NONE":
            raise Ga7LedgerError("learning_promotion_denied")
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO ga7_learning(candidate_id, case_key, "  # noqa: E501
                "payload_json, authority_impact) VALUES (?,?,?,?)",
                (candidate_id, case_key, json.dumps(payload, sort_keys=True), "NONE"),
            )

    def learning(self, case_key: str) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM ga7_learning WHERE case_key=?", (case_key,)
            )
            return [json.loads(row["payload_json"]) for row in rows]
