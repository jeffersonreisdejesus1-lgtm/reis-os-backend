from copy import deepcopy
from threading import RLock
from typing import Dict, Any
from recursive_runtime.contracts.model import ActorState, Checkpoint, Receipt, Lifecycle

class Conflict(RuntimeError): pass
class Stale(RuntimeError): pass
class InvalidCheckpoint(RuntimeError): pass

class StateRepository:
    def __init__(self):
        self._actors: Dict[str, ActorState] = {}
        self._active_by_identity: Dict[str, str] = {}
        self._namespaces = set()
        self._lock = RLock()
    @property
    def lock(self): return self._lock
    def add(self, actor: ActorState, *, active=True):
        with self._lock:
            if actor.state_namespace in self._namespaces: raise Conflict("STATE_NAMESPACE_COLLISION")
            self._actors[actor.actor_id] = deepcopy(actor)
            self._namespaces.add(actor.state_namespace)
            if active: self._active_by_identity[actor.identity_id] = actor.actor_id
    def get(self, actor_id):
        with self._lock: return deepcopy(self._actors[actor_id])
    def mutate(self, actor_id): return self._actors[actor_id]
    def set_active(self, actor_id):
        with self._lock:
            a=self._actors[actor_id]; self._active_by_identity[a.identity_id]=actor_id
    def validate_current(self, actor_id, generation, fencing_epoch):
        with self._lock:
            a=self._actors[actor_id]
            if self._active_by_identity.get(a.identity_id) != actor_id: raise Stale("STALE_PREDECESSOR")
            if a.lifecycle is Lifecycle.FENCED: raise Stale("FENCED")
            if a.generation != generation: raise Stale("STALE_GENERATION")
            if a.fencing_epoch != fencing_epoch: raise Stale("STALE_FENCING")
    def descendants(self, actor_id):
        out=[]; q=list(self._actors[actor_id].children)
        while q:
            x=q.pop(0); out.append(x); q.extend(self._actors[x].children)
        return tuple(out)

class ReceiptRepository:
    def __init__(self): self._data: Dict[str, Receipt] = {}; self._lock=RLock()
    def put(self, r: Receipt):
        with self._lock:
            ex=self._data.get(r.receipt_id)
            if ex is not None and ex != r: raise Conflict("RECEIPT_CONFLICT")
            self._data[r.receipt_id]=deepcopy(r)
    def all(self):
        with self._lock: return tuple(deepcopy(v) for v in self._data.values())

class CheckpointRepository:
    def __init__(self): self._by_actor={}
    def put(self, cp: Checkpoint): self._by_actor.setdefault(cp.actor.actor_id,[]).append(deepcopy(cp))
    def latest(self, actor_id):
        arr=self._by_actor.get(actor_id,[])
        if not arr: raise InvalidCheckpoint("NO_VALID_CHECKPOINT")
        return deepcopy(arr[-1])

class BudgetLedger:
    def __init__(self): self._limits={}; self._reserved={}; self._actual={}; self._lock=RLock()
    def bind(self, ref, provider_id, max_spawns):
        self._limits[ref]=(provider_id,max_spawns); self._reserved[ref]=0; self._actual[ref]=0
    def provider(self, ref): return self._limits[ref][0]
    def reserve_spawn(self, ref):
        with self._lock:
            _, limit=self._limits[ref]
            if self._reserved[ref] >= limit: raise Conflict("BUDGET_EXHAUSTED")
            self._reserved[ref]+=1
    def release_spawn(self, ref):
        with self._lock: self._reserved[ref]=max(0,self._reserved[ref]-1)
    def reconcile_spawn(self, ref):
        with self._lock:
            if self._reserved[ref] <= 0: raise Conflict("NO_RESERVATION")
            self._reserved[ref]-=1; self._actual[ref]+=1
    def snapshot(self, ref):
        with self._lock: return self._reserved[ref], self._actual[ref]

import json
from pathlib import Path

class DurableJournalRepository:
    def __init__(self, path):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True); self._lock = RLock()
        if not self.path.exists(): self.path.write_text("", encoding="utf-8")
    def _load(self):
        out = {}; raw = self.path.read_text(encoding="utf-8")
        for line in raw.splitlines():
            if not line.strip(): continue
            row = json.loads(line); out[row["journal_id"]] = row
        return out
    def put(self, record):
        with self._lock:
            rows = self._load()
            payload = {"journal_id": record.journal_id,"kind": record.kind,"actor_id": record.actor_id,"trace_id": record.trace_id,"generation": record.generation,"fencing_epoch": record.fencing_epoch,"status": record.status,"payload": list(record.payload)}
            existing = rows.get(record.journal_id)
            if existing is not None:
                if existing == payload: return
                raise Conflict("JOURNAL_ID_CONFLICT")
            with self.path.open("a", encoding="utf-8") as f: f.write(json.dumps(payload, sort_keys=True) + "\n")
    def all(self):
        with self._lock: return tuple(self._load().values())
    def latest_for_actor(self, actor_id, kind=None):
        rows = [r for r in self.all() if r["actor_id"] == actor_id]
        if kind is not None: rows = [r for r in rows if r["kind"] == kind]
        return rows[-1] if rows else None
