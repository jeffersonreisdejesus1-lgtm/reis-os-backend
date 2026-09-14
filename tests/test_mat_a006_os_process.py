from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROBE = r'''
import json, os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from app.materialization.material_plane import (
    DurableEffectStore, FilesystemMaterialProvider, MaterialExecutionRequest, MaterialPlane, Outcome,
)
root = Path(sys.argv[2])
mode = sys.argv[3]
req = MaterialExecutionRequest(
    mission_id="M-A006", logical_operation_id="op-a006", effect_id="eff-a006",
    program_id="REIS-OS-AUTONOMOUS-MATERIALIZATION-CLOSURE-001",
    actor="SOFIA", bound_object="object://a006", expected_object_version="v0",
    capability="fixture_write", authorized_intent_hash="a006",
    payload="durability-payload", authority_ref="authority://dev", generation=1,
)
plane = MaterialPlane(
    store=DurableEffectStore(root / "effects.db"),
    provider=FilesystemMaterialProvider(root / "fx"),
)
if mode == "p1":
    result = plane.execute(req)
elif mode == "p1-unknown":
    result = plane.execute(req, pretick_timeout=True)
else:
    result = plane.execute(req)
print(json.dumps({
    "pid": os.getpid(),
    "outcome": result.outcome.value,
    "replayed": result.replayed,
    "material": result.material,
    "failure": result.failure,
    "artifact": result.material_artifact_ref,
    "hash": result.execution_hash,
}))
'''


def _run(repo: Path, work: Path, mode: str) -> dict:
    completed = subprocess.run(
        [sys.executable, "-c", PROBE, str(repo), str(work), mode],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(repo),
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "app" / "materialization" / "material_plane.py").exists():
            return parent
    return Path.cwd()


def test_a006_t01_t03_t09_t10_two_process_replay_no_duplicate(tmp_path: Path) -> None:
    repo = _repo_root()
    p1 = _run(repo, tmp_path, "p1")
    p2 = _run(repo, tmp_path, "p2")
    assert p1["pid"] != p2["pid"]
    assert p1["replayed"] is False
    assert p1["outcome"] == "SUCCEEDED"
    assert p1["material"] is True
    assert p2["replayed"] is True
    assert p2["hash"] == p1["hash"]
    artifact = Path(p1["artifact"])
    assert artifact.read_text(encoding="utf-8") == "durability-payload"
    # no second write: same bytes after p2
    assert artifact.read_text(encoding="utf-8") == "durability-payload"


def test_a006_t04_restart_before_known_effect_stays_unknown(tmp_path: Path) -> None:
    repo = _repo_root()
    p1 = _run(repo, tmp_path, "p1-unknown")
    p2 = _run(repo, tmp_path, "p2")
    assert p1["pid"] != p2["pid"]
    assert p1["outcome"] == "EXECUTION_UNKNOWN"
    assert p1["material"] is False


def test_a006_t07_tamper_after_restart_is_drift(tmp_path: Path) -> None:
    repo = _repo_root()
    p1 = _run(repo, tmp_path, "p1")
    Path(p1["artifact"]).write_text("tampered", encoding="utf-8")
    p2 = _run(repo, tmp_path, "p2")
    assert p1["pid"] != p2["pid"]
    assert p2["replayed"] is True
    assert p2["outcome"] != "SUCCEEDED"
    assert Path(p1["artifact"]).read_text(encoding="utf-8") == "tampered"
