from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from typing import Any

from .executor import SkillReceipt


@dataclass(frozen=True, slots=True)
class DurableSkillReceipt:
    operation_id: str
    mission_id: str
    receipt: SkillReceipt
    payload_fingerprint: str
    receipt_hash: str


class SkillReceiptStore:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS skill_receipts (
                operation_id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                skill_version TEXT NOT NULL,
                authority_ref TEXT NOT NULL,
                status TEXT NOT NULL,
                result_digest TEXT NOT NULL,
                payload_fingerprint TEXT NOT NULL,
                receipt_hash TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def persist(
        self,
        *,
        operation_id: str,
        mission_id: str,
        receipt: SkillReceipt,
        payload: dict[str, Any],
    ) -> DurableSkillReceipt:
        payload_fingerprint = self._digest(payload)
        durable = DurableSkillReceipt(
            operation_id=operation_id,
            mission_id=mission_id,
            receipt=receipt,
            payload_fingerprint=payload_fingerprint,
            receipt_hash=self._receipt_hash(
                operation_id, mission_id, receipt, payload_fingerprint
            ),
        )
        existing = self._read(operation_id)
        if existing is not None:
            if existing != durable:
                raise ValueError("skill_receipt_conflict")
            return existing
        self._connection.execute(
            """
            INSERT INTO skill_receipts (
                operation_id, mission_id, skill_id, skill_version, authority_ref,
                status, result_digest, payload_fingerprint, receipt_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                durable.operation_id,
                durable.mission_id,
                durable.receipt.skill_id,
                durable.receipt.skill_version,
                durable.receipt.authority_ref,
                durable.receipt.status,
                durable.receipt.result_digest,
                durable.payload_fingerprint,
                durable.receipt_hash,
            ),
        )
        self._connection.commit()
        readback = self._read(operation_id)
        if readback != durable:
            raise RuntimeError("skill_receipt_readback_failed")
        return durable

    def recover(self, operation_id: str) -> DurableSkillReceipt:
        recovered = self._read(operation_id)
        if recovered is None:
            raise LookupError("skill_receipt_not_found")
        expected = self._receipt_hash(
            recovered.operation_id,
            recovered.mission_id,
            recovered.receipt,
            recovered.payload_fingerprint,
        )
        if expected != recovered.receipt_hash:
            raise ValueError("skill_receipt_corrupt")
        return recovered

    @staticmethod
    def _digest(value: object) -> str:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    @classmethod
    def _receipt_hash(
        cls,
        operation_id: str,
        mission_id: str,
        receipt: SkillReceipt,
        payload_fingerprint: str,
    ) -> str:
        return cls._digest(
            {
                "operation_id": operation_id,
                "mission_id": mission_id,
                "receipt": asdict(receipt),
                "payload_fingerprint": payload_fingerprint,
            }
        )

    def _read(self, operation_id: str) -> DurableSkillReceipt | None:
        row = self._connection.execute(
            """
            SELECT operation_id, mission_id, skill_id, skill_version,
                   authority_ref, status, result_digest, payload_fingerprint,
                   receipt_hash
            FROM skill_receipts WHERE operation_id = ?
            """,
            (operation_id,),
        ).fetchone()
        if row is None:
            return None
        receipt = SkillReceipt(
            skill_id=row[2],
            skill_version=row[3],
            authority_ref=row[4],
            status=row[5],
            result_digest=row[6],
        )
        return DurableSkillReceipt(
            operation_id=row[0],
            mission_id=row[1],
            receipt=receipt,
            payload_fingerprint=row[7],
            receipt_hash=row[8],
        )
