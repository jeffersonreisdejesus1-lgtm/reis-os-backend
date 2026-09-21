from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.cupuwa_skills.distributed_ownership import LeaseConflict, StaleOwner
from app.cupuwa_skills.distributed_storage import (
    DistributedOperationKey,
    DistributedOperationRecord,
    DistributedOperationState,
)
from app.cupuwa_skills.posix_distributed_store import (
    PosixFileDistributedStorage,
    payload_fingerprint,
)

AUTHORITY_REF = "authority://noesis/cupuwa-d06"


def _key(operation_id: str, payload: dict, mission: str = "M-D06") -> DistributedOperationKey:
    return DistributedOperationKey(
        mission_id=mission,
        operation_id=operation_id,
        payload_fingerprint=payload_fingerprint(payload),
        schema_version="1.0",
    )


PROBE = r'''
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from app.cupuwa_skills.distributed_storage import DistributedOperationKey, DistributedOperationState, DistributedOperationRecord
from app.cupuwa_skills.posix_distributed_store import PosixFileDistributedStorage, payload_fingerprint
store = PosixFileDistributedStorage(Path(sys.argv[2]))
cmd = sys.argv[3]
payload = json.loads(sys.argv[4])
op = sys.argv[5]
owner = sys.argv[6]
key = DistributedOperationKey("M-D06", op, payload_fingerprint(payload), "1.0")
if cmd == "claim":
    rec = store.claim(key, owner)
    print(json.dumps({"pid": __import__("os").getpid(), "state": rec.state.value, "owner": rec.owner_id}))
elif cmd == "read":
    rec = store.read(key)
    print(json.dumps({"pid": __import__("os").getpid(), "state": None if rec is None else rec.state.value, "owner": None if rec is None else rec.owner_id}))
elif cmd == "succeed":
    digest = store.put_receipt(f"r-{op}", {"authority_ref": "authority://noesis/cupuwa-d06", "ok": True})
    rec = store.write(DistributedOperationRecord(key, DistributedOperationState.SUCCEEDED, owner, f"r-{op}", digest))
    print(json.dumps({"pid": __import__("os").getpid(), "state": rec.state.value, "receipt": rec.receipt_id}))
elif cmd == "recover":
    receipt = store.recover(op, owner_id=owner)
    print(json.dumps({"pid": __import__("os").getpid(), "decision": receipt.decision, "digest": receipt.digest, "state": receipt.observed_state}))
'''


def _repo() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "app" / "cupuwa_skills" / "posix_distributed_store.py").exists():
            return parent
    return Path.cwd()


def _run(tmp_path: Path, cmd: str, payload: dict, op: str, owner: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "-c", PROBE, str(_repo()), str(tmp_path), cmd, json.dumps(payload), op, owner],
        capture_output=True,
        text=True,
        cwd=str(_repo()),
        env=os.environ.copy(),
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_q01_write_process_a_read_process_b(tmp_path: Path) -> None:
    payload = {"n": 1}
    a = _run(tmp_path, "claim", payload, "op-q01", "host-a")
    b = _run(tmp_path, "read", payload, "op-q01", "host-b")
    assert a["pid"] != b["pid"]
    assert a["state"] == "EXECUTING"
    assert b["state"] == "EXECUTING"
    assert b["owner"] == "host-a"


def test_q02_concurrent_claim_one_owner(tmp_path: Path) -> None:
    payload = {"n": 2}
    first = _run(tmp_path, "claim", payload, "op-q02", "host-a")
    with pytest.raises(AssertionError):
        _run(tmp_path, "claim", payload, "op-q02", "host-b")
    assert first["owner"] == "host-a"


def test_q03_conflicting_payload_fail_closed(tmp_path: Path) -> None:
    store = PosixFileDistributedStorage(tmp_path)
    store.claim(_key("op-q03", {"n": 1}), "host-a")
    with pytest.raises(LeaseConflict, match="idempotency conflict"):
        store.claim(_key("op-q03", {"n": 2}), "host-b")


def test_q04_stale_owner_rejected_after_expiry(tmp_path: Path) -> None:
    store = PosixFileDistributedStorage(tmp_path)
    key = _key("op-q04", {"n": 4})
    store.claim(key, "host-a")
    store.expire_lease("op-q04")
    taken = store.claim(key, "host-b")
    assert taken.owner_id == "host-b"
    with pytest.raises(StaleOwner):
        store.write(
            DistributedOperationRecord(
                key, DistributedOperationState.SUCCEEDED, "host-a", "r-stale", "x"
            )
        )


def test_q05_q06_interrupt_and_recover(tmp_path: Path) -> None:
    payload = {"n": 5}
    claimed = _run(tmp_path, "claim", payload, "op-q05", "host-a")
    assert claimed["state"] == "EXECUTING"
    recovered = _run(tmp_path, "recover", payload, "op-q05", "host-b")
    assert recovered["decision"] in {"HOLD", "RETRY"}
    assert recovered["pid"] != claimed["pid"]


def test_q07_replay_no_duplicate_success(tmp_path: Path) -> None:
    payload = {"n": 7}
    _run(tmp_path, "claim", payload, "op-q07", "host-a")
    first = _run(tmp_path, "succeed", payload, "op-q07", "host-a")
    second = _run(tmp_path, "succeed", payload, "op-q07", "host-a")
    assert first["state"] == second["state"] == "SUCCEEDED"
    store = PosixFileDistributedStorage(tmp_path)
    rec = store.read(_key("op-q07", payload))
    assert rec is not None
    assert rec.receipt_id == "r-op-q07"


def test_q08_corrupt_receipt_fail_closed(tmp_path: Path) -> None:
    store = PosixFileDistributedStorage(tmp_path)
    key = _key("op-q08", {"n": 8})
    store.claim(key, "host-a")
    (tmp_path / "receipts" / "r-bad.json").write_text("{", encoding="utf-8")
    store.write(
        DistributedOperationRecord(key, DistributedOperationState.UNKNOWN, "host-a", "r-bad", None)
    )
    receipt = store.recover("op-q08", owner_id="host-b")
    assert receipt.decision == "HOLD"


def test_q09_deterministic_recovery_receipt(tmp_path: Path) -> None:
    payload = {"n": 9}
    _run(tmp_path, "claim", payload, "op-q09", "host-a")
    _run(tmp_path, "succeed", payload, "op-q09", "host-a")
    first = _run(tmp_path, "recover", payload, "op-q09", "host-b")
    second = _run(tmp_path, "recover", payload, "op-q09", "host-b")
    assert first["digest"] == second["digest"]
    assert first["decision"] == "RECONCILE"


def test_q10_authority_ref_preserved(tmp_path: Path) -> None:
    store = PosixFileDistributedStorage(tmp_path)
    key = _key("op-q10", {"n": 10})
    store.claim(key, "host-a")
    digest = store.put_receipt("r-op-q10", {"authority_ref": AUTHORITY_REF, "ok": True})
    store.write(
        DistributedOperationRecord(
            key, DistributedOperationState.SUCCEEDED, "host-a", "r-op-q10", digest
        )
    )
    receipt = store.get_receipt("r-op-q10")
    assert receipt is not None
    assert receipt["authority_ref"] == AUTHORITY_REF
    recovered = store.recover("op-q10", owner_id="host-b")
    assert recovered.decision == "RECONCILE"
    assert store.get_receipt("r-op-q10")["authority_ref"] == AUTHORITY_REF
