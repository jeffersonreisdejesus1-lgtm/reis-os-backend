# ruff: noqa: E501,I001,E701,E702
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import TypedDict, cast
from .contracts import BindingStatus, MissionSnapshot, MissionStatus, RepositoryEffectReceipt

class PendingEffect(TypedDict):
    mission_id: str
    idempotency_key: str
    generation: int
    path: str
    before_hash: str
    after_hash: str
    readback_hash: str
    payload_json: str
    status: str
    requested_hash: str


class MissionRuntimeStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._init_schema()
    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        return connection
    def _init_schema(self) -> None:
        with self._connect() as c:
            c.executescript("""CREATE TABLE IF NOT EXISTS missions(
                mission_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, ocs_id TEXT NOT NULL,
                authority_ref TEXT NOT NULL, state_namespace TEXT NOT NULL, memory_namespace TEXT NOT NULL,
                generation INTEGER NOT NULL, instance_id TEXT NOT NULL, status TEXT NOT NULL,
                checkpoint_version INTEGER NOT NULL, checkpoint_hash TEXT, transcript_ref TEXT,
                binding_status TEXT NOT NULL DEFAULT 'UNKNOWN', binding_evidence TEXT, checkpoint_material_json TEXT);
                CREATE TABLE IF NOT EXISTS effects(
                mission_id TEXT NOT NULL, idempotency_key TEXT NOT NULL, generation INTEGER NOT NULL,
                path TEXT NOT NULL, before_hash TEXT NOT NULL, after_hash TEXT NOT NULL, readback_hash TEXT NOT NULL,
                payload_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'APPLIED', requested_hash TEXT NOT NULL DEFAULT '',
                PRIMARY KEY(mission_id,idempotency_key));
                CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY AUTOINCREMENT, mission_id TEXT NOT NULL,
                event_type TEXT NOT NULL, payload_json TEXT NOT NULL);""")
    def create(self, snapshot: MissionSnapshot) -> None:
        with self._connect() as c:
            c.execute("INSERT INTO missions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (snapshot.mission_id,snapshot.organization_id,snapshot.ocs_id,snapshot.authority_ref,
                 snapshot.state_namespace,snapshot.memory_namespace,snapshot.generation,snapshot.instance_id,
                 snapshot.status.value,snapshot.checkpoint_version,snapshot.checkpoint_hash,snapshot.transcript_ref,
                 snapshot.binding_status.value,snapshot.binding_evidence,snapshot.checkpoint_material_json))
            self._append_event(c,snapshot.mission_id,"MISSION_CREATED",{"generation":snapshot.generation,"instance_id":snapshot.instance_id})
    def save(self, snapshot: MissionSnapshot, event_type: str) -> None:
        with self._connect() as c:
            cur=c.execute("""UPDATE missions SET generation=?,instance_id=?,status=?,checkpoint_version=?,
                checkpoint_hash=?,transcript_ref=?,binding_status=?,binding_evidence=?,checkpoint_material_json=?
                WHERE mission_id=? AND organization_id=? AND ocs_id=? AND authority_ref=?""",
                (snapshot.generation,snapshot.instance_id,snapshot.status.value,snapshot.checkpoint_version,
                 snapshot.checkpoint_hash,snapshot.transcript_ref,snapshot.binding_status.value,snapshot.binding_evidence,
                 snapshot.checkpoint_material_json,snapshot.mission_id,snapshot.organization_id,snapshot.ocs_id,snapshot.authority_ref))
            if cur.rowcount != 1: raise ValueError("mission_identity_or_authority_mismatch")
            self._append_event(c,snapshot.mission_id,event_type,{"generation":snapshot.generation,"instance_id":snapshot.instance_id,"status":snapshot.status.value})
    def load(self, mission_id: str) -> MissionSnapshot:
        with self._connect() as c: row=c.execute("SELECT * FROM missions WHERE mission_id=?",(mission_id,)).fetchone()
        if row is None: raise KeyError(mission_id)
        return MissionSnapshot(row["mission_id"],row["organization_id"],row["ocs_id"],row["authority_ref"],row["state_namespace"],
            row["memory_namespace"],row["generation"],row["instance_id"],MissionStatus(row["status"]),row["checkpoint_version"],
            row["checkpoint_hash"],row["transcript_ref"],BindingStatus(row["binding_status"]),row["binding_evidence"],row["checkpoint_material_json"])
    def claim_effect(self, mission_id: str, idempotency_key: str, *, generation: int, path: str, requested_hash: str) -> tuple[str, str, str] | None:
        with self._connect() as c:
            c.execute("BEGIN IMMEDIATE")
            row=c.execute("SELECT status,path,requested_hash FROM effects WHERE mission_id=? AND idempotency_key=?",(mission_id,idempotency_key)).fetchone()
            if row is not None: c.execute("COMMIT"); return str(row["status"]),str(row["path"]),str(row["requested_hash"])
            c.execute("INSERT INTO effects(mission_id,idempotency_key,generation,path,before_hash,after_hash,readback_hash,payload_json,status,requested_hash) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (mission_id,idempotency_key,generation,path,"","","",json.dumps({"content_hash":requested_hash},sort_keys=True),"PENDING",requested_hash))
            c.execute("COMMIT"); return None
    def effect_claim(self, mission_id: str, key: str) -> tuple[str, str, str]:
        with self._connect() as c:
            row=c.execute("SELECT status,path,requested_hash FROM effects WHERE mission_id=? AND idempotency_key=?",(mission_id,key)).fetchone()
        if row is None: raise KeyError(key)
        return str(row["status"]),str(row["path"]),str(row["requested_hash"])
    def effect(self, mission_id: str, key: str) -> RepositoryEffectReceipt | None:
        with self._connect() as c: row=c.execute("SELECT * FROM effects WHERE mission_id=? AND idempotency_key=? AND status='APPLIED'",(mission_id,key)).fetchone()
        if row is None: return None
        return RepositoryEffectReceipt(row["mission_id"],row["idempotency_key"],row["generation"],row["path"],row["before_hash"],row["after_hash"],False,row["readback_hash"])
    def pending_effects(self, mission_id: str) -> list[PendingEffect]:
        with self._connect() as c: rows=c.execute("SELECT * FROM effects WHERE mission_id=? AND status='PENDING'",(mission_id,)).fetchall()
        return [cast(PendingEffect, dict(r)) for r in rows]
    def apply_effect(self, receipt: RepositoryEffectReceipt, payload: dict[str,str]) -> None:
        with self._connect() as c:
            cur=c.execute("UPDATE effects SET before_hash=?,after_hash=?,readback_hash=?,payload_json=?,status='APPLIED' WHERE mission_id=? AND idempotency_key=? AND status='PENDING'",
                (receipt.before_hash,receipt.after_hash,receipt.readback_hash,json.dumps(payload,sort_keys=True),receipt.mission_id,receipt.idempotency_key))
            if cur.rowcount != 1: raise ValueError("mission_effect_claim_not_pending")
            self._append_event(c,receipt.mission_id,"MATERIAL_EFFECT_APPLIED",{"idempotency_key":receipt.idempotency_key,"path":receipt.path,"after_hash":receipt.after_hash})
    def fail_pending(self, mission_id: str, key: str, reason: str) -> None:
        with self._connect() as c:
            cur=c.execute("UPDATE effects SET status='FAILED',payload_json=? WHERE mission_id=? AND idempotency_key=? AND status='PENDING'",(json.dumps({"reason":reason}),mission_id,key))
            if cur.rowcount != 1: raise ValueError("mission_effect_claim_not_pending")
    def effect_records(self, mission_id: str) -> list[dict[str, str]]:
        with self._connect() as c: rows=c.execute("SELECT idempotency_key,generation,path,before_hash,after_hash,readback_hash,requested_hash FROM effects WHERE mission_id=? AND status='APPLIED' ORDER BY idempotency_key",(mission_id,)).fetchall()
        return [dict(r) for r in rows]
    def checkpoint_material_matches(self, mission_id: str) -> bool:
        row=self.load(mission_id)
        if row.checkpoint_material_json is None: return False
        material=json.loads(row.checkpoint_material_json)
        expected=material.get("effects")
        if not isinstance(expected,list): return False
        current=self.effect_records(mission_id)
        return sorted(current,key=lambda x:x["idempotency_key"]) == sorted(expected,key=lambda x:x["idempotency_key"])
    @staticmethod
    def _append_event(c: sqlite3.Connection, mission_id: str, event_type: str, payload: dict[str, object]) -> None:
        c.execute("INSERT INTO events(mission_id,event_type,payload_json) VALUES(?,?,?)",(mission_id,event_type,json.dumps(payload,sort_keys=True)))
