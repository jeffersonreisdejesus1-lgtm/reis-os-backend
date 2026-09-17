from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path


class LedgerUnknown(RuntimeError):
    pass


def _default_path() -> Path:
    configured = os.environ.get("GICA_LEDGER_PATH")
    if configured:
        return Path(configured)
    return Path(os.environ.get("TMPDIR", "/tmp")) / "gica-transition-ledger.sqlite"


class DurableGicaLedger:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else _default_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        with self._conn() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS transitions (
                    predecessor TEXT PRIMARY KEY,
                    logical_id TEXT NOT NULL,
                    successor TEXT NOT NULL,
                    generation INTEGER NOT NULL
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS founder (
                    founder_key TEXT PRIMARY KEY,
                    successor TEXT NOT NULL
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS pending_transitions (
                    predecessor TEXT PRIMARY KEY,
                    logical_id TEXT NOT NULL,
                    successor TEXT NOT NULL,
                    generation INTEGER NOT NULL
                )"""
            )

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.isolation_level = "IMMEDIATE"
        return conn

    @staticmethod
    def encode_key(parts: tuple[object, ...]) -> str:
        return json.dumps(parts, sort_keys=True, default=str)

    def get_transition(
        self, predecessor: tuple[object, ...]
    ) -> tuple[str, str, int] | None:
        key = self.encode_key(predecessor)
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT logical_id, successor, generation "
                "FROM transitions WHERE predecessor=?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        logical_id, successor, generation = row
        if not logical_id or not successor:
            raise LedgerUnknown("corrupted_transition_record")
        return logical_id, successor, int(generation)

    def commit_transition(
        self,
        predecessor: tuple[object, ...],
        logical_id: str,
        successor_blob: str,
    ) -> tuple[str, str, int]:
        key = self.encode_key(predecessor)
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT logical_id, successor, generation "
                "FROM transitions WHERE predecessor=?",
                (key,),
            ).fetchone()
            if row is not None:
                return row[0], row[1], int(row[2])
            conn.execute(
                "INSERT INTO transitions(predecessor, logical_id, successor, "
                "generation) "
                "VALUES (?,?,?,?)",
                (key, logical_id, successor_blob, 1),
            )
        return logical_id, successor_blob, 1

    def prepare_transition(
        self,
        predecessor: tuple[object, ...],
        logical_id: str,
        successor_blob: str,
    ) -> tuple[str, str, int]:
        """Durably record intent before commit; repeated calls are idempotent."""
        key = self.encode_key(predecessor)
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT logical_id, successor, generation "
                "FROM pending_transitions WHERE predecessor=?",
                (key,),
            ).fetchone()
            if row is not None:
                return row[0], row[1], int(row[2])
            committed = conn.execute(
                "SELECT logical_id, successor, generation "
                "FROM transitions WHERE predecessor=?",
                (key,),
            ).fetchone()
            if committed is not None:
                return committed[0], committed[1], int(committed[2])
            conn.execute(
                "INSERT INTO pending_transitions("
                "predecessor, logical_id, successor, generation) "
                "VALUES (?,?,?,?)",
                (key, logical_id, successor_blob, 1),
            )
        return logical_id, successor_blob, 1

    def reconcile_transition(
        self, predecessor: tuple[object, ...]
    ) -> tuple[str, str, int] | None:
        """Complete a pending transition atomically, or return the committed one."""
        key = self.encode_key(predecessor)
        with self._lock, self._conn() as conn:
            committed = conn.execute(
                "SELECT logical_id, successor, generation "
                "FROM transitions WHERE predecessor=?",
                (key,),
            ).fetchone()
            if committed is not None:
                conn.execute(
                    "DELETE FROM pending_transitions WHERE predecessor=?", (key,)
                )
                return committed[0], committed[1], int(committed[2])
            pending = conn.execute(
                "SELECT logical_id, successor, generation "
                "FROM pending_transitions WHERE predecessor=?",
                (key,),
            ).fetchone()
            if pending is None:
                return None
            conn.execute(
                "INSERT INTO transitions("
                "predecessor, logical_id, successor, generation) "
                "VALUES (?,?,?,?)",
                (key, pending[0], pending[1], pending[2]),
            )
            conn.execute(
                "DELETE FROM pending_transitions WHERE predecessor=?", (key,)
            )
            return pending[0], pending[1], int(pending[2])

    def get_pending(
        self, predecessor: tuple[object, ...]
    ) -> tuple[str, str, int] | None:
        key = self.encode_key(predecessor)
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT logical_id, successor, generation "
                "FROM pending_transitions WHERE predecessor=?",
                (key,),
            ).fetchone()
        return None if row is None else (row[0], row[1], int(row[2]))

    def get_founder(self, founder_key: tuple[object, ...]) -> str | None:
        key = self.encode_key(founder_key)
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT successor FROM founder WHERE founder_key=?", (key,)
            ).fetchone()
        if row is None:
            return None
        if not row[0]:
            raise LedgerUnknown("corrupted_founder_record")
        return str(row[0])

    def commit_founder(
        self, founder_key: tuple[object, ...], successor_blob: str
    ) -> str:
        key = self.encode_key(founder_key)
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT successor FROM founder WHERE founder_key=?", (key,)
            ).fetchone()
            if row is not None:
                return str(row[0])
            conn.execute(
                "INSERT INTO founder(founder_key, successor) VALUES (?,?)",
                (key, successor_blob),
            )
        return successor_blob


_LEDGER = DurableGicaLedger()


def ledger() -> DurableGicaLedger:
    return _LEDGER


def reset_ledger(path: Path) -> DurableGicaLedger:
    global _LEDGER
    _LEDGER = DurableGicaLedger(path)
    return _LEDGER
